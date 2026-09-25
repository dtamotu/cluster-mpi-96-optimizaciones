# Informe actualizado: 96 núcleos, Ethernet y Wi-Fi

Esta copia derivada añade los experimentos de optimización en
[OPTIMIZACIONES.md](OPTIMIZACIONES.md). El informe revisado está en
[revision/informe_mejorado.tex](revision/informe_mejorado.tex) y su PDF en
[revision/informe_mejorado.pdf](revision/informe_mejorado.pdf). La revisión
incorpora auditoría de los datos, análisis de variabilidad y conclusiones
corregidas; el informe anterior permanece en [informe_final.tex](informe_final.tex).

Repositorio: [github.com/dtamotu/cluster-mpi-96-optimizaciones](https://github.com/dtamotu/cluster-mpi-96-optimizaciones) (privado).

Abrir `revision/informe_mejorado.pdf`. El documento conserva la carátula,
integrantes, curso y narrativa histórica; también integra la campaña de
optimización, una auditoría de las 243 ejecuciones y el análisis de las
repeticiones. `informe_optimizacion.pdf` queda como informe técnico acotado de
la campaña nueva.

## Reconstrucción

```bash
cd /home/alumno16/cluster-mpi-96-optimizaciones/revision
./compilar.sh
```

Requiere Python 3 con matplotlib/numpy, pdflatex y los paquetes LaTeX del informe
de referencia. La reconstrucción solo lee las copias de evidencia; no ejecuta MPI.

- `revision/informe_mejorado.tex`: portada y composición de la versión revisada.
- `revision/auditar_evidencia.py`: coteja CSV, logs, contadores y sellos.
- `revision/generar_optimizacion.py`: tabla resumen, repeticiones y figuras nuevas.
- `informe_final.tex`: versión integrada anterior a la revisión.
- `main.tex`: versión histórica del informe completo.
- `contenido.tex` y `ampliacion.tex`: metodología, resultados e interpretación.
- `anexos.tex`: configuración, comandos, scripts y fuentes.
- `generar_datos.py`: tablas, métricas, figuras y verificaciones de consistencia.
- `datos/`: CSV, logs y JSON originales de ambas baterías; procedencia y SHA-256.
- `fuentes/INFORME_ANALISIS_EXPANDIDO_96.md`: borrador preservado para contraste;
  los resultados citados en el PDF se cotejaron con CSV y logs.
- `src/` y `scripts/`: copias de código y lanzadores de las pruebas.
- `medir_trafico.sh`: herramienta opcional para una ejecución futura con contadores
  TX. No se ejecutó para generar los resultados del informe.

La campaña nueva usada por el informe revisado suma 82 ejecuciones de matrices y
difusión, más 36 ejecuciones extra de tamaños mayores y trapecio. Todas las 118
filas válidas fueron auditadas contra sus logs y selladas con SHA-256. El script
`revision/compilar.sh` vuelve a generar las tablas, figuras y el PDF usando esas
copias locales; no necesita que los cuatro nodos estén conectados.

Las dos baterías tienen una sola ejecución por configuración. La segunda suma
75 ejecuciones y registra TX+RX solo de la interfaz del servidor. Los MB de 1112
y 357–358 proceden de series históricas con otra medición de tráfico y no se
atribuyen a las baterías de 96 procesos. El caso de 906.351 s corresponde a
8 procesos, de los cuales 889.744 s se registraron en `MPI_Bcast(B)`.
Las seis figuras usan colores sobrios para Ethernet, Wi-Fi y la variante 2D;
cada punto o barra muestra su valor medido.

Referencias primarias: [FAQ Open MPI 4.x](https://www.open-mpi.org/faq/?category=tcp)
y [decisión fija de Bcast en Open MPI 4.1.6](https://github.com/open-mpi/ompi/blob/v4.1.6/ompi/mca/coll/tuned/coll_tuned_decision_fixed.c).
