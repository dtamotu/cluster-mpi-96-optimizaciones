#!/usr/bin/env python3
"""Contrasta CSV con logs, comprueba resultados y sella archivos con SHA-256."""
from __future__ import annotations

import argparse
import csv
import hashlib
from collections import defaultdict
from pathlib import Path

from experimentos import parse_result


def audit(folder: Path):
    csv_path = folder / "resultados.csv"
    rows = list(csv.DictReader(csv_path.open()))
    seen = set()
    checks = defaultdict(list)
    files = [csv_path]
    if (folder / "entorno.json").exists():
        files.append(folder / "entorno.json")
    for row in rows:
        ident = row["id"]
        if ident in seen:
            raise ValueError(f"ID duplicado: {ident}")
        seen.add(ident)
        log = folder / row["log"]
        if not log.is_file():
            raise FileNotFoundError(log)
        files.append(log)
        if row["estado"] != "ok":
            continue
        parsed = parse_result(log.read_text(errors="replace"))
        field = "T_Bcast" if row["kind"] == "bcast" else "T_Total"
        if abs(float(parsed[field]) - float(row[field])) > 1e-6:
            raise ValueError(f"tiempo diferente entre CSV y log: {ident}")
        if row["kind"] == "bcast" and parsed["Valido"] != "1":
            raise ValueError(f"huella de difusión distinta: {ident}")
        if row["kind"] == "matriz":
            checks[int(row["n"])].append((float(parsed["Checksum"]), float(parsed["WSum"])))
        if row["kind"] == "trapecio" and float(parsed["Error"]) > 1e-8:
            raise ValueError(f"error numérico de trapecio: {ident}")
    for n, vals in checks.items():
        base = vals[0]
        for candidate in vals[1:]:
            if abs(candidate[0] - base[0]) > 0.02 or abs(candidate[1] / base[1] - 1) > 1e-5:
                raise ValueError(f"matrices N={n} con sumas de control distintas")
    lines = []
    for path in sorted(files):
        lines.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(folder)}")
    (folder / "SHA256SUMS").write_text("\n".join(lines) + "\n")
    print(f"{folder}: {len(rows)} intentos, {sum(r['estado'] == 'ok' for r in rows)} válidos; {len(checks)} tamaños de matriz; {len(lines)} archivos sellados")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("carpetas", nargs="+", type=Path)
    args = p.parse_args()
    for path in args.carpetas:
        audit(path.resolve())
