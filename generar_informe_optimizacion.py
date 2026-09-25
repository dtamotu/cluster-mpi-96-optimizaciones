#!/usr/bin/env python3
"""Regenera las tablas y el PDF LaTeX desde las corridas guardadas."""
from __future__ import annotations

import argparse
import csv
import math
import statistics as stats
import subprocess
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def fmt(x, places=3):
    return f"{x:.{places}f}"


def cell(s):
    return str(s).replace("_", r"\_").replace("-", "--")


def summary(rows):
    groups = defaultdict(list)
    for r in rows:
        if r["estado"] == "ok":
            key = (r["kind"], r["red"], int(r["p"]), int(r["nodos"]), r["variante"])
            groups[key].append(r)
    return groups


def values(group, key):
    return [float(r[key]) for r in group if r.get(key)]


def metric(groups, key, field):
    v = values(groups.get(key, []), field)
    return stats.median(v) if v else None


def comparison(groups, first, second, field):
    a, b = metric(groups, first, field), metric(groups, second, field)
    return f"{fmt(a / b, 2)}\\,veces" if a and b else "sin datos suficientes"


def build(csv_path: Path):
    rows = list(csv.DictReader(csv_path.open()))
    groups = summary(rows)
    output = []
    output.append(r"\begin{longtable}{llrrlrrrr}")
    output.append(r"\caption{Resultados medidos en la batería nueva. Los tiempos son medianas de las corridas válidas; el rango muestra mínimo y máximo. TX suma la transmisión de los nodos participantes.}\\")
    output.append(r"\toprule Red & Prueba & $P$ & Nodos & Variante & $n$ & $T$ med. (s) & Rango (s) & TX (MB) \\")
    output.append(r"\midrule\endfirsthead")
    output.append(r"\toprule Red & Prueba & $P$ & Nodos & Variante & $n$ & $T$ med. (s) & Rango (s) & TX (MB) \\")
    output.append(r"\midrule\endhead")
    for key in sorted(groups, key=lambda k: (k[0], k[1], k[2], k[3], k[4])):
        kind, red, p, nodos, variant = key
        group = groups[key]
        field = "T_Bcast" if kind == "bcast" else "T_Total"
        data = values(group, field)
        tx = values(group, "tx_mb_total")
        if not data:
            continue
        output.append(f"{cell(red)} & {cell(kind)} & {p} & {nodos} & {cell(variant)} & {len(data)} & "
                      f"{fmt(stats.median(data))} & {fmt(min(data))}--{fmt(max(data))} & "
                      f"{fmt(stats.median(tx), 1) if tx else '--'} " + r"\\")
    output.append(r"\bottomrule\end{longtable}")
    (ROOT / "tablas_optimizacion.tex").write_text("\n".join(output) + "\n")

    keys = lambda kind, red, p, nodos, variant: (kind, red, p, nodos, variant)
    notes = []
    for red in ("Ethernet", "Wi-Fi"):
        a = keys("matriz", red, 96, 4, "1d")
        b = keys("matriz", red, 96, 4, "1d-hier")
        notes.append(f"En {red}, la difusión jerárquica explícita frente a 1D por defecto a $P=96$ dio un cociente de tiempos "
                     f"{comparison(groups, a, b, 'T_Total')}. Un valor mayor que 1 favorece la variante jerárquica.\n\n")
    for red in ("Ethernet", "Wi-Fi"):
        a = keys("matriz", red, 64, 4, "1d")
        b = keys("matriz", red, 64, 4, "2d")
        notes.append(f"En {red}, SUMMA 2D frente a 1D, ambos con $P=64$, dio un cociente de tiempos "
                     f"{comparison(groups, a, b, 'T_Total')}.\n\n")
    for red in ("Ethernet", "Wi-Fi"):
        a = keys("matriz", red, 96, 4, "1d")
        b = keys("matriz", red, 24, 1, "1d")
        notes.append(f"En {red}, cuatro nodos con 96 procesos frente a un nodo con 24 procesos dieron un cociente "
                     f"$T_{{96}}/T_{{24}}$ de {comparison(groups, a, b, 'T_Total')}. Aquí un valor mayor que 1 favorece un nodo.\n\n")
    (ROOT / "conclusiones_optimizacion.tex").write_text("\n".join(notes))

    all_ok = sum(r["estado"] == "ok" for r in rows)
    failures = [r for r in rows if r["estado"] != "ok"]
    records = f"Se guardaron {len(rows)} intentos, de los cuales {all_ok} terminaron y entregaron una línea de resultado válida."
    if failures:
        records += " Los intentos fallidos o vencidos aparecen en el CSV y conservan su log; no se sustituyen por una cifra estimada."
    (ROOT / "estado_optimizacion.tex").write_text(records + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    args = parser.parse_args()
    build(args.csv.resolve())
    for _ in range(2):
        subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "informe_optimizacion.tex"],
                       cwd=ROOT, stdout=subprocess.DEVNULL, check=True)
    print(ROOT / "informe_optimizacion.pdf")


if __name__ == "__main__":
    main()
