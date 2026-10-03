/* Estimacion serial de pi por el metodo de Monte Carlo. */
#include <time.h>

#include "montecarlo.h"
#include "montecarlo_pi.h"

static double segundos(void)
{
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec + t.tv_nsec / 1e9;
}

int main(int argc, char *argv[])
{
    long long datos[2];

    if (!leer_argumentos(argc, argv, datos)) {
        return 1;
    }
    long long n = datos[0];
    long long semilla = datos[1];

    srand48(semilla);

    double inicio = segundos();
    long long aciertos = contar_aciertos_pi(n);
    double fin = segundos();

    double estimacion = calcular_estimacion_pi(aciertos, n);
    imprimir_resultado(CONSTANTE_PI, n, 1, semilla, estimacion, fin - inicio);
    return 0;
}