# Reproducibilidad del estudio MPI

## ¿Se puede reproducir todo desde GitHub?

Sí, pero hay que distinguir entre reconstruir el informe, consultar las mediciones guardadas y volver a ejecutar las pruebas en el clúster.

| Objetivo | Estado |
|---|---|
| Reconstruir el informe y sus figuras | Completamente reproducible desde el repositorio. |
| Consultar las mediciones originales | Sí: están los CSV, JSON y logs. |
| Repetir la campaña de optimización de 118 corridas | Sí, si se dispone del clúster y del entorno MPI. |
| Repetir exactamente las baterías históricas | Las fuentes y scripts están disponibles, pero los binarios históricos deben prepararse manualmente. |
| Reproducir exactamente el estado de la red, frecuencia, carga y Wi-Fi | No puede garantizarse desde Git; esas condiciones dependen del momento de ejecución. |

El repositorio es público y de libre acceso en GitHub para su clonación y replicación.

## Mediciones almacenadas

El repositorio contiene:

- 50 logs de la primera batería.
- 75 logs de la batería ampliada.
- 118 corridas válidas de la campaña de optimización, con logs, comandos, contadores TX/RX, entorno y hashes SHA-256.
- Corridas piloto y de humo.
- JSON históricos de la ejecución de 906 s, caché, tráfico y mediodía.
- Código C, scripts MPI, configuraciones SSH, CSV y fuentes LaTeX.

En total hay 260 archivos de log versionados, incluyendo las pruebas históricas, la campaña válida y los pilotos.

## Alcance de las mediciones

No todas las campañas midieron las mismas variables:

- La primera batería registra tiempos y resultados numéricos, pero no tráfico por nodo.
- La batería ampliada registra TX+RX únicamente del servidor.
- La campaña de optimización registra TX/RX de los nodos participantes.
- No se capturaron paquetes, frecuencia de CPU, RSS de memoria ni contadores detallados de retransmisiones.

Por tanto, el repositorio contiene todas las mediciones que realmente se realizaron, pero no datos que nunca fueron capturados.

## Repetir la campaña actual

Esto requiere cuatro nodos accesibles por SSH, Open MPI, `mpicc`, las mismas interfaces de red y las direcciones configuradas en los scripts.

```bash
git clone https://github.com/dtamotu/cluster-mpi-96-optimizaciones.git
cd cluster-mpi-96-optimizaciones

./preparar.sh
./ejecutar_todo.sh 420
```

`preparar.sh` compila los programas actuales y distribuye los ejecutables a los workers. `ejecutar_todo.sh` ejecuta las pruebas piloto, las 82 corridas principales y las 36 corridas adicionales de la campaña.

Las claves privadas SSH no están en GitHub. Deben configurarse localmente y los nombres, usuarios, direcciones IP e interfaces deben coincidir con los archivos de `scripts/`.

## Reconstruir el informe con las mediciones guardadas

Esta operación no necesita que los nodos estén conectados:

```bash
cd cluster-mpi-96-optimizaciones/revision
./compilar.sh
```

El comando regenera las tablas, figuras, auditoría y el PDF a partir de los datos versionados.

## Incorporar una campaña nueva

Una campaña nueva se guarda en una carpeta con fecha dentro de `resultados_optimizacion/`. El informe actual utiliza las carpetas archivadas de la campaña que produjo los resultados publicados. Para que una campaña nueva aparezca en el PDF, hay que incorporarla explícitamente al generador de análisis y volver a compilar.

## Archivos principales

- `revision/informe_mejorado.pdf`: informe profundo regenerado.
- `revision/compilar.sh`: reconstrucción del informe.
- `revision/generar_analisis.py`: análisis de repeticiones, tráfico por nodo, memoria y tiempo de pared.
- `datos/`: mediciones de las baterías inicial y ampliada.
- `resultados_optimizacion/`: logs y resultados de la campaña de optimización.
- `src/`: fuentes C actuales.
- `fuentes/codigo_baterias/`: fuentes recuperadas de las baterías históricas.
- `scripts/`: lanzadores Ethernet/Wi-Fi y configuración SSH.

Repositorio: <https://github.com/dtamotu/cluster-mpi-96-optimizaciones>
