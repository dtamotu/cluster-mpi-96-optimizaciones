#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
export MPLCONFIGDIR="$PWD/tmp/matplotlib"
mkdir -p "$MPLCONFIGDIR" tmp

# Regenera la evidencia histórica y la campaña controlada sin ejecutar MPI.
python3 generar_datos.py
python3 generar_informe_optimizacion.py \
  resultados_optimizacion/20260925_074354/resultados.csv \
  resultados_optimizacion/20260925_extra/resultados.csv

for pasada in 1 2 3; do
  pdflatex -interaction=nonstopmode -halt-on-error informe_final.tex \
    > "tmp/latex_final_${pasada}.log"
done
echo "PDF generado: $PWD/informe_final.pdf"
