#!/usr/bin/env python3
"""Tablas y figuras de la campaña de optimización; no ejecuta MPI.

Lee los CSV y logs de resultados_optimizacion/ del repositorio original
(solo lectura) y escribe en tablas/ e img/ de esta carpeta.
"""
from __future__ import annotations

import csv
import os
import re
import statistics as stats
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("EVIDENCIA_MPI", OUT.parent)).resolve()
CAMPANAS = [ROOT / "resultados_optimizacion" / "20260925_074354",
            ROOT / "resultados_optimizacion" / "20260925_extra"]
COLORES = ["#244F73", "#A45B43", "#2F756F", "#7A6A8C"]
plt.rcParams.update({"font.size": 10, "axes.titlesize": 11,
                     "font.family": "DejaVu Sans", "pdf.fonttype": 42})


def cargar():
    filas = []
    for carpeta in CAMPANAS:
        for fila in csv.DictReader((carpeta / "resultados.csv").open()):
            fila["_log"] = carpeta / fila["log"]
            filas.append(fila)
    grupos = defaultdict(list)
    for f in filas:
        if f["estado"] == "ok":
            grupos[(f["kind"], f["red"], int(f["n"]), int(f["p"]), int(f["nodos"]), f["variante"])].append(f)
    return filas, grupos


def valores(grupo, campo):
    return [float(f[campo]) for f in grupo if f.get(campo)]


def mediana(grupos, clave, campo):
    v = valores(grupos.get(clave, []), campo)
    return stats.median(v) if v else None


def rango(grupos, clave, campo):
    v = valores(grupos.get(clave, []), campo)
    return (min(v), max(v)) if v else None


def num(x, dec=3):
    return f"{x:.{dec}f}"


def celda(s):
    return str(s).replace("_", r"\_")


def escribir(nombre, texto):
    (OUT / "tablas" / nombre).write_text(texto)


def tabla_detalle(grupos):
    lineas = [r"\begin{longtable}{llrrrlrrrr}",
              r"\caption{Campaña de optimización: medianas de las corridas válidas, con mínimo y máximo. "
              r"TX suma la transmisión de las interfaces de los nodos participantes.}\label{tab:opt-detalle}\\",
              r"\toprule Red & Prueba & Tamaño & $P$ & Nodos & Variante & Reps. & $T$ med. (s) & Rango (s) & TX (MB) \\",
              r"\midrule\endfirsthead",
              r"\toprule Red & Prueba & Tamaño & $P$ & Nodos & Variante & Reps. & $T$ med. (s) & Rango (s) & TX (MB) \\",
              r"\midrule\endhead"]
    for clave in sorted(grupos):
        tipo, red, n, p, nodos, variante = clave
        campo = "T_Bcast" if tipo == "bcast" else "T_Total"
        t = valores(grupos[clave], campo)
        tx = valores(grupos[clave], "tx_mb_total")
        ntexto = "$10^{8}$" if n == 10**8 else "$10^{11}$" if n == 10**11 else str(n)
        lineas.append(f"{celda(red)} & {celda(tipo)} & {ntexto} & {p} & {nodos} & {celda(variante)} & {len(t)} & "
                      f"{num(stats.median(t))} & {num(min(t))}--{num(max(t))} & "
                      f"{num(stats.median(tx), 1) if tx else '--'} " + r"\\")
    lineas.append(r"\bottomrule\end{longtable}")
    escribir("optimizacion_detalle.tex", "\n".join(lineas) + "\n")


def tabla_resumen(grupos):
    """Comparaciones clave A/B con cociente de tiempos, de TX y solapamiento de rangos."""
    M = lambda red, n, p, nodos, var: ("matriz", red, n, p, nodos, var)
    B = lambda red, nodos, var: ("bcast", red, 3072, 16, nodos, var)
    T = lambda n, p, var: ("trapecio", "Ethernet", n, p, 1 if p == 24 else 4, var)
    casos = [
        ("Difusión de $B$ en la multiplicación completa ($N=3072$, $P=96$, 4 nodos)", None, None, None),
        ("1D global / 1D jerárquica", "Ethernet", M("Ethernet", 3072, 96, 4, "1d"), M("Ethernet", 3072, 96, 4, "1d-hier")),
        ("1D global / 1D jerárquica", "Wi-Fi", M("Wi-Fi", 3072, 96, 4, "1d"), M("Wi-Fi", 3072, 96, 4, "1d-hier")),
        ("Difusión aislada de 75.5 MB ($P=16$)", None, None, None),
        ("Global / jerárquica, 4 nodos", "Ethernet", B("Ethernet", 4, "world"), B("Ethernet", 4, "hier")),
        ("Global / jerárquica, 4 nodos", "Wi-Fi", B("Wi-Fi", 4, "world"), B("Wi-Fi", 4, "hier")),
        (r"\texttt{knomial} / jerárquica, 4 nodos", "Ethernet", B("Ethernet", 4, "tuned-knomial"), B("Ethernet", 4, "hier")),
        (r"\texttt{knomial} / jerárquica, 4 nodos", "Wi-Fi", B("Wi-Fi", 4, "tuned-knomial"), B("Wi-Fi", 4, "hier")),
        ("Global: 4 nodos / 1 nodo", "Ethernet", B("Ethernet", 4, "world"), B("Ethernet", 1, "world")),
        ("Partición del problema ($N=3072$, $P=64$, 4 nodos)", None, None, None),
        ("1D / SUMMA 2D", "Ethernet", M("Ethernet", 3072, 64, 4, "1d"), M("Ethernet", 3072, 64, 4, "2d")),
        ("1D / SUMMA 2D", "Wi-Fi", M("Wi-Fi", 3072, 64, 4, "1d"), M("Wi-Fi", 3072, 64, 4, "2d")),
        ("Cuatro nodos frente a uno (1D global)", None, None, None),
        (r"$T_{96}/T_{24}$, $N=3072$", "Ethernet", M("Ethernet", 3072, 96, 4, "1d"), M("Ethernet", 3072, 24, 1, "1d")),
        (r"$T_{96}/T_{24}$, $N=3072$", "Wi-Fi", M("Wi-Fi", 3072, 96, 4, "1d"), M("Wi-Fi", 3072, 24, 1, "1d")),
        (r"$T_{96}/T_{24}$, $N=6144$", "Ethernet", M("Ethernet", 6144, 96, 4, "1d"), M("Ethernet", 6144, 24, 1, "1d")),
        (r"$T_{96}/T_{24}$, $N=7168$", "Ethernet", M("Ethernet", 7168, 96, 4, "1d"), M("Ethernet", 7168, 24, 1, "1d")),
        ("Reparto del trapecio: simétrico / asimétrico", None, None, None),
        (r"$n=10^8$, $P=24$", "Ethernet", T(10**8, 24, "simetrico"), T(10**8, 24, "asimetrico")),
        (r"$n=10^8$, $P=96$", "Ethernet", T(10**8, 96, "simetrico"), T(10**8, 96, "asimetrico")),
        (r"$n=10^{11}$, $P=24$", "Ethernet", T(10**11, 24, "simetrico"), T(10**11, 24, "asimetrico")),
        (r"$n=10^{11}$, $P=96$", "Ethernet", T(10**11, 96, "simetrico"), T(10**11, 96, "asimetrico")),
    ]
    lineas = [r"\begin{center}\small",
              r"\begin{tabular}{p{4.6cm}lrrrrc}",
              r"\toprule",
              r"Comparación A / B & Red & $\tilde T_A$ (s) & $\tilde T_B$ (s) & $\tilde T_A/\tilde T_B$ & TX$_A$/TX$_B$ & Rangos \\",
              r"\midrule"]
    for etiqueta, red, a, b in casos:
        if a is None:
            lineas.append(r"\addlinespace[2pt]\multicolumn{7}{l}{\textit{" + etiqueta + r"}} \\")
            continue
        campo = "T_Bcast" if a[0] == "bcast" else "T_Total"
        ta, tb = mediana(grupos, a, campo), mediana(grupos, b, campo)
        xa, xb = mediana(grupos, a, "tx_mb_total"), mediana(grupos, b, "tx_mb_total")
        ra, rb = rango(grupos, a, campo), rango(grupos, b, campo)
        separados = ra[1] < rb[0] or rb[1] < ra[0]
        tx = f"{xa / xb:.2f}" if xa and xb and xb > 1 else "--"
        dec = 4 if max(ta, tb) < 0.1 else 3
        solape = "separados" if separados else r"\textbf{solapan}"
        lineas.append(f"{etiqueta} & {celda(red)} & {num(ta, dec)} & {num(tb, dec)} & {ta / tb:.2f} & {tx} & "
                      f"{solape} " + r"\\")
    lineas += [r"\bottomrule", r"\end{tabular}", r"\end{center}"]
    escribir("optimizacion_resumen.tex", "\n".join(lineas) + "\n")


def leer_asym(log):
    linea = re.search(r"^RESULT_ASYM: (.*)$", log.read_text(errors="replace"), re.M).group(1)
    return dict(x.strip().split("=", 1) for x in linea.split(","))


def tabla_trapecio(filas):
    """Cada repetición del trapecio con su desbalance tomado del log."""
    datos = defaultdict(dict)
    for f in filas:
        if f["kind"] != "trapecio" or f["estado"] != "ok":
            continue
        campos = leer_asym(f["_log"])
        datos[(int(f["n"]), int(f["p"]))][(f["variante"], int(f["repeticion"]))] = (
            float(campos["T_Total"]), float(campos["Desbalance"]))
    lineas = [r"\begin{center}\small",
              r"\begin{tabular}{rrrrrrrr}",
              r"\toprule",
              r" & & \multicolumn{2}{c}{Rep. 1} & \multicolumn{2}{c}{Rep. 2} & \multicolumn{2}{c}{Rep. 3} \\",
              r"\cmidrule(lr){3-4}\cmidrule(lr){5-6}\cmidrule(lr){7-8}",
              r"$n$, $P$ & Reparto & $T$ (s) & Desb. & $T$ (s) & Desb. & $T$ (s) & Desb. \\",
              r"\midrule"]
    for n, p in sorted(datos):
        ntexto = "$10^{8}$" if n == 10**8 else "$10^{11}$"
        for variante in ("simetrico", "asimetrico"):
            celdas = []
            for rep in (1, 2, 3):
                t, d = datos[(n, p)][(variante, rep)]
                celdas += [num(t, 4 if t < 0.1 else 3), f"{d:.3f}"]
            etiqueta = f"{ntexto}, {p}" if variante == "simetrico" else ""
            lineas.append(f"{etiqueta} & {'simétrico' if variante == 'simetrico' else 'asimétrico'} & "
                          + " & ".join(celdas) + r" \\")
        lineas.append(r"\addlinespace[2pt]")
    lineas[-1] = r"\bottomrule"
    lineas += [r"\end{tabular}", r"\end{center}"]
    escribir("trapecio_repeticiones.tex", "\n".join(lineas) + "\n")


def guardar(fig, nombre):
    fig.savefig(OUT / "img" / f"{nombre}.pdf", bbox_inches="tight", metadata={"CreationDate": None})
    fig.savefig(OUT / "img" / f"{nombre}.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def etiqueta_tiempo(v):
    return f"{v:.3f}" if v < 10 else f"{v:.1f}"


def barras(grupos, categorias, variantes, campo, nombre, titulo):
    fig, ax = plt.subplots(figsize=(10.2, 4.6))
    ancho = 0.78 / len(variantes)
    for j, (etiqueta, variante) in enumerate(variantes):
        xs, ys, lo, hi = [], [], [], []
        for i, (red, p, nodos, tipo) in enumerate(categorias):
            v = valores(grupos.get((tipo, red, 3072, p, nodos, variante), []), campo)
            if not v:
                continue
            m = stats.median(v)
            xs.append(i - 0.39 + ancho * (j + 0.5)); ys.append(m)
            lo.append(m - min(v)); hi.append(max(v) - m)
        if not xs:
            continue
        ax.bar(xs, ys, width=ancho * 0.92, label=etiqueta, color=COLORES[j], edgecolor=COLORES[j],
               yerr=[lo, hi], capsize=2.5, error_kw={"ecolor": "#344550", "linewidth": 0.9})
        for x, y, h in zip(xs, ys, hi):
            ax.annotate(etiqueta_tiempo(y), (x, y + h), xytext=(0, 3), textcoords="offset points",
                        ha="center", va="bottom", fontsize=7.5)
    ax.set_xticks(range(len(categorias)),
                  [f"{r}\nP={p}, {n} nodo{'s' if n > 1 else ''}" for r, p, n, _ in categorias])
    ax.set_yscale("log")
    ax.set_ylabel("Segundos (escala logarítmica)")
    ax.set_title(titulo)
    ax.grid(axis="y", color="#DCE4E9", linewidth=0.7)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    bajo, alto = ax.get_ylim()
    ax.set_ylim(bajo, alto * 2.2)
    ax.legend(ncol=len(variantes), loc="upper center", bbox_to_anchor=(0.5, -0.17), frameon=False)
    fig.tight_layout()
    guardar(fig, nombre)


def figura_tamano(grupos):
    fig, ax = plt.subplots(figsize=(8.5, 4.4))
    for p, etiqueta, color in ((24, "Un nodo, 24 procesos", COLORES[0]),
                               (96, "Cuatro nodos, 96 procesos", COLORES[1])):
        xs, ys, lo, hi = [], [], [], []
        for n in (3072, 6144, 7168):
            v = valores(grupos.get(("matriz", "Ethernet", n, p, 1 if p == 24 else 4, "1d"), []), "T_Total")
            if v:
                m = stats.median(v)
                xs.append(n); ys.append(m); lo.append(m - min(v)); hi.append(max(v) - m)
        ax.errorbar(xs, ys, yerr=[lo, hi], marker="o", linewidth=1.8, capsize=3, color=color,
                    markerfacecolor="white", label=etiqueta)
        for x, y in zip(xs, ys):
            ax.annotate(etiqueta_tiempo(y), (x, y), xytext=(8, -3 if p == 24 else 5),
                        textcoords="offset points", fontsize=8.5, color=color)
    ax.set_yscale("log")
    ax.set_xticks((3072, 6144, 7168))
    ax.set_xlim(2700, 7700)
    ax.set_xlabel("Dimensión N de la matriz")
    ax.set_ylabel("Tiempo total (s, escala logarítmica)")
    ax.set_title("Escalamiento por tamaño en Ethernet (1D global)")
    ax.grid(color="#DCE4E9", linewidth=0.7)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, loc="upper left")
    fig.tight_layout()
    guardar(fig, "optimizacion_tamano")


def main():
    filas, grupos = cargar()
    (OUT / "tablas").mkdir(exist_ok=True)
    (OUT / "img").mkdir(exist_ok=True)
    tabla_detalle(grupos)
    tabla_resumen(grupos)
    tabla_trapecio(filas)
    barras(grupos, [(red, p, 1 if p == 24 else 4, "matriz") for red in ("Ethernet", "Wi-Fi") for p in (24, 96)],
           [("1D global", "1d"), ("1D jerárquica", "1d-hier")], "T_Total",
           "optimizacion_matrices", "Multiplicación completa, N=3072 (mediana, mínimo y máximo)")
    barras(grupos, [(red, 16, 4, "bcast") for red in ("Ethernet", "Wi-Fi")],
           [("Global", "world"), ("Jerárquica", "hier"),
            ("tuned knomial", "tuned-knomial"), ("tuned scatter/allgather", "tuned-scatter")],
           "T_Bcast", "optimizacion_bcast", "Difusión aislada de B (75.5 MB), 16 procesos en 4 nodos")
    figura_tamano(grupos)
    validas = sum(f["estado"] == "ok" for f in filas)
    print(f"Campaña: {len(filas)} intentos, {validas} válidos; tablas y 3 figuras regeneradas.")


if __name__ == "__main__":
    main()
