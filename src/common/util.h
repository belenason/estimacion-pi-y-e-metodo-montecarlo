/*
 * util.h - Utilidades compartidas por todas las versiones:
 * lectura de argumentos, medición de tiempo y salida en formato CSV.
 *
 * Todos los programas se usan igual:
 *     programa <pi|e> <N> <semilla>
 * e imprimen UNA línea CSV:
 *     sistema,programa,constante,N,P,semilla,estimacion,error_abs,error_rel,tiempo_s
 */
#ifndef UTIL_H
#define UTIL_H

#include <errno.h>
#include <inttypes.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

/* Valores de referencia para calcular el error. */
#define PI_TRUE 3.14159265358979323846
#define E_TRUE  2.71828182845904523536

/* Qué constante se estima. */
#define CONST_PI 0
#define CONST_E  1

/* Convierte un texto en un entero sin signo de 64 bits. Devuelve 1 si salió bien, 0 si no. */
static inline int parse_u64(const char *text, uint64_t *value)
{
    char *end = NULL;

    if (text[0] == '\0' || text[0] == '-') {
        return 0;                       /* vacío o negativo */
    }
    errno = 0;
    unsigned long long parsed = strtoull(text, &end, 10);
    if (errno != 0 || *end != '\0') {
        return 0;                       /* fuera de rango o con caracteres no numéricos */
    }
    *value = (uint64_t)parsed;
    return 1;
}

/*
 * Lee los tres argumentos de la línea de comandos.
 * Devuelve 1 si son válidos; si no, imprime el modo de uso y devuelve 0.
 */
static inline int parse_args(int argc, char **argv, int *constant, uint64_t *n, uint64_t *seed)
{
    int ok = (argc == 4);

    if (ok && strcmp(argv[1], "pi") == 0) {
        *constant = CONST_PI;
    } else if (ok && strcmp(argv[1], "e") == 0) {
        *constant = CONST_E;
    } else {
        ok = 0;
    }

    ok = ok && parse_u64(argv[2], n) && *n > 0;
    ok = ok && parse_u64(argv[3], seed);

    if (!ok) {
        fprintf(stderr, "Uso: %s <pi|e> <N> <semilla>\n", argv[0]);
        fprintf(stderr, "  N: cantidad de muestras (entero mayor que 0)\n");
    }
    return ok;
}

/* Tiempo de reloj en segundos (reloj monotónico: no retrocede ni salta). */
static inline double wall_time(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec + (double)ts.tv_nsec * 1e-9;
}

/* Imprime la línea CSV de resultados. El nombre del sistema se toma de la variable de entorno SYSTEM. */
static inline void print_csv_row(const char *program, int constant, uint64_t n, int p,
                                 uint64_t seed, double estimate, double time_s)
{
    const char *system_name = getenv("SYSTEM");
    if (system_name == NULL) {
        system_name = "local";
    }

    double true_value = (constant == CONST_PI) ? PI_TRUE : E_TRUE;
    double abs_err = fabs(estimate - true_value);
    double rel_err = abs_err / true_value;

    printf("%s,%s,%s,%" PRIu64 ",%d,%" PRIu64 ",%.12f,%.6e,%.6e,%.6f\n",
           system_name, program, (constant == CONST_PI) ? "pi" : "e",
           n, p, seed, estimate, abs_err, rel_err, time_s);
}

#endif /* UTIL_H */
