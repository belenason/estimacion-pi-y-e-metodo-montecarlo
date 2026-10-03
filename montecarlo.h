/*
 * montecarlo.h
 * Funciones compartidas por los programas: lectura de argumentos y salida.
 */
#ifndef MONTECARLO_H
#define MONTECARLO_H

#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#define PI_REAL 3.14159265358979323846
#define E_REAL  2.71828182845904523536

#define CONSTANTE_PI 0
#define CONSTANTE_E  1

/*
 * Lee los argumentos:  <N> [semilla]
 * Los guarda en datos[0] (N) y datos[1] (semilla).
 * Devuelve 1 si son válidos y 0 si no.
 */
static int leer_argumentos(int argc, char *argv[], long long datos[2])
{
    if (argc < 2) {
        fprintf(stderr, "Uso: %s <N> [semilla]\n", argv[0]);
        return 0;
    }

    datos[0] = atoll(argv[1]);
    if (datos[0] <= 0) {
        fprintf(stderr, "N debe ser un entero mayor que 0\n");
        return 0;
    }

    datos[1] = (argc >= 3) ? atoll(argv[2]) : 12345;
    return 1;
}

/* Imprime una línea en formato CSV: constante,N,P,semilla,estimacion,error_abs,tiempo_s */
static void imprimir_resultado(int constante, long long n, int procesos, long long semilla, double estimacion, double tiempo)
{
    const char *nombre;
    double valor_real;

    if (constante == CONSTANTE_PI) {
        nombre = "pi";
        valor_real = PI_REAL;
    } else {
        nombre = "e";
        valor_real = E_REAL;
    }

    double error_absoluto = fabs(estimacion - valor_real);

    printf("%s,%lld,%d,%lld,%.10f,%.3e,%.6f\n",
           nombre, n, procesos, semilla, estimacion, error_absoluto, tiempo);
}

#endif
