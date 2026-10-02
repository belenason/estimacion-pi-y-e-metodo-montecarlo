/*
 * serial_v0.c - Versión 0: implementación ingenua (línea de base).
 *
 * Es la traducción más directa de la definición matemática:
 *   - números aleatorios con rand() de la biblioteca estándar,
 *   - distancia al origen con sqrt() y pow(),
 *   - un if para contar,
 *   - contadores de tipo int.
 *
 * Limitación conocida: int llega hasta 2^31 - 1 (unos 2,1 x 10^9). Para no
 * desbordar, el programa rechaza los N demasiado grandes. La versión 1 lo corrige.
 */
#include <limits.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#include "util.h"

/* N máximo que soportan los contadores int. Para e se generan en promedio
 * 2,72 números por ensayo, así que el total crece más rápido que N. */
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
    int constant;
    uint64_t n, seed;

    if (!parse_args(argc, argv, &constant, &n, &seed)) {
        return 1;
    }

    uint64_t max_n = (constant == CONST_PI) ? MAX_N_PI : MAX_N_E;
    if (n > max_n) {
        fprintf(stderr, "serial_v0: N = %" PRIu64 " desbordaría los contadores int (máximo %" PRIu64 ").\n",
                n, max_n);
        return 2;
    }

    srand((unsigned int)seed);

    double t0 = wall_time();
    int count = (constant == CONST_PI) ? count_hits_pi((int)n) : count_draws_e((int)n);
    double t1 = wall_time();

    /* pi = 4 * aciertos / N          e = números generados / N */
    double estimate = (constant == CONST_PI) ? 4.0 * count / (double)n
                                             : (double)count / (double)n;

    print_csv_row("serial_v0", constant, n, 1, seed, estimate, t1 - t0);
    return 0;
}
