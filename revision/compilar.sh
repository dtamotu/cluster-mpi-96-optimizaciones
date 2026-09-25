#!/usr/bin/env bash
# Regenera tablas, figuras y auditoría desde la evidencia (solo lectura) y compila el PDF.
set -euo pipefail
cd -- "$(dirname -- "$0")"
export MPLCONFIGDIR="$PWD/tmp/matplotlib"
mkdir -p "$MPLCONFIGDIR" tmp

python3 generar_datos.py
python3 generar_optimizacion.py
python3 auditar_evidencia.py

for pasada in 1 2 3; do
  pdflatex -interaction=nonstopmode -halt-on-error informe_mejorado.tex \
    > "tmp/latex_${pasada}.log"
done
echo "PDF generado: $PWD/informe_mejorado.pdf"
