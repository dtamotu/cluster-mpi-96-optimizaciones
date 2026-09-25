#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
timeout="${1:-420}"
[[ "$timeout" =~ ^[1-9][0-9]*$ ]] || { echo 'Uso: ./ejecutar_todo.sh [timeout_segundos]' >&2; exit 2; }
resultado="resultados_optimizacion/$(date +%Y%m%d_%H%M%S)"
./preparar.sh
python3 experimentos.py smoke --dir "$resultado/smoke" --timeout "$timeout"
python3 experimentos.py run --dir "$resultado" --timeout "$timeout"
python3 experimentos.py extra --dir "$resultado/extra" --timeout "$timeout"
python3 auditar_resultados.py "$resultado" "$resultado/extra"
python3 generar_informe_optimizacion.py "$resultado/resultados.csv" "$resultado/extra/resultados.csv"
printf 'Datos: %s\nInforme: %s/informe_optimizacion.pdf\n' "$resultado" "$PWD"
