#!/usr/bin/env python3
"""Audita la evidencia del informe y genera las tablas de auditoría y variabilidad.

Solo lee: los CSV, logs, JSON y sellos SHA-256 del repositorio original y,
si existe, la carpeta experimentos_96. Escribe únicamente en tablas/ y datos/
de esta carpeta. Si una comprobación falla, se informa en la tabla; no se
corrige ni se omite ningún dato.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import statistics as stats
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("EVIDENCIA_MPI", OUT.parent)).resolve()
EXP = ROOT.parent / "experimentos_96"
CAMPANAS = [ROOT / "resultados_optimizacion" / "20260925_074354",
            ROOT / "resultados_optimizacion" / "20260925_extra"]
TOL = 1e-6


def resultado(texto, prefijos=("RESULT_2D", "RESULT_TRAP", "RESULT_BCAST", "RESULT_ASYM")):
    lineas = [l for l in texto.splitlines() if l.startswith(prefijos)]
    campos = dict(x.strip().split("=", 1) for x in lineas[0].split(":", 1)[1].split(",")) if lineas else {}
    return len(lineas), campos


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cerca(a, b):
    return abs(float(a) - float(b)) <= TOL * max(1.0, abs(float(b)))


def bateria_1():
    total = fallos = 0
    for red in ("ethernet", "wifi"):
        for f in csv.DictReader((ROOT / "datos" / red / "tiempos.csv").open()):
            total += 1
            n_res, c = resultado((ROOT / "datos" / red / f"{f['experimento']}_{f['tamano']}_{f['procesos']}.log").read_text())
            if n_res != 1 or not cerca(f["T_Total"], c["T_Total"]) or int(c["Procs"]) != int(f["procesos"]):
                fallos += 1
    return total, fallos


def bateria_2():
    carpeta = ROOT / "datos" / "ampliada"
    total = fallos = 0
    for f in csv.DictReader((carpeta / "resultados_consolidados.csv").open()):
        total += 1
        n_res, c = resultado((carpeta / f"{f['red']}_{f['experimento']}_{f['tamano']}_{f['procesos']}.log").read_text())
        pares = [("T_Total", "T_Total"), ("T_Calc", "T_Calc")]
        pares += [("T_Dist", "T_Dist"), ("T_Gather", "T_Gather")] if f["experimento"] == "matrices" else [("T_Gather", "T_Reduce")]
        if n_res != 1 or any(not cerca(f[a], c[b]) for a, b in pares):
            fallos += 1
    return total, fallos


def huellas():
    """Suma diagonal y ponderada por N en todos los logs de matrices de ambas baterías."""
    por_n = {}
    for log in list((ROOT / "datos").glob("ethernet/matrices_*.log")) + list((ROOT / "datos").glob("wifi/matrices_*.log")) \
            + list((ROOT / "datos" / "ampliada").glob("*_matrices_*.log")):
        _, c = resultado(log.read_text())
        por_n.setdefault(int(c["N"]), set()).add((c["Checksum"], c["WSum"]))
    errores = []
    for log in list((ROOT / "datos").glob("*/trapecio_*.log")) + list((ROOT / "datos" / "ampliada").glob("*_trapecio_*.log")):
        _, c = resultado(log.read_text())
        errores.append(float(c["Error"]))
    return len(por_n), sum(len(v) != 1 for v in por_n.values()), max(errores), len(errores)


def campana():
    total = fallos = trafico = 0
    for carpeta in CAMPANAS:
        for f in csv.DictReader((carpeta / "resultados.csv").open()):
            total += 1
            texto = (carpeta / f["log"]).read_text(errors="replace")
            n_res, c = resultado(texto)
            campos = [k for k in ("T_Total", "T_Dist", "T_Scatter", "T_Bcast", "T_Calc", "T_Gather", "Checksum", "WSum")
                      if f.get(k) and k in c]
            if n_res != 1 or any(not cerca(f[k], c[k]) for k in campos):
                fallos += 1
            meta = json.JSONDecoder().raw_decode(texto)[0]
            tx = sum(meta["despues"][h][0] - meta["antes"][h][0] for h in meta["antes"]) / 1e6
            rx = sum(meta["despues"][h][1] - meta["antes"][h][1] for h in meta["antes"]) / 1e6
            if abs(tx - float(f["tx_mb_total"])) > 1e-3 or abs(rx - float(f["rx_mb_total"])) > 1e-3:
                trafico += 1
    return total, fallos, trafico


def sellos():
    archivos = malos = 0
    for carpeta in CAMPANAS:
        for linea in (carpeta / "SHA256SUMS").read_text().splitlines():
            h, nombre = linea.split(maxsplit=1)
            archivos += 1
            malos += sha(carpeta / nombre) != h
    return archivos, malos


def procedencia():
    copias = copias_mal = 0
    originales_revisados = 0
    originales_distintos = []
    for nombre in ("procedencia.json", "procedencia_ampliada.json"):
        for e in json.loads((ROOT / "datos" / nombre).read_text()):
            copias += 1
            copias_mal += sha(ROOT / e["copia"]) != e["sha256"]
            original = Path(e["original"])
            if original.exists():
                originales_revisados += 1
                if sha(original) != e["sha256"]:
                    originales_distintos.append(original.name)
    return copias, copias_mal, originales_revisados, sorted(originales_distintos)


def compilacion():
    return json.loads((CAMPANAS[0] / "entorno.json").read_text()).get("compilacion", "sin registro")


def analisis_ampliado():
    """Indica a qué CSV corresponde analisis/metricas.csv de la batería ampliada original."""
    base = EXP / "bateria_expandida" / "20260925_003457"
    if not (base / "analisis" / "metricas.csv").exists():
        return "no disponible"
    metricas = {(r["experimento"], r["tamano"], r["procesos"]): float(r["T_Total"])
                for r in csv.DictReader((base / "analisis" / "metricas.csv").open())}
    for nombre, red in (("tiempos_eth.csv", "Ethernet"), ("tiempos_wifi.csv", "Wi-Fi")):
        fuente = {(r["experimento"], r["tamano"], r["procesos"]): float(r["T_Total"])
                  for r in csv.DictReader((base / nombre).open())}
        if fuente == metricas:
            return red
    return "ninguno"


def tex(s):
    return s.replace("_", r"\_")


def tabla_auditoria():
    b1, b1f = bateria_1()
    b2, b2f = bateria_2()
    n_tam, n_tam_mal, err_max, n_trap = huellas()
    c, cf, ctx = campana()
    s, sm = sellos()
    pc, pcm, por, po = procedencia()
    flags = compilacion()
    analisis = analisis_ampliado()
    ok = lambda fallos: "sin discrepancias" if fallos == 0 else f"\\textbf{{{fallos} discrepancias}}"
    filas = [
        ("Primera batería: CSV frente a logs", f"{b1} filas (T\\_Total, $P$)", ok(b1f)),
        ("Segunda batería: CSV consolidado frente a logs", f"{b2} filas (4 tiempos)", ok(b2f)),
        ("Huellas de matrices en ambas baterías", f"{n_tam} tamaños de $N$", ok(n_tam_mal)),
        ("Error del trapecio respecto de $\\pi$", f"{n_trap} ejecuciones", f"máximo {err_max:.2e}"),
        ("Campaña: CSV frente a logs", f"{c} filas (tiempos y huellas)", ok(cf)),
        ("Campaña: TX/RX frente a contadores del log", f"{c} filas", ok(ctx)),
        ("Campaña: sellos SHA256SUMS", f"{s} archivos", ok(sm)),
        ("Copias de evidencia frente a procedencia", f"{pc} archivos", ok(pcm)),
        ("Originales externos, si están disponibles", f"{por} archivos",
         "no disponibles" if por == 0 else ok(0) if not po else
         "\\textbf{distintos}: " + ", ".join(f"\\archivo{{{p}}}" for p in po)),
        ("Compilación registrada en la campaña", "\\archivo{entorno.json}", f"\\texttt{{{tex(flags)}}}"),
        ("Gráficos de \\archivo{bateria_expandida/.../analisis/}", "\\archivo{metricas.csv}",
         f"\\textbf{{solo {analisis}}}" if analisis in ("Ethernet", "Wi-Fi") else analisis),
    ]
    lineas = [r"\begin{center}\small", r"\begin{tabularx}{\linewidth}{>{\raggedright\arraybackslash}p{5.4cm}>{\raggedright\arraybackslash}p{3.6cm}X}",
              r"\toprule", r"Comprobación & Alcance & Resultado \\", r"\midrule"]
    lineas += [f"{a} & {b} & {r} \\\\" for a, b, r in filas]
    lineas += [r"\bottomrule", r"\end{tabularx}", r"\end{center}"]
    (OUT / "tablas" / "auditoria.tex").write_text("\n".join(lineas) + "\n")
    resumen = {"bateria_1": [b1, b1f], "bateria_2": [b2, b2f], "tamanos_matriz": [n_tam, n_tam_mal],
               "trapecio_error_max": err_max, "campana": [c, cf, ctx], "sha256sums": [s, sm],
               "procedencia_copias": [pc, pcm], "originales_revisados": por,
               "originales_distintos": po, "compilacion_campana": flags,
               "analisis_bateria_ampliada": analisis}
    (OUT / "datos").mkdir(exist_ok=True)
    (OUT / "datos" / "auditoria.json").write_text(json.dumps(resumen, indent=2, ensure_ascii=False) + "\n")
    return resumen


def log_campos(path):
    return resultado(path.read_text(errors="replace"))[1]


def tabla_variabilidad():
    """Corrida única de cada batería frente a mediana y rango de la campaña."""
    filas_campana = []
    for carpeta in CAMPANAS:
        filas_campana += list(csv.DictReader((carpeta / "resultados.csv").open()))

    def campana_vals(tipo, red, n, p, variante, campo):
        return [float(f[campo]) for f in filas_campana if f["kind"] == tipo and f["red"] == red and int(f["n"]) == n
                and int(f["p"]) == p and f["variante"] == variante and f["estado"] == "ok" and f[campo]]

    def b1(red, exp, n, p, campo="T_Total"):
        path = ROOT / "datos" / ("ethernet" if red == "Ethernet" else "wifi") / f"{exp}_{n}_{p}.log"
        return float(log_campos(path)[campo]) if path.exists() else None

    def b2(red, exp, n, p, campo="T_Total"):
        path = ROOT / "datos" / "ampliada" / f"{red}_{exp}_{n}_{p}.log"
        return float(log_campos(path)[campo]) if path.exists() else None

    casos = [("Matrices", "Ethernet", 3072, 24), ("Matrices", "Ethernet", 3072, 96),
             ("Matrices", "Wi-Fi", 3072, 24), ("Matrices", "Wi-Fi", 3072, 96),
             ("Matrices", "Ethernet", 6144, 24), ("Matrices", "Ethernet", 6144, 96),
             ("Trapecio", "Ethernet", 10**11, 24), ("Trapecio", "Ethernet", 10**11, 96)]
    fmt = lambda v: "--" if v is None else f"{v:.3f}"
    lineas = [r"\begin{center}\small", r"\begin{tabular}{llrrrrrr}", r"\toprule",
              r" & & & \multicolumn{2}{c}{Corrida única} & \multicolumn{3}{c}{Campaña} \\",
              r"\cmidrule(lr){4-5}\cmidrule(lr){6-8}",
              r"Prueba & Red & $P$ & Bat. 1 & Bat. 2 & Mediana & Rango & Reps. \\", r"\midrule"]
    calc = []
    for exp, red, n, p in casos:
        clave = "matrices" if exp == "Matrices" else "trapecio"
        tipo, variante = ("matriz", "1d") if exp == "Matrices" else ("trapecio", "simetrico")
        v = campana_vals(tipo, red, n, p, variante, "T_Total")
        ntexto = f"$N={n}$" if exp == "Matrices" else "$n=10^{11}$"
        lineas.append(f"{exp} {ntexto} & {red} & {p} & {fmt(b1(red, clave, n, p))} & "
                      f"{fmt(b2(red, clave, n, p))} & {fmt(stats.median(v))} & {fmt(min(v))}--{fmt(max(v))} & {len(v)} \\\\")
        if exp == "Matrices" and p == 24:
            vc = campana_vals(tipo, red, n, p, variante, "T_Calc")
            vd = campana_vals(tipo, red, n, p, variante, "T_Dist")
            calc.append((ntexto, red, b1(red, clave, n, p, "T_Calc"), b2(red, clave, n, p, "T_Calc"), stats.median(vc),
                         b1(red, clave, n, p, "T_Dist"), b2(red, clave, n, p, "T_Dist"), stats.median(vd)))
    lineas += [r"\bottomrule", r"\end{tabular}", r"\end{center}"]
    (OUT / "tablas" / "variabilidad.tex").write_text("\n".join(lineas) + "\n")

    lineas = [r"\begin{center}\small", r"\begin{tabular}{llrrrrrr}", r"\toprule",
              r" & & \multicolumn{3}{c}{$T_{Calc}$ máximo (s)} & \multicolumn{3}{c}{$T_{Dist}$ máximo (s)} \\",
              r"\cmidrule(lr){3-5}\cmidrule(lr){6-8}",
              r"Matriz & Red & Bat. 1 & Bat. 2 & Campaña & Bat. 1 & Bat. 2 & Campaña \\", r"\midrule"]
    for ntexto, red, c1, c2, cc, d1, d2, dc in calc:
        lineas.append(f"{ntexto} & {red} & {fmt(c1)} & {fmt(c2)} & {fmt(cc)} & "
                      f"{fmt(d1)} & {fmt(d2)} & {fmt(dc)} \\\\")
    lineas += [r"\bottomrule", r"\end{tabular}", r"\end{center}"]
    (OUT / "tablas" / "variabilidad_fases.tex").write_text("\n".join(lineas) + "\n")


def main():
    resumen = tabla_auditoria()
    tabla_variabilidad()
    print("Auditoría:", json.dumps(resumen, ensure_ascii=False))


if __name__ == "__main__":
    main()
