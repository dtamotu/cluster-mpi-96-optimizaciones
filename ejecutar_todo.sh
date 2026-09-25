#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
resultado="resultados_optimizacion/$(date +%Y%m%d_%H%M%S)"
./preparar.sh
python3 experimentos.py smoke --dir "$resultado/smoke"
python3 experimentos.py run --dir "$resultado" "${@}"
python3 generar_informe_optimizacion.py "$resultado/resultados.csv"
printf 'Datos: %s\nInforme: %s/informe_optimizacion.pdf\n' "$resultado" "$PWD"
