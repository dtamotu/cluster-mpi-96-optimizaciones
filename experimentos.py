#!/usr/bin/env python3
"""Batería reproducible: matrices 1D, jerárquica, 2D y difusión aislada."""
from __future__ import annotations

import argparse
import csv
import json
import os
import random
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STAGE = "/var/tmp/cluster-mpi-96-optimizaciones/bin"
HOSTS = {
    "Ethernet": ["10.7.50.202", "10.7.50.203", "10.7.50.201", "10.7.50.204"],
    "Wi-Fi": ["10.7.134.117", "10.7.134.58", "10.7.134.59", "10.7.134.51"],
}
IFACE = {"Ethernet": "enp128s31f6", "Wi-Fi": "wlp129s0f0"}
CFG = {"Ethernet": ROOT / "scripts/ssh_config", "Wi-Fi": ROOT / "scripts/ssh_config_wifi"}
FIELDS = ["id", "kind", "red", "n", "p", "nodos", "variante", "repeticion", "estado",
          "T_Total", "T_Dist", "T_Scatter", "T_Bcast", "T_Summa", "T_Calc",
          "T_Gather", "T_CalcMax", "T_CalcMin", "T_Reduce", "Desbalance", "Error", "Pi",
          "Checksum", "WSum", "Hash", "Valido", "pared_s",
          "tx_mb_total", "rx_mb_total", "log"]


def cases():
    out = []
    # Caso principal: cinco repeticiones por configuración para estimar dispersión.
    for rep in range(1, 6):
        block = []
        for red in HOSTS:
            for p in (24, 96):
                for variant in ("1d", "1d-hier"):
                    block.append(dict(kind="matriz", red=red, n=3072, p=p,
                                      nodos=1 if p == 24 else 4, variante=variant, repeticion=rep))
        if rep <= 3:
            # Difusión de B aislada; 16 rangos locales o entre cuatro nodos.
            for red in HOSTS:
                for variant in ("world", "hier", "tuned-knomial", "tuned-scatter"):
                    block.append(dict(kind="bcast", red=red, n=3072, p=16, nodos=4,
                                      variante=variant, repeticion=rep))
            for variant in ("world", "hier"):
                block.append(dict(kind="bcast", red="Ethernet", n=3072, p=16, nodos=1,
                                  variante=variant, repeticion=rep))
            # El SUMMA existente admite 64=8x8; se compara con 1D al mismo P.
            for red in HOSTS:
                for variant in ("1d", "2d"):
                    block.append(dict(kind="matriz", red=red, n=3072, p=64, nodos=4,
                                      variante=variant, repeticion=rep))
        random.Random(20260925 + rep).shuffle(block)
        out.extend(block)
    for c in out:
        c["id"] = "_".join(str(c[k]) for k in ("kind", "red", "n", "p", "nodos", "variante", "repeticion")).replace(" ", "")
    return out


def cases_extra():
    out = []
    for rep in range(1, 4):
        block = []
        for n in (6144, 7168):
            for p in (24, 96):
                block.append(dict(kind="matriz", red="Ethernet", n=n, p=p,
                                  nodos=1 if p == 24 else 4, variante="1d", repeticion=rep))
        for n in (100000000, 100000000000):
            for p in (24, 96):
                for variant in ("simetrico", "asimetrico"):
                    block.append(dict(kind="trapecio", red="Ethernet", n=n, p=p,
                                      nodos=1 if p == 24 else 4, variante=variant, repeticion=rep))
        random.Random(20260926 + rep).shuffle(block)
        out.extend(block)
    for c in out:
        c["id"] = "_".join(str(c[k]) for k in ("kind", "red", "n", "p", "nodos", "variante", "repeticion"))
    return out


def counter(host: str, iface: str, cfg: Path):
    path = f"/sys/class/net/{iface}/statistics"
    cmd = f"cat {path}/tx_bytes {path}/rx_bytes"
    if host in ("10.7.50.202", "10.7.134.117"):
        proc = subprocess.run(["bash", "-lc", cmd], text=True, capture_output=True, timeout=8)
    else:
        proc = subprocess.run(["ssh", "-F", str(cfg), host, cmd], text=True, capture_output=True, timeout=15)
    if proc.returncode:
        raise RuntimeError(f"contador {host}: {proc.stderr.strip()}")
    tx, rx = map(int, proc.stdout.split())
    return tx, rx


def counters(red: str, nodos: int):
    return {host: counter(host, IFACE[red], CFG[red]) for host in HOSTS[red][:nodos]}


def check_large_matrix_memory(c: dict):
    if c["kind"] != "matriz" or c["n"] < 6144:
        return
    # 24 copias de B y A/C/fragmentos; 30 % de margen para MPI y el sistema.
    needed = int(1.3 * (24 * 8 + 32) * c["n"] ** 2)
    for host in HOSTS[c["red"]][:c["nodos"]]:
        cmd = "awk '/MemAvailable:/ {print $2}' /proc/meminfo"
        args = ["bash", "-lc", cmd] if host in ("10.7.50.202", "10.7.134.117") else ["ssh", "-F", str(CFG[c["red"]]), host, cmd]
        proc = subprocess.run(args, text=True, capture_output=True, timeout=15)
        if proc.returncode or not proc.stdout.strip().isdigit():
            raise RuntimeError(f"no se pudo leer MemAvailable en {host}")
        available = int(proc.stdout.strip()) * 1024
        if available < needed:
            raise RuntimeError(f"MemAvailable insuficiente en {host}: {available / 2**30:.1f} GiB < {needed / 2**30:.1f} GiB requeridos")


def command(c):
    red, p, nodos = c["red"], c["p"], c["nodos"]
    slots = p // nodos
    hosts = ",".join(f"{host}:{slots}" for host in HOSTS[red][:nodos])
    net = "10.7.50.0/24" if red == "Ethernet" else "10.7.134.0/23"
    cmd = ["mpirun", "-H", hosts, "-np", str(p), "--map-by", "slot", "--rank-by", "slot",
           "--bind-to", "core", "--mca", "plm_rsh_agent", f"ssh -F {CFG[red]}",
           "--mca", "btl", "self,vader,tcp", "--mca", "btl_tcp_if_include", net,
           "--mca", "oob_tcp_if_include", net]
    if c["kind"] == "trapecio":
        cmd.append("--report-bindings")
    if c["variante"].startswith("tuned-"):
        alg = "7" if c["variante"] == "tuned-knomial" else "8"
        cmd += ["--mca", "coll_tuned_use_dynamic_rules", "1",
                "--mca", "coll_tuned_bcast_algorithm", alg]
    if c["kind"] == "bcast":
        mode = "hier" if c["variante"] == "hier" else "world"
        cmd += [f"{STAGE}/bcast_bench", str(c["n"]), mode]
    elif c["kind"] == "trapecio":
        mode = "0" if c["variante"] == "simetrico" else "1"
        cmd += [f"{STAGE}/trapecio_asimetrico", str(c["n"]), mode]
    else:
        cmd += [f"{STAGE}/mpi_matrix_2d", str(c["n"]), c["variante"], "tiled", "64"]
    return cmd


def parse_result(output: str):
    lines = [s for s in output.splitlines() if s.startswith(("RESULT_2D:", "RESULT_BCAST:", "RESULT_ASYM:"))]
    if len(lines) != 1:
        raise ValueError(f"se esperaba una línea RESULT, aparecieron {len(lines)}")
    result = {}
    for part in lines[0].split(":", 1)[1].split(","):
        k, value = part.strip().split("=", 1)
        result[k] = value
    return result


def append_row(path: Path, row: dict):
    new = not path.exists()
    if new:
        fieldnames = FIELDS
    else:
        with path.open(newline="") as existing_file:
            fieldnames = next(csv.reader(existing_file))
    with path.open("a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if new:
            writer.writeheader()
        writer.writerow({k: row.get(k, "") for k in fieldnames})
        f.flush()
        os.fsync(f.fileno())


def execute(c: dict, folder: Path, timeout: int):
    cmd = command(c)
    log = folder / "logs" / f"{c['id']}.log"
    log.parent.mkdir(exist_ok=True)
    start = datetime.now().astimezone().isoformat()
    t0 = time.monotonic()
    before = after = None
    try:
        check_large_matrix_memory(c)
        before = counters(c["red"], c["nodos"])
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout, cwd=ROOT)
        after = counters(c["red"], c["nodos"])
        status = "ok" if proc.returncode == 0 else f"exit_{proc.returncode}"
        output = proc.stdout + "\n" + proc.stderr
    except subprocess.TimeoutExpired as exc:
        status = "timeout"
        output = (exc.stdout or b"").decode(errors="replace") if isinstance(exc.stdout, bytes) else exc.stdout or ""
        output += "\n" + ((exc.stderr or b"").decode(errors="replace") if isinstance(exc.stderr, bytes) else exc.stderr or "")
        try:
            after = counters(c["red"], c["nodos"])
        except Exception as err:
            output += f"\nerror al leer contadores finales: {err}\n"
    except Exception as exc:
        status = "error"
        output = f"{type(exc).__name__}: {exc}\n"
    wall = time.monotonic() - t0
    log.write_text(json.dumps({"inicio": start, "comando": cmd, "antes": before, "despues": after,
                               "estado": status}, indent=2, ensure_ascii=False) + "\n\n" + output)
    row = dict(c, estado=status, pared_s=round(wall, 4), log=str(log.relative_to(folder)))
    if before and after:
        row["tx_mb_total"] = round(sum(after[h][0] - before[h][0] for h in before) / 1e6, 4)
        row["rx_mb_total"] = round(sum(after[h][1] - before[h][1] for h in before) / 1e6, 4)
    if status == "ok":
        try:
            data = parse_result(output)
            for key in ("T_Total", "T_Dist", "T_Scatter", "T_Bcast", "T_Summa", "T_Calc", "T_Gather",
                        "T_CalcMax", "T_CalcMin", "T_Reduce", "Desbalance", "Error", "Pi",
                        "Checksum", "WSum", "Hash", "Valido"):
                if key in data:
                    row[key] = data[key]
            if data.get("Valido") == "0":
                row["estado"] = "checksum_invalido"
            if c["kind"] == "matriz" and c["n"] == 3072:
                if abs(float(data["Checksum"]) - 22083010.24) > 0.02 or abs(float(data["WSum"]) / 4.748730e11 - 1) > 1e-5:
                    row["estado"] = "checksum_invalido"
            if c["kind"] == "trapecio" and float(data["Error"]) > 1e-8:
                row["estado"] = "error_numerico"
        except Exception as exc:
            row["estado"] = "parse_error"
            with log.open("a") as f:
                f.write(f"\n{exc}\n")
    row["log"] = str(log.relative_to(folder))
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["plan", "smoke", "run", "plan-extra", "extra"])
    parser.add_argument("--dir", type=Path, help="directorio de resultados para reanudar")
    parser.add_argument("--timeout", type=int, default=420, help="límite por corrida en segundos")
    parser.add_argument("--max-new", type=int, help="número máximo de intentos nuevos en esta invocación")
    args = parser.parse_args()
    planned = cases_extra() if args.action in ("plan-extra", "extra") else cases()
    if args.action in ("plan", "plan-extra"):
        for c in planned:
            print(c["id"], " ".join(command(c)))
        print(f"Total: {len(planned)} corridas")
        return
    if args.action == "smoke":
        planned = [dict(kind="matriz", red="Ethernet", n=512, p=16, nodos=4,
                        variante=v, repeticion=0, id=f"smoke_matriz_{v}") for v in ("1d", "1d-hier", "2d")]
        # 2D requiere P cuadrado y 512 divisible por 4.
        planned += [dict(kind="trapecio", red="Ethernet", n=10000, p=24, nodos=1,
                         variante=v, repeticion=0, id=f"smoke_trapecio_{v}") for v in ("simetrico", "asimetrico")]
    folder = args.dir or ROOT / "resultados_optimizacion" / datetime.now().strftime("%Y%m%d_%H%M%S")
    folder.mkdir(parents=True, exist_ok=True)
    csv_path = folder / "resultados.csv"
    existing = {r["id"] for r in csv.DictReader(csv_path.open())} if csv_path.exists() else set()
    if not (folder / "entorno.json").exists():
        env = {"fecha": datetime.now().astimezone().isoformat(), "hostname": os.uname().nodename,
               "mpi": subprocess.run(["ompi_info", "--version"], text=True, capture_output=True).stdout.splitlines()[0],
               "compilacion": "mpicc -O3 -std=c11 -Wall -Wextra", "timeout_s": args.timeout,
               "casos_planificados": len(planned),
               "nota_trafico": "suma TX/RX por nodo; incluye control SSH y posible tráfico ajeno"}
        (folder / "entorno.json").write_text(json.dumps(env, indent=2, ensure_ascii=False))
    newly_run = 0
    for idx, c in enumerate(planned, 1):
        if c["id"] in existing:
            continue
        print(f"[{idx}/{len(planned)}] {c['id']}", flush=True)
        row = execute(c, folder, args.timeout)
        append_row(csv_path, row)
        newly_run += 1
        print(f"  {row['estado']} T={row.get('T_Total') or row.get('T_Bcast')} s, pared={row['pared_s']} s", flush=True)
        if args.max_new and newly_run >= args.max_new:
            break
    print(f"Resultados: {csv_path}")


if __name__ == "__main__":
    main()
