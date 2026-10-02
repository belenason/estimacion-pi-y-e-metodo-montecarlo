/*
 * montecarlo_serial.c
 * Estimación de pi y e por el método de Monte Carlo, versión serial.
 * Es la referencia para calcular el speedup de la versión paralela.
 *
 * Uso:  ./montecarlo_serial <pi|e> <N> [semilla]
 */
#include <time.h>

#include "montecarlo.h"

/* Tiempo de reloj en segundos. */
static double segundos(void)
{
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec + t.tv_nsec / 1e9;
}

int main(int argc, char *argv[])
{
    long long datos[3];

    if (!leer_argumentos(argc, argv, datos)) {
        return 1;
    }
    int constante = (int)datos[0];
    long long n = datos[1];
    long long semilla = datos[2];

    srand48(semilla);

    double inicio = segundos();

    long long cuenta;
    if (constante == CONSTANTE_PI) {
        cuenta = contar_aciertos_pi(n);
    } else {
        cuenta = contar_sumandos_e(n);
    }

    double fin = segundos();

    double estimacion = calcular_estimacion(constante, cuenta, n);
    imprimir_resultado(constante, n, 1, semilla, estimacion, fin - inicio);
    return 0;
}
