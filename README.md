# Estudio Experimental y Optimización en Clúster MPI de 96 Núcleos

**Universidad Nacional de San Agustín (UNSA)**  
**Departamento Académico de Ingeniería de Sistemas e Informática**  
**Escuela Profesional de Ciencia de la Computación**  
* **Curso:** Computación Paralela y Distribuida  
* **Docente:** Alvaro Henry Mamani Aliaga  
* **Integrantes:**  
  * Paredes Malaga José Carlos  
  * Alvarez Astete Jheeremy Manuel  
  * Machaca Muñiz Jose Alejandro  
  * Tamo Turpo David  
  * Ramos Wilson  
* **Fecha:** Septiembre de 2026  

---

## 📌 Documento Principal Recomendado

> [!IMPORTANT]
> El informe final oficial, revisado por pares y con auditoría estadística completa es:  
> 📄 [**`revision/informe_mejorado.pdf`**](revision/informe_mejorado.pdf) *(37 páginas, compilado y listo para lectura)*.

### Mapa de Informes en el Repositorio

| Archivo | Ubicación | Páginas | Descripción |
| :--- | :--- | :---: | :--- |
| **`informe_mejorado.pdf`** | [**`revision/`**](revision/informe_mejorado.pdf) | **37** | **DOCUMENTO DEFINITIVO RECOMENDADO.** Incluye auditoría automática de las 243 corridas, análisis de variabilidad y dispersión, modelos de memoria y conclusiones corregidas. |
| `informe_final.pdf` | [Raíz](informe_final.pdf) | 39 | Versión integrada previa que compila las tres etapas históricas. |
| `informe_optimizacion.pdf` | [Raíz](informe_optimizacion.pdf) | 8 | Resumen técnico acotado exclusivamente a la campaña de optimización. |
| `main.pdf` | [Raíz](main.pdf) | 32 | Versión histórica original con la primera batería y la batería ampliada. |

---

## 🔬 Resumen del Proyecto

Este estudio investiga el rendimiento, la escalabilidad, la memoria y el comportamiento de la red de dos algoritmos fundamentales de computación científica:
1. **Multiplicación de matrices** $C = A \times B$ ($N \in [512, 7168]$) mediante descomposiciones en franjas 1D, 1D jerárquica y bloques 2D (algoritmo SUMMA).
2. **Integración numérica por la regla del trapecio** ($n \in [10^8, 10^{11}]$) con evaluación de partición simétrica clásica vs. partición asimétrica calibrada para arquitecturas híbridas.

El clúster experimental consta de **4 nodos físicos** interconectados mediante **Ethernet Gigabit (1 Gbps)** y **Wi-Fi 5 GHz (802.11ac)**, equipados con procesadores **Intel Core Ultra 9 285** (24 núcleos físicos por nodo: 8 P-cores Lion Cove + 16 E-cores Skymont), totalizando **96 núcleos físicos de cómputo**.

---

## 📊 Hallazgos y Resultados Clave

El proyecto documenta y respalda experimentalmente **243 ejecuciones controladas**:

```
                              RESUMEN DE RESULTADOS CLAVE
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│ 1. MPI_Bcast Optimizado:                                                                 │
│    El algoritmo por defecto de Open MPI 4.1.6 (scatter-allgather) enviaba >1,000 MB.     │
│    Con difusión jerárquica o árbol K-nomial, el tráfico bajó a 228 MB (-77%),             │
│    acelerando la difusión en 4.50× en Wi-Fi (133 s → 29.5 s) y 2.17× en Ethernet.        │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│ 2. Matrices 1D-Jerárquicas (N=3072, P=96):                                              │
│    La variante 1d-hier redujo el tiempo total en 1.96× en Wi-Fi (101 s → 51 s)           │
│    y en 1.95× en Ethernet (6.26 s → 3.22 s), cortando el tráfico TX de red a la mitad.  │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│ 3. 1D vs. 2D SUMMA (P=64):                                                              │
│    1D superó a SUMMA 2D tanto en Ethernet (3.15 s vs 5.49 s) como en Wi-Fi (51.7 s vs    │
│    87.3 s), debido a que SUMMA genera casi el doble de tráfico por difusión de paneles.  │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│ 4. Matrices Masivas y Punto de Cruce (N=6144 y 7168):                                   │
│    1 nodo local (24 núcleos) sigue ganando en matrices de hasta 7168 por el bus DDR5     │
│    a 44.8 GB/s. Sin embargo, para N > 36,000 la memoria de 32 GB se agota y el clúster │
│    de 128 GB es la única opción computacionalmente viable.                               │
├──────────────────────────────────────────────────────────────────────────────────────────┤
│ 5. Trapecio Asimétrico (Lion Cove vs Skymont):                                           │
│    Calibrar pesos según IPC real (w_P / w_E = 1.2658) y corregir el extremo numérico    │
│    f(1)/2 logró una aceleración de 1.19× en cómputo local puro para 10^11 trapecios.    │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Guía de Replicación y Reproducibilidad

El repositorio implementa una separación estricta entre la **reconstrucción autónoma** (que no necesita red) y la **re-ejecución en vivo** en el hardware del laboratorio.

Para consultar los detalles completos de la infraestructura de auditoría, lee [**`REPRODUCIBILIDAD.md`**](REPRODUCIBILIDAD.md).

### Caso A: Reconstruir el Informe y las Figuras (100% Autónomo, sin Clúster)
*No requiere conexión SSH ni que los nodos estén encendidos.* Lee las copias locales de evidencia y compila el documento en segundos:

```bash
git clone https://github.com/dtamotu/cluster-mpi-96-optimizaciones.git
cd cluster-mpi-96-optimizaciones/revision

# Regenera auditoría, tablas, figuras y el PDF oficial:
./compilar.sh
```
*Requisitos:* Linux con Python 3 (`numpy`, `matplotlib`) y `pdflatex` con paquetes estándar.

---

### Caso B: Auditar la Evidencia Criptográfica
Comprueba que los resultados del informe coinciden línea por línea con las salidas de consola y los hashes SHA-256:

```bash
cd cluster-mpi-96-optimizaciones/revision
python3 auditar_evidencia.py
```
*Salida esperada:* `0 discrepancias` en 50 filas de Batería 1, 75 filas de Batería 2 y 118 filas de la Campaña de Optimización.

---

### Caso C: Repetir la Campaña de Optimización en el Clúster Físico
Requiere que los 4 nodos (`servidor`, `workers1`, `workers2`, `workers4`) estén encendidos y accesibles por SSH en la subred Ethernet `10.7.50.0/24` o Wi-Fi `10.7.134.0/23`:

```bash
cd cluster-mpi-96-optimizaciones

# 1. Compila los programas y los distribuye a /var/tmp en los workers:
./preparar.sh

# 2. Ejecuta la batería completa con control de timeout (420 s por prueba):
./ejecutar_todo.sh 420
```

---

## 📁 Estructura del Repositorio

```
cluster-mpi-96-optimizaciones/
├── README.md                      # Esta guía general de navegación
├── REPRODUCIBILIDAD.md            # Protocolo detallado de reproducibilidad y auditoría
├── OPTIMIZACIONES.md              # Bitácora técnica de las optimizaciones algorítmicas
│
├── revision/                      # 🌟 ENTORNO DE EDICIÓN Y REVISIÓN DEFINITIVA
│   ├── informe_mejorado.pdf       # 👉 El PDF final recomendado (37 páginas)
│   ├── compilar.sh                # Script de compilación del informe mejorado
│   ├── auditar_evidencia.py       # Auditor forense de CSVs, logs y SHA-256
│   ├── generar_analisis.py        # Generador de gráficos de dispersión y memoria
│   ├── generar_optimizacion.py    # Generador de tablas estadísticas de optimización
│   └── tablas/ e img/             # Fuentes tabulares y figuras vectoriales
│
├── src/                           # Código fuente C optimizado
│   ├── mpi_matrix_2d.c            # Multiplicación 1D, 1D-hier y 2D SUMMA
│   ├── bcast_bench.c              # Microbenchmark de difusión aislada con hash FNV-1a
│   ├── trapecio_asimetrico.c      # Integración con balanceo P/E y borde analítico
│   └── kernels.h                  # Micro-kernels de álgebra (ijk, ikj, tiled-64)
│
├── scripts/                       # Lanzadores y configuraciones de red
│   ├── ssh_config                 # Configuración de salto para Ethernet (10.7.50.x)
│   ├── ssh_config_wifi            # Configuración de salto para Wi-Fi (10.7.134.x)
│   └── lanzar.sh, medir.sh        # Scripts utilitarios de ejecución
│
├── datos/                         # Evidencia histórica de las dos primeras baterías
│   ├── ethernet/ y wifi/          # Logs originales de la Batería 1 (50 ejecuciones)
│   ├── ampliada/                  # Logs y CSVs de la Batería Ampliada (75 ejecuciones)
│   └── procedencia.json           # Trazabilidad de archivos y hashes
│
└── resultados_optimizacion/       # Campaña de optimización controlada
    ├── 20260925_074354/           # 82 ejecuciones principales (matrices 3072, bcast)
    ├── 20260925_extra/            # 36 ejecuciones extra (matrices 6144/7168, trapecio)
    └── SHA256SUMS                 # Firmas criptográficas de inmutabilidad
```

---

## 🛠️ Tecnologías y Requisitos

* **Sistema Operativo:** Linux (Ubuntu 24.04 LTS / Debian)
* **Compilador C:** GCC 13+ con soporte para `C11`, banderas `-O3 -Wall -Wextra`
* **Librería MPI:** Open MPI 4.1.6 (con componentes MCA `btl`, `vader`, `coll_tuned`)
* **Procesadores:** Intel(R) Core(TM) Ultra 9 285 (Arrow Lake, 24 núcleos físicos por nodo)
* **Tipos de Red:**
  * Cableada: Gigabit Ethernet 1000BASE-T (`10.7.50.0/24`)
  * Inalámbrica: Wi-Fi 5 GHz 802.11ac canal 161 (`10.7.134.0/23`)

---

## 📜 Licencia y Cita Académica

Proyecto académico desarrollado para el curso de **Computación Paralela y Distribuida** de la **Universidad Nacional de San Agustín (UNSA)**.  
Repositorio público: [github.com/dtamotu/cluster-mpi-96-optimizaciones](https://github.com/dtamotu/cluster-mpi-96-optimizaciones)
