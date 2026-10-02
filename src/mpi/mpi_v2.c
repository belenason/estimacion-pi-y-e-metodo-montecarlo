/*
 * mpi_v2.c - Versión paralela principal.
 *
 * Es serial_v2 repartido entre P procesos con MPI:
 *   - el proceso 0 lee los argumentos y los difunde (MPI_Bcast),
 *   - cada proceso hace su parte de las N muestras con su propio tramo de
 *     números aleatorios (jump), sin comunicarse con los demás,
 *   - al final se suman los P contadores con una sola MPI_Reduce.
 */
#include <stdio.h>
#include <stdlib.h>

#include <mpi.h>

#include "prng.h"
#include "util.h"

/* Cuenta cuántos de n puntos al azar caen dentro del cuarto de círculo. */
static uint64_t count_hits_pi(uint64_t n, prng_t *g)
{
    uint64_t hits = 0;

    for (uint64_t i = 0; i < n; i++) {
        double x = prng_uniform(g);
        double y = prng_uniform(g);
        hits += (x * x + y * y <= 1.0);
    }
    return hits;
}

/* Repite n ensayos: sumar uniformes hasta superar 1. Devuelve el total de números generados. */
static uint64_t count_draws_e(uint64_t n, prng_t *g)
{
    uint64_t total_draws = 0;

    for (uint64_t i = 0; i < n; i++) {
        double sum = 0.0;
        while (sum <= 1.0) {
            sum += prng_uniform(g);
            total_draws++;
        }
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
    uint64_t params[3] = {0, 0, 0};         /* constante, N, semilla */
    if (rank == 0) {
        int constant = CONST_PI;
        uint64_t n = 0, seed = 0;

        if (!parse_args(argc, argv, &constant, &n, &seed)) {
            MPI_Abort(MPI_COMM_WORLD, 1);   /* argumentos inválidos: termina todos los procesos */
        }
        params[0] = (uint64_t)constant;
        params[1] = n;
        params[2] = seed;
    }
    MPI_Bcast(params, 3, MPI_UINT64_T, 0, MPI_COMM_WORLD);

    int constant = (int)params[0];
    uint64_t n = params[1];
    uint64_t seed = params[2];

    /* 2. Reparto del trabajo: N / P para cada uno; el resto se reparte de a uno entre los primeros. */
    uint64_t p = (uint64_t)size;
    uint64_t local_n = n / p + ((uint64_t)rank < n % p ? 1 : 0);

    /* 3. Números aleatorios independientes: misma semilla y "rank" saltos de 2^128 pasos. */
    prng_t g;
    prng_seed(&g, seed);
    for (int i = 0; i < rank; i++) {
        prng_jump(&g);
    }

    /* 4. Cómputo cronometrado: todos arrancan juntos después de la barrera. */
    MPI_Barrier(MPI_COMM_WORLD);
    double t0 = MPI_Wtime();

    uint64_t local_count = (constant == CONST_PI) ? count_hits_pi(local_n, &g)
                                                  : count_draws_e(local_n, &g);

    uint64_t total_count = 0;
    MPI_Reduce(&local_count, &total_count, 1, MPI_UINT64_T, MPI_SUM, 0, MPI_COMM_WORLD);

    double t1 = MPI_Wtime();

    /* 5. El proceso 0 calcula la estimación e imprime el resultado. */
    if (rank == 0) {
        double estimate = (constant == CONST_PI) ? 4.0 * (double)total_count / (double)n
                                                 : (double)total_count / (double)n;
        print_csv_row("mpi_v2", constant, n, size, seed, estimate, t1 - t0);
    }

    MPI_Finalize();
    return 0;
}
