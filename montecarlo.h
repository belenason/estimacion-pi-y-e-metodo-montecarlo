/*
 * montecarlo.h
 * Funciones compartidas por la versión serial y la versión MPI:
 * los dos experimentos de Monte Carlo, la lectura de argumentos y la salida.
 */
#ifndef MONTECARLO_H
#define MONTECARLO_H

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define PI_REAL 3.14159265358979323846
#define E_REAL  2.71828182845904523536

#define CONSTANTE_PI 0
#define CONSTANTE_E  1

/*
 * Experimento de pi: se generan n puntos (x, y) al azar en el cuadrado
 * [0,1] x [0,1] y se cuenta cuántos caen dentro del cuarto de círculo de
 * radio 1. Esa proporción tiende a pi/4.
 *
 * Se compara x*x + y*y con 1 en lugar de calcular la raíz cuadrada: da el
 * mismo resultado y evita una operación costosa en cada iteración.
 */
static long long contar_aciertos_pi(long long n)
{
    long long aciertos = 0;

    for (long long i = 0; i < n; i++) {
        double x = drand48();
        double y = drand48();
        if (x * x + y * y <= 1.0) {
            aciertos++;
        }
    }
    return aciertos;
}

/*
 * Experimento de e: en cada ensayo se suman números al azar entre 0 y 1
 * hasta que la suma supera 1. La cantidad promedio de números necesarios
 * tiende a e. Se devuelve el total de números generados en los n ensayos.
 */
static long long contar_sumandos_e(long long n)
{
    long long sumandos = 0;

    for (long long i = 0; i < n; i++) {
        double suma = 0.0;
        while (suma <= 1.0) {
            suma += drand48();
            sumandos++;
        }
    }
    return sumandos;
}

/* A partir del contador calcula la estimación de la constante. */
static double calcular_estimacion(int constante, long long cuenta, long long n)
{
    if (constante == CONSTANTE_PI) {
        return 4.0 * (double)cuenta / (double)n;    /* pi = 4 * aciertos / N */
    }
    return (double)cuenta / (double)n;              /* e = sumandos / N */
}

/*
 * Lee los argumentos:  <pi|e> <N> [semilla]
 * Los guarda en datos[0] (constante), datos[1] (N) y datos[2] (semilla).
 * Devuelve 1 si son válidos y 0 si no.
 */
static int leer_argumentos(int argc, char *argv[], long long datos[3])
{
    if (argc < 3) {
        fprintf(stderr, "Uso: %s <pi|e> <N> [semilla]\n", argv[0]);
        return 0;
    }

    if (strcmp(argv[1], "pi") == 0) {
        datos[0] = CONSTANTE_PI;
    } else if (strcmp(argv[1], "e") == 0) {
        datos[0] = CONSTANTE_E;
    } else {
        fprintf(stderr, "La constante debe ser 'pi' o 'e'\n");
        return 0;
    }

    datos[1] = atoll(argv[2]);
    if (datos[1] <= 0) {
        fprintf(stderr, "N debe ser un entero mayor que 0\n");
        return 0;
    }

    datos[2] = (argc >= 4) ? atoll(argv[3]) : 12345;
    return 1;
}

/* Imprime una línea en formato CSV: constante,N,P,semilla,estimacion,error_abs,tiempo_s */
static void imprimir_resultado(int constante, long long n, int procesos, long long semilla,
                               double estimacion, double tiempo)
{
    double real = (constante == CONSTANTE_PI) ? PI_REAL : E_REAL;

    printf("%s,%lld,%d,%lld,%.10f,%.3e,%.6f\n",
           (constante == CONSTANTE_PI) ? "pi" : "e",
           n, procesos, semilla, estimacion, fabs(estimacion - real), tiempo);
}

#endif
