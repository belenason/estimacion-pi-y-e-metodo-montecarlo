/*
 * serial_v2.c - Versión 2: generador de alta calidad (xoshiro256**).
 *
 * Único cambio respecto de la versión 1: rand() se reemplaza por el generador
 * de prng.h. El estado del generador es una variable local que se pasa por
 * puntero, sin estado global oculto. Es la base de la versión paralela.
 */
#include <stdio.h>
#include <stdlib.h>

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
    int constant;
    uint64_t n, seed;

    if (!parse_args(argc, argv, &constant, &n, &seed)) {
        return 1;
    }

    prng_t g;
    prng_seed(&g, seed);

    double t0 = wall_time();
    uint64_t count = (constant == CONST_PI) ? count_hits_pi(n, &g) : count_draws_e(n, &g);
    double t1 = wall_time();

    /* pi = 4 * aciertos / N          e = números generados / N */
    double estimate = (constant == CONST_PI) ? 4.0 * (double)count / (double)n
                                             : (double)count / (double)n;

    print_csv_row("serial_v2", constant, n, 1, seed, estimate, t1 - t0);
    return 0;
}
