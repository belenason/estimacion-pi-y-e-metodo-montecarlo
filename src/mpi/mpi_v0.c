/*
 * mpi_v0.c - Versión paralela ingenua (referencia).
 *
 * Es serial_v0 repartido entre P procesos con MPI. Conserva sus limitaciones:
 * rand(), sqrt(), pow() y contadores int.
 *
 * Debilidad conocida: con rand() la única forma de diferenciar los procesos es
 * sembrar cada uno con "semilla + rango". Eso NO garantiza que las secuencias
 * sean independientes ni que no se solapen. mpi_v2 lo resuelve con jump().
 */
#include <limits.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#include <mpi.h>

#include "util.h"

/* N máximo que soportan los contadores int (ver serial_v0.c). */
#define MAX_N_PI ((uint64_t)INT_MAX)
#define MAX_N_E  ((uint64_t)INT_MAX / 4)

/* Cuenta cuántos de n puntos al azar caen dentro del cuarto de círculo. */
static int count_hits_pi(int n)
{
    int hits = 0;

    for (int i = 0; i < n; i++) {
        double x = (double)rand() / RAND_MAX;
        double y = (double)rand() / RAND_MAX;
        double distance = sqrt(pow(x, 2) + pow(y, 2));
        if (distance <= 1.0) {
            hits++;
        }
    }
    return hits;
}

/* Repite n ensayos: sumar uniformes hasta superar 1. Devuelve el total de números generados. */
static int count_draws_e(int n)
{
    int total_draws = 0;

    for (int i = 0; i < n; i++) {
        double sum = 0.0;
        int draws = 0;
        while (sum <= 1.0) {
            sum += (double)rand() / RAND_MAX;
            draws++;
        }
        total_draws += draws;
    }
    return total_draws;
}

int main(int argc, char **argv)
{
    MPI_Init(&argc, &argv);

    int rank, size;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);   /* quién soy: 0 .. P-1 */
    MPI_Comm_size(MPI_COMM_WORLD, &size);   /* cuántos somos: P */

    /* 1. El proceso 0 lee los argumentos y los difunde a todos. */
    int params[3] = {0, 0, 0};              /* constante, N, semilla */
    if (rank == 0) {
        int constant = CONST_PI;
        uint64_t n = 0, seed = 0;

        if (!parse_args(argc, argv, &constant, &n, &seed)) {
            MPI_Abort(MPI_COMM_WORLD, 1);   /* argumentos inválidos: termina todos los procesos */
        }
        uint64_t max_n = (constant == CONST_PI) ? MAX_N_PI : MAX_N_E;
        if (n > max_n || seed > (uint64_t)INT_MAX) {
            fprintf(stderr, "mpi_v0: N o semilla demasiado grandes para int (N máximo %" PRIu64 ").\n", max_n);
            MPI_Abort(MPI_COMM_WORLD, 2);
        }
        params[0] = constant;
        params[1] = (int)n;
        params[2] = (int)seed;
    }
    MPI_Bcast(params, 3, MPI_INT, 0, MPI_COMM_WORLD);

    int constant = params[0];
    int n = params[1];
    int seed = params[2];

    /* 2. Reparto del trabajo: N / P para cada uno; el resto se reparte de a uno entre los primeros. */
    int local_n = n / size + (rank < n % size ? 1 : 0);

    /* 3. Semilla distinta por proceso (forma ingenua, sin garantías). */
    srand((unsigned int)seed + (unsigned int)rank);

    /* 4. Cómputo cronometrado: todos arrancan juntos después de la barrera. */
    MPI_Barrier(MPI_COMM_WORLD);
    double t0 = MPI_Wtime();

    int local_count = (constant == CONST_PI) ? count_hits_pi(local_n) : count_draws_e(local_n);

    int total_count = 0;
    MPI_Reduce(&local_count, &total_count, 1, MPI_INT, MPI_SUM, 0, MPI_COMM_WORLD);

    double t1 = MPI_Wtime();

    /* 5. El proceso 0 calcula la estimación e imprime el resultado. */
    if (rank == 0) {
        double estimate = (constant == CONST_PI) ? 4.0 * total_count / (double)n
                                                 : (double)total_count / (double)n;
        print_csv_row("mpi_v0", constant, (uint64_t)n, size, (uint64_t)seed, estimate, t1 - t0);
    }

    MPI_Finalize();
    return 0;
}
