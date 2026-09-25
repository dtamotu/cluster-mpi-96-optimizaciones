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
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent


def fmt(x, places=3):
    return f"{x:.{places}f}"


def cell(s):
    return str(s).replace("_", r"\_").replace("-", "--")


def summary(rows):
    groups = defaultdict(list)
    for r in rows:
        if r["estado"] == "ok":
            key = (r["kind"], r["red"], int(r["n"]), int(r["p"]), int(r["nodos"]), r["variante"])
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


def build(csv_paths: list[Path]):
    rows = []
    for csv_path in csv_paths:
        rows.extend(csv.DictReader(csv_path.open()))
    groups = summary(rows)
    output = []
    output.append(r"\begin{longtable}{llrrrlrrrr}")
    output.append(r"\caption{Resultados medidos en la batería nueva. Los tiempos son medianas de las corridas válidas; el rango muestra mínimo y máximo. TX suma la transmisión de los nodos participantes.}\\")
    output.append(r"\toprule Red & Prueba & Tamaño & $P$ & Nodos & Variante & Reps. & $T$ med. (s) & Rango (s) & TX (MB) \\")
    output.append(r"\midrule\endfirsthead")
    output.append(r"\toprule Red & Prueba & Tamaño & $P$ & Nodos & Variante & Reps. & $T$ med. (s) & Rango (s) & TX (MB) \\")
    output.append(r"\midrule\endhead")
    for key in sorted(groups, key=lambda k: (k[0], k[1], k[2], k[3], k[4], k[5])):
        kind, red, n, p, nodos, variant = key
        group = groups[key]
        field = "T_Bcast" if kind == "bcast" else "T_Total"
        data = values(group, field)
        tx = values(group, "tx_mb_total")
        if not data:
            continue
        ntext = "$10^{8}$" if n == 100000000 else "$10^{11}$" if n == 100000000000 else str(n)
        output.append(f"{cell(red)} & {cell(kind)} & {ntext} & {p} & {nodos} & {cell(variant)} & {len(data)} & "
                      f"{fmt(stats.median(data))} & {fmt(min(data))}--{fmt(max(data))} & "
                      f"{fmt(stats.median(tx), 1) if tx else '--'} " + r"\\")
    output.append(r"\bottomrule\end{longtable}")
    (ROOT / "tablas_optimizacion.tex").write_text("\n".join(output) + "\n")

    keys = lambda kind, red, n, p, nodos, variant: (kind, red, n, p, nodos, variant)
    notes = []
    for red in ("Ethernet", "Wi-Fi"):
        a = keys("matriz", red, 3072, 96, 4, "1d")
        b = keys("matriz", red, 3072, 96, 4, "1d-hier")
        ba, bb = metric(groups, a, "T_Bcast"), metric(groups, b, "T_Bcast")
        bcast_text = f" El máximo de la fase Bcast pasó de {fmt(ba)} a {fmt(bb)} s." if ba is not None and bb is not None else ""
        notes.append(f"En {red}, la difusión jerárquica explícita frente a 1D por defecto a $P=96$ dio un cociente de tiempos "
                     f"{comparison(groups, a, b, 'T_Total')} y un cociente de TX agregados "
                     f"{comparison(groups, a, b, 'tx_mb_total')}. Un valor mayor que 1 favorece la variante jerárquica."
                     + bcast_text + "\n\n")
    for red in ("Ethernet", "Wi-Fi"):
        a = keys("matriz", red, 3072, 64, 4, "1d")
        b = keys("matriz", red, 3072, 64, 4, "2d")
        notes.append(f"En {red}, 1D frente a SUMMA 2D, ambos con $P=64$, dio un cociente de tiempos "
                     f"{comparison(groups, a, b, 'T_Total')} y un cociente de TX agregados "
                     f"{comparison(groups, a, b, 'tx_mb_total')}. Un valor menor que 1 favorece 1D.\n\n")
    for red in ("Ethernet", "Wi-Fi"):
        a = keys("bcast", red, 3072, 16, 4, "world")
        b = keys("bcast", red, 3072, 16, 4, "hier")
        notes.append(f"En la difusión aislada por {red}, la colectiva global frente a la jerárquica dio un cociente de tiempo "
                     f"{comparison(groups, a, b, 'T_Bcast')} y de TX agregado "
                     f"{comparison(groups, a, b, 'tx_mb_total')}.\n\n")
    a = keys("bcast", "Ethernet", 3072, 16, 4, "world")
    b = keys("bcast", "Ethernet", 3072, 16, 1, "world")
    notes.append(f"Con 16 procesos y difusión global por Ethernet, cuatro nodos frente a uno dieron un cociente "
                 f"{comparison(groups, a, b, 'T_Bcast')}.\n\n")
    for red in ("Ethernet", "Wi-Fi"):
        a = keys("matriz", red, 3072, 96, 4, "1d")
        b = keys("matriz", red, 3072, 24, 1, "1d")
        notes.append(f"En {red}, cuatro nodos con 96 procesos frente a un nodo con 24 procesos dieron un cociente "
                     f"$T_{{96}}/T_{{24}}$ de {comparison(groups, a, b, 'T_Total')}. Aquí un valor mayor que 1 favorece un nodo.\n\n")
    for n in (6144, 7168):
        a = keys("matriz", "Ethernet", n, 96, 4, "1d")
        b = keys("matriz", "Ethernet", n, 24, 1, "1d")
        notes.append(f"Para $N={n}$ por Ethernet, $T_{{96}}/T_{{24}}$ fue "
                     f"{comparison(groups, a, b, 'T_Total')}.\n\n")
    for n in (100000000, 100000000000):
        for p in (24, 96):
            a = keys("trapecio", "Ethernet", n, p, 1 if p == 24 else 4, "simetrico")
            b = keys("trapecio", "Ethernet", n, p, 1 if p == 24 else 4, "asimetrico")
            ntext = "10^8" if n == 100000000 else "10^{11}"
            notes.append(f"Trapecio con $n={ntext}$ y $P={p}$: $T_{{sim}}/T_{{asim}}$ fue "
                         f"{comparison(groups, a, b, 'T_Total')}.\n\n")
    (ROOT / "conclusiones_optimizacion.tex").write_text("\n".join(notes))

    all_ok = sum(r["estado"] == "ok" for r in rows)
    failures = [r for r in rows if r["estado"] != "ok"]
    records = f"Se guardaron {len(rows)} intentos, de los cuales {all_ok} terminaron y entregaron una línea de resultado válida."
    if failures:
        records += " Los intentos fallidos o vencidos aparecen en el CSV y conservan su log; no se sustituyen por una cifra estimada."
    (ROOT / "estado_optimizacion.tex").write_text(records + "\n")
    make_plots(groups)


def make_plots(groups):
    figdir = ROOT / "img"
    figdir.mkdir(exist_ok=True)
    def bars(categories, variants, field, name, title):
        fig, ax = plt.subplots(figsize=(10.2, 4.5))
        palette = ["#284b63", "#8e6c4e", "#658b63", "#9a7192"]
        width = 0.78 / len(variants)
        for j, (label, variant) in enumerate(variants):
            xs, ys, lo, hi = [], [], [], []
            for i, (red, p, nodos, kind) in enumerate(categories):
                vv = values(groups.get((kind, red, 3072, p, nodos, variant), []), field)
                if not vv:
                    continue
                med = stats.median(vv)
                xs.append(i - 0.39 + width * (j + 0.5))
                ys.append(med)
                lo.append(med - min(vv))
                hi.append(max(vv) - med)
            if xs:
                ax.bar(xs, ys, width=width * 0.92, label=label, color=palette[j],
                       yerr=[lo, hi], capsize=2, linewidth=0.3, edgecolor="black")
        ax.set_xticks(range(len(categories)), [f"{r}\nP={p}, {n} nodo{'s' if n > 1 else ''}" for r, p, n, _ in categories])
        ax.set_yscale("log")
        ax.set_ylabel("Segundos (escala logarítmica)")
        ax.set_title(title)
        ax.grid(axis="y", alpha=0.25)
        if ax.has_data():
            ax.legend(ncol=len(variants), loc="upper center", bbox_to_anchor=(0.5, -0.17), frameon=False)
        fig.tight_layout()
        fig.savefig(figdir / name, dpi=180, bbox_inches="tight")
        plt.close(fig)
    bars([(red, p, 1 if p == 24 else 4, "matriz") for red in ("Ethernet", "Wi-Fi") for p in (24, 96)],
         [("1D global", "1d"), ("1D jerárquica", "1d-hier")], "T_Total",
         "optimizacion_matrices.png", "Multiplicación completa, N=3072")
    bars([(red, 16, 4, "bcast") for red in ("Ethernet", "Wi-Fi")],
         [("Global", "world"), ("Jerárquica", "hier"),
          ("Knomial", "tuned-knomial"), ("Scatter/allgather", "tuned-scatter")],
         "T_Bcast", "optimizacion_bcast.png", "Difusión aislada de B, 75.5 MB")
    fig, ax = plt.subplots(figsize=(8.5, 4.4))
    for p, label, color in ((24, "Un nodo, 24 procesos", "#284b63"),
                            (96, "Cuatro nodos, 96 procesos", "#8e6c4e")):
        xs, ys, lo, hi = [], [], [], []
        for n in (3072, 6144, 7168):
            v = values(groups.get(("matriz", "Ethernet", n, p, 1 if p == 24 else 4, "1d"), []), "T_Total")
            if v:
                med = stats.median(v)
                xs.append(n); ys.append(med); lo.append(med - min(v)); hi.append(max(v) - med)
        if xs:
            ax.errorbar(xs, ys, yerr=[lo, hi], marker="o", linewidth=2, capsize=3,
                        color=color, label=label)
    ax.set_yscale("log")
    ax.set_xticks((3072, 6144, 7168))
    ax.set_xlabel("Dimensión N de la matriz")
    ax.set_ylabel("Tiempo total (s, escala logarítmica)")
    ax.set_title("Escalamiento por tamaño en Ethernet")
    ax.grid(alpha=0.25)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(figdir / "optimizacion_tamano.png", dpi=180)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path, nargs="+")
    args = parser.parse_args()
    build([p.resolve() for p in args.csv])
    for _ in range(2):
        subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "informe_optimizacion.tex"],
                       cwd=ROOT, stdout=subprocess.DEVNULL, check=True)
    print(ROOT / "informe_optimizacion.pdf")


if __name__ == "__main__":
    main()
