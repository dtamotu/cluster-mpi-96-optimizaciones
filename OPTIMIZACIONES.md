# Experimentos de optimización MPI

Esta carpeta conserva el historial del proyecto original y contiene las fuentes,
binarios compilables, scripts, datos anteriores, mediciones nuevas y el informe
LaTeX. El repositorio original permanece independiente.

Repositorio derivado: https://github.com/dtamotu/cluster-mpi-96-optimizaciones

Origen: https://github.com/dtamotu/cluster-mpi-96

## Uso

```bash
cd /home/alumno16/cluster-mpi-96-optimizaciones
./preparar.sh
python3 experimentos.py plan
python3 experimentos.py smoke
python3 experimentos.py run --timeout 420
python3 experimentos.py extra
python3 auditar_resultados.py resultados_optimizacion/FECHA resultados_optimizacion/OTRA_FECHA
python3 generar_informe_optimizacion.py resultados_optimizacion/FECHA/resultados.csv resultados_optimizacion/OTRA_FECHA/resultados.csv
# O bien ejecutar preparación, prueba corta, batería e informe:
./ejecutar_todo.sh
```

`experimentos.py run --dir resultados_optimizacion/FECHA` reanuda una batería
interrumpida sin repetir los identificadores ya escritos. Cada caso guarda un
log con el comando exacto, la salida y contadores TX/RX por nodo. El CSV se
sincroniza a disco después de cada intento. Un error o vencimiento queda
registrado, sin inventar un tiempo. El límite por defecto es 420 s por corrida.

Los binarios se compilan dentro de `bin/` y `preparar.sh` los copia a
`/var/tmp/cluster-mpi-96-optimizaciones/bin` en los trabajadores. Esa copia
temporal es necesaria porque MPI inicia procesos en otras computadoras; el
proyecto y todos los resultados permanecen en la carpeta local.

## Comparaciones

- Cinco repeticiones de matrices 1D y 1D jerárquica con 24 y 96 procesos,
  por Ethernet y Wi-Fi, tamaño 3072.
- Difusión aislada de una matriz de 75.497 MB con 16 procesos: un nodo frente
  a cuatro; difusión global, jerárquica y algoritmos `knomial` y
  `scatter_allgather` solicitados a Open MPI `tuned`.
- Matrices 1D frente a SUMMA 2D con 64 procesos en cuatro nodos. La versión
  2D existente exige un número cuadrado de procesos y no acepta 96.
- Tamaños 6144 y 7168 por Ethernet, con 24 y 96 procesos.
- Trapecio simétrico y asimétrico, con el extremo numérico corregido, para
  \(10^8\) y \(10^{11}\) trapecios y 24/96 procesos.

El informe nuevo es [informe_optimizacion.tex](informe_optimizacion.tex). La
fuente principal del informe histórico, [main.tex](main.tex), se conserva.

## Interpretación

`T_Total` del programa de matrices y `T_Bcast` del microbenchmark se calculan
con `MPI_Wtime`; no incluyen el arranque de MPI. `pared_s` sí incluye ese
arranque, SSH y lectura de contadores. Los máximos de las fases pueden provenir
de procesos distintos, de modo que no se suman para reconstruir `T_Total`.

`tx_mb_total` y `rx_mb_total` suman cambios de contador de las interfaces en
los nodos participantes; pueden contener tráfico de control o ajeno. Los logs
guardan los valores por nodo. Las pruebas de matrices verifican suma diagonal
y suma ponderada; la difusión aislada compara una huella del búfer completo
entre todos los procesos.
