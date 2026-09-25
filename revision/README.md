# Informe MPI de 96 núcleos: versión revisada

Versión revisada del informe LaTeX, integrada en el mismo repositorio. El PDF
resultante es `informe_mejorado.pdf`. Los scripts de esta carpeta **leen** la
evidencia (CSV, logs, JSON y sellos SHA-256) de la carpeta principal y escriben
los resultados de la reconstrucción solo aquí.

## Reconstrucción

```bash
cd /home/alumno16/cluster-mpi-96-optimizaciones/revision
./compilar.sh
```

Para leer la evidencia desde otra ubicación:
`EVIDENCIA_MPI=/ruta/al/repositorio ./compilar.sh`.

| Script | Qué genera |
|---|---|
| `generar_datos.py` | Tablas y figuras de las baterías y series históricas (copia adaptada del original; mismas cifras). |
| `generar_optimizacion.py` | Tabla resumen, tabla completa, repeticiones del trapecio y tres figuras de la campaña. |
| `auditar_evidencia.py` | Auditoría automática (`tablas/auditoria.tex`, `datos/auditoria.json`) y tablas de variabilidad. |

## Cambios respecto de `informe_final.tex`

**Contenido nuevo**
- Sección *Una corrida frente a repeticiones*: compara las corridas únicas de las
  baterías con las medianas de la campaña. Con 96 procesos coinciden dentro de un
  2 %; con 24 procesos la campaña es un 19–37 % más lenta, con la mayor parte
  de la diferencia en `T_Calc`.
- Sección *Auditoría de la evidencia*: las 243 filas coinciden con sus logs, las
  huellas son consistentes y los sellos SHA-256 están intactos. También documenta
  los problemas hallados:
  - `bateria_expandida/.../analisis/` contiene solo gráficos Wi-Fi (se sobrescribió la versión Ethernet);
  - el hash de `mpi_matrix_2d.c` en `procedencia.json` corresponde a la versión modificada;
  - la campaña se compiló sin `-march=native -funroll-loops`, a diferencia de las baterías;
  - hay afirmaciones de los borradores `.md` que los logs no respaldan.
- La campaña incluye una tabla resumen con cocientes y solapamiento de rangos, el
  resultado `knomial` (TX similar y mediana 3 % menor que la difusión jerárquica
  en el microbenchmark, sin cambiar el código) y
  las tres repeticiones del trapecio con el desbalance leído de cada log.

**Correcciones**
- El resumen atribuía al trapecio asimétrico una ventaja; con medianas y rangos no es concluyente.
- "Los gráficos usan escala lineal" era falso para las figuras de la campaña (logarítmicas).
- La cifra de 6.52× para N=6144 procede de una sola corrida; ahora se contrasta con la mediana de 4.77×.
- En los anexos, la ruta (`informe_actual_96`) y el archivo (`main.tex`) de reconstrucción estaban desactualizados.
- `Wi--Fi` y `1d--hier` se imprimían con raya (–) en la tabla de la campaña.

**Estructura y presentación**
- Las conclusiones se unificaron y ahora van después de la campaña; antes la precedían.
- Se añadió una tabla de "Respuestas breves" en el resumen ejecutivo.
- Se quitaron 26 `\clearpage` que dejaban páginas medio vacías.
- Las figuras de la campaña están en PDF vectorial y muestran el valor de cada mediana.
