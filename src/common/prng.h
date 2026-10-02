/*
 * prng.h - Generador de números pseudoaleatorios xoshiro256**.
 *
 * Reemplaza a rand() a partir de la versión 2. Ventajas:
 *   - El estado vive en una variable local (struct), no en una variable global oculta.
 *   - Período 2^256 - 1: imposible de agotar.
 *   - jump() permite dar a cada proceso MPI un tramo propio de la secuencia,
 *     garantizando que los tramos no se solapan.
 *
 * Algoritmo y constantes: David Blackman y Sebastiano Vigna (dominio público),
 * https://prng.di.unimi.it/
 */
#ifndef PRNG_H
#define PRNG_H

#include <stdint.h>

/* Estado del generador: 4 enteros de 64 bits (256 bits = 32 bytes). */
typedef struct {
    uint64_t s[4];
} prng_t;

/*
 * splitmix64: generador auxiliar que solo se usa para inicializar.
 * A partir de UNA semilla produce una sucesión de valores de 64 bits muy
 * "mezclados". Así, semillas simples y parecidas (1, 2, 3...) dan estados
 * iniciales completamente distintos entre sí.
 */
static inline uint64_t splitmix64(uint64_t *state)
{
    *state += 0x9E3779B97F4A7C15ULL;          /* avanza un contador */
    uint64_t z = *state;
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;  /* mezcla los bits */
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
    return z ^ (z >> 31);
}

/* Inicializa el generador: llena los 4 enteros del estado con splitmix64. */
static inline void prng_seed(prng_t *g, uint64_t seed)
{
    for (int i = 0; i < 4; i++) {
        g->s[i] = splitmix64(&seed);
    }
}

/* Rotación de bits a la izquierda: los k bits que salen por arriba vuelven a entrar por abajo. */
static inline uint64_t rotl(uint64_t x, int k)
{
    return (x << k) | (x >> (64 - k));
}

/* Devuelve el siguiente entero aleatorio de 64 bits y avanza el estado un paso. */
static inline uint64_t prng_next(prng_t *g)
{
    /* Salida: se calcula a partir de uno de los cuatro enteros del estado. */
    uint64_t result = rotl(g->s[1] * 5, 7) * 9;

    /* Avance del estado: solo desplazamientos, rotaciones y XOR (muy rápido). */
    uint64_t t = g->s[1] << 17;
    g->s[2] ^= g->s[0];
    g->s[3] ^= g->s[1];
    g->s[1] ^= g->s[2];
    g->s[0] ^= g->s[3];
    g->s[2] ^= t;
    g->s[3] = rotl(g->s[3], 45);

    return result;
}

/* Devuelve un número real uniforme en [0, 1]: el entero dividido por el máximo posible. */
static inline double prng_uniform(prng_t *g)
{
    return (double)prng_next(g) / (double)UINT64_MAX;
}

/*
 * jump: adelanta el generador 2^128 pasos de una sola vez.
 * Equivale a llamar 2^128 veces a prng_next(), pero cuesta solo 256 pasos.
 *
 * Uso en paralelo: todos los procesos parten de la misma semilla y el proceso
 * de rango r llama a jump() r veces. Cada uno queda al inicio de un tramo
 * propio de 2^128 números, así que los tramos no pueden solaparse.
 */
static inline void prng_jump(prng_t *g)
{
    /* Constantes del salto, calculadas por los autores del generador. */
    static const uint64_t JUMP[4] = {
        0x180EC6D33CFD0ABAULL, 0xD5A61266F0C9392CULL,
        0xA9582618E03FC9AAULL, 0x39ABDC4529B1661CULL
    };

    uint64_t s0 = 0, s1 = 0, s2 = 0, s3 = 0;

    for (int i = 0; i < 4; i++) {
        for (int bit = 0; bit < 64; bit++) {
            if (JUMP[i] & (1ULL << bit)) {
                s0 ^= g->s[0];
                s1 ^= g->s[1];
                s2 ^= g->s[2];
                s3 ^= g->s[3];
            }
            prng_next(g);
        }
    }

    g->s[0] = s0;
    g->s[1] = s1;
    g->s[2] = s2;
    g->s[3] = s3;
}

#endif /* PRNG_H */
