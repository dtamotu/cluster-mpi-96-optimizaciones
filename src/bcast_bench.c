#include <mpi.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv) {
    MPI_Init(&argc, &argv);
    int rank, p;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &p);
    if (argc != 3) {
        if (!rank) fprintf(stderr, "uso: %s N <world|hier>\n", argv[0]);
        MPI_Abort(MPI_COMM_WORLD, 2);
    }
    int n = atoi(argv[1]);
    int hier = strcmp(argv[2], "hier") == 0;
    if (n < 1 || ((size_t)n * n) > INT32_MAX || (!hier && strcmp(argv[2], "world") != 0)) {
        if (!rank) fprintf(stderr, "argumentos invalidos\n");
        MPI_Abort(MPI_COMM_WORLD, 2);
    }
    size_t count = (size_t)n * n;
    double *b = malloc(count * sizeof(double));
    if (!b) MPI_Abort(MPI_COMM_WORLD, 3);
    if (!rank) for (size_t i = 0; i < count; ++i) b[i] = (double)(i % 251) / 251.0;

    MPI_Comm local = MPI_COMM_NULL, leaders = MPI_COMM_NULL;
    int local_rank = -1;
    if (hier) {
        MPI_Comm_split_type(MPI_COMM_WORLD, MPI_COMM_TYPE_SHARED, rank, MPI_INFO_NULL, &local);
        MPI_Comm_rank(local, &local_rank);
        MPI_Comm_split(MPI_COMM_WORLD, local_rank == 0 ? 0 : MPI_UNDEFINED, rank, &leaders);
    }
    MPI_Barrier(MPI_COMM_WORLD);
    double t0 = MPI_Wtime();
    if (hier) {
        if (local_rank == 0) MPI_Bcast(b, (int)count, MPI_DOUBLE, 0, leaders);
        MPI_Bcast(b, (int)count, MPI_DOUBLE, 0, local);
    } else {
        MPI_Bcast(b, (int)count, MPI_DOUBLE, 0, MPI_COMM_WORLD);
    }
    double elapsed = MPI_Wtime() - t0;
    double maximum;
    MPI_Reduce(&elapsed, &maximum, 1, MPI_DOUBLE, MPI_MAX, 0, MPI_COMM_WORLD);

    uint64_t hash = UINT64_C(1469598103934665603);
    const unsigned char *bytes = (const unsigned char *)b;
    for (size_t i = 0; i < count * sizeof(double); ++i) {
        hash ^= bytes[i];
        hash *= UINT64_C(1099511628211);
    }
    unsigned long long local_hash = (unsigned long long)hash, min_hash, max_hash;
    MPI_Allreduce(&local_hash, &min_hash, 1, MPI_UNSIGNED_LONG_LONG, MPI_MIN, MPI_COMM_WORLD);
    MPI_Allreduce(&local_hash, &max_hash, 1, MPI_UNSIGNED_LONG_LONG, MPI_MAX, MPI_COMM_WORLD);
    if (!rank) {
        printf("RESULT_BCAST: N=%d, Procs=%d, Modo=%s, T_Bcast=%.6f, Hash=%llu, Valido=%d\n",
               n, p, argv[2], maximum, min_hash, min_hash == max_hash);
        fflush(stdout);
    }
    if (hier) {
        if (leaders != MPI_COMM_NULL) MPI_Comm_free(&leaders);
        MPI_Comm_free(&local);
    }
    free(b);
    MPI_Finalize();
    return min_hash == max_hash ? 0 : 4;
}
