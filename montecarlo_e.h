/* Rutinas del experimento de Monte Carlo para estimar e. */
#ifndef MONTECARLO_E_H
#define MONTECARLO_E_H

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

static double calcular_estimacion_e(long long sumandos, long long n)
{
    return (double)sumandos / (double)n;
}

#endif