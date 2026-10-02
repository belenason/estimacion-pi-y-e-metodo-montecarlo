/*
 * serial_v1.c - Versión 1: optimización matemática, de saltos y de tipos.
 *
 * Cambios respecto de la versión 0 (el generador sigue siendo rand()):
 *   - Sin sqrt() ni pow(): comparar x*x + y*y <= 1 equivale a comparar la
 *     distancia, porque ambos lados son no negativos.
 *   - Multiplicar por 1/RAND_MAX (calculado una sola vez) en lugar de dividir
 *     en cada iteración: la multiplicación es varias veces más rápida.
 *   - Sin if: el resultado de la comparación (0 o 1) se suma directamente.
 *   - Contadores uint64_t: ya no hay desborde para N grandes.
 */
#include <stdio.h>
#include <stdlib.h>

#include "util.h"

/* Factor para llevar la salida de rand() al intervalo [0, 1]. */
static const double INV_RAND_MAX = 1.0 / RAND_MAX;

/* Cuenta cuántos de n puntos al azar caen dentro del cuarto de círculo. */
static uint64_t count_hits_pi(uint64_t n)
{
    uint64_t hits = 0;

    for (uint64_t i = 0; i < n; i++) {
        double x = rand() * INV_RAND_MAX;
        double y = rand() * INV_RAND_MAX;
        hits += (x * x + y * y <= 1.0);
    }
    return hits;
}

/* Repite n ensayos: sumar uniformes hasta superar 1. Devuelve el total de números generados. */
static uint64_t count_draws_e(uint64_t n)
{
    uint64_t total_draws = 0;

    for (uint64_t i = 0; i < n; i++) {
        double sum = 0.0;
        while (sum <= 1.0) {
            sum += rand() * INV_RAND_MAX;
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

    srand((unsigned int)seed);

    double t0 = wall_time();
    uint64_t count = (constant == CONST_PI) ? count_hits_pi(n) : count_draws_e(n);
    double t1 = wall_time();

    /* pi = 4 * aciertos / N          e = números generados / N */
    double estimate = (constant == CONST_PI) ? 4.0 * (double)count / (double)n
                                             : (double)count / (double)n;

    print_csv_row("serial_v1", constant, n, 1, seed, estimate, t1 - t0);
    return 0;
}
