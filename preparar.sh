#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p bin
mpicc -O3 -std=c11 -Wall -Wextra -o bin/mpi_matrix_2d src/mpi_matrix_2d.c -lm
mpicc -O3 -std=c11 -Wall -Wextra -o bin/bcast_bench src/bcast_bench.c

# MPI arranca los procesos en máquinas diferentes. El proyecto completo reside
# aquí; solo se copian los dos ejecutables al mismo directorio temporal de cada nodo.
stage=/var/tmp/cluster-mpi-96-optimizaciones/bin
mkdir -p "$stage"
cp bin/mpi_matrix_2d bin/bcast_bench "$stage/"
for host in 10.7.50.203 10.7.50.201 10.7.50.204; do
    ssh -F scripts/ssh_config "$host" "mkdir -p '$stage'"
    scp -q -F scripts/ssh_config bin/mpi_matrix_2d bin/bcast_bench "$host:$stage/"
done
printf 'Binarios compilados y distribuidos: %s\n' "$stage"
