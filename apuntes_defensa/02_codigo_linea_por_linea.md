# 02 — El código, línea por línea

> **Apunte de estudio.** Describe el código de la rama `main`. Conviene leerlo con el archivo de código abierto al lado.

Contenido:

0. Mapa del proyecto
1. Conceptos de C que aparecen en todo el código
2. `Makefile`
3. `src/common/util.h`
4. `src/common/prng.h`
5. `serial_v0.c`
6. `serial_v1.c`
7. `serial_v2.c`
8. `mpi_v2.c` (la versión principal)
9. `mpi_v0.c`
10. Los scripts, en breve
11. Preguntas de código probables

Los recuadros **"¿Por qué así y no de otra forma?"** son las respuestas para el profesor.

---

## 0. Mapa del proyecto

```
Makefile              cómo se compila todo
src/common/util.h     leer argumentos, medir tiempo, imprimir el resultado
src/common/prng.h     el generador de números aleatorios (xoshiro256**)
src/serial/           serial_v0.c  serial_v1.c  serial_v2.c
src/mpi/              mpi_v0.c  mpi_v2.c
scripts/              instalar, medir, describir el sistema
analysis/             calcular medianas/speedup y dibujar los gráficos
results/              CSV crudos, tablas resumen y figuras
```

**Todos los programas tienen la misma forma:**

1. Leer tres argumentos: qué constante (`pi` o `e`), `N` y la semilla.
2. Preparar el generador aleatorio.
3. Tomar el tiempo, ejecutar el **núcleo** (el bucle que cuenta), tomar el tiempo otra vez.
4. Convertir el contador en la estimación.
5. Imprimir una línea CSV.

El núcleo son siempre dos funciones: `count_hits_pi` (cuenta puntos dentro del cuarto de círculo)
y `count_draws_e` (cuenta cuántos números aleatorios se generaron en total). Las dos devuelven
**un contador entero**. Esa decisión es clave para MPI: lo único que hay que sumar entre procesos
es un entero.

Se usa así:

```bash
./bin/serial_v2 pi 1000000 1
mpirun -np 4 ./bin/mpi_v2 e 100000000 1
```

y cada ejecución imprime una línea:

```
sistema,programa,constante,N,P,semilla,estimacion,error_abs,error_rel,tiempo_s
local,serial_v2,pi,1000000,1,1,3.141532000000,6.065359e-05,1.930664e-05,0.021081
```

---

## 1. Conceptos de C que aparecen en todo el código

**`#include`** — "pegar acá el contenido de otro archivo". Con `< >` busca en las bibliotecas del
sistema (`<stdio.h>`); con `" "` busca en el proyecto (`"util.h"`).

**Guardas de inclusión** — al principio de cada `.h`:

```c
#ifndef PRNG_H
#define PRNG_H
...
#endif
```

"Si todavía no se definió `PRNG_H`, definilo y procesá el archivo." Evita que el mismo archivo se
incluya dos veces y dé errores de "definición duplicada".

**`#define NOMBRE valor`** — una sustitución de texto antes de compilar. `#define CONST_PI 0`
hace que cada `CONST_PI` del código se reemplace por `0`. Sirve para dar nombre a los números.

**Tipos enteros:**

| Tipo | Tamaño | Rango | Dónde se usa |
|---|---|---|---|
| `int` | 32 bits, con signo | hasta 2 147 483 647 (≈ 2,1 × 10⁹) | V0, y lo que exige MPI (`rank`, `size`) |
| `uint64_t` | **exactamente** 64 bits, sin signo | hasta ≈ 1,8 × 10¹⁹ | contadores y N desde la V1 |
| `unsigned long long` | al menos 64 bits | — | solo lo que devuelve `strtoull` |
| `double` | 64 bits, punto flotante | ≈ 15–16 dígitos significativos | coordenadas, sumas, tiempos |

> **¿Por qué `uint64_t` y no `int` o `long`?**
> `int` desborda en 2,1 × 10⁹, y el proyecto usa N hasta 10¹⁰. `long` es de 64 bits en Linux pero
> de **32 bits en Windows**: el mismo código daría resultados distintos según el sistema.
> `uint64_t` (de `<stdint.h>`) garantiza 64 bits en cualquier plataforma, y tiene su tipo MPI
> exacto, `MPI_UINT64_T`. Sin signo porque un contador nunca es negativo.
> Desbordar un `int` con signo es además *comportamiento indefinido* en C: el compilador no está
> obligado a hacer nada razonable.

**Punteros** — un puntero guarda *dónde está* una variable, no su valor.

- `&x` = "la dirección de x".
- `*p` = "lo que hay en la dirección p".
- `prng_t *g` = "g es la dirección de un generador".

Analogía: en vez de darle a alguien una fotocopia de mi cuaderno (pasar por valor), le digo en qué
cajón está (pasar por puntero); lo que escriba queda escrito en **mi** cuaderno. Se usa cuando una
función tiene que **modificar** algo del que la llamó: `parse_args(..., &n, &seed)` llena `n` y
`seed`; `prng_uniform(&g)` avanza el estado del generador.

**`struct`** — varias variables agrupadas bajo un nombre. `prng_t` agrupa los cuatro enteros del
estado del generador. `g.s[0]` accede a un campo cuando tengo la variable; `g->s[0]` cuando tengo
un puntero a ella (`g->` es una abreviatura de `(*g).`).

**`static inline`** (en los `.h`) — `static`: la función es privada de cada archivo `.c` que la
incluye, no hay choques de nombres al enlazar. `inline`: se sugiere al compilador que copie el
cuerpo de la función en el lugar de la llamada, evitando el costo de llamar a una función miles de
millones de veces dentro del bucle.

**`static` delante de una función en un `.c`** (`static uint64_t count_hits_pi`) — la función solo
se usa dentro de ese archivo.

**Operador ternario** — `condición ? valor_si_verdadero : valor_si_falso`. Es un `if/else` que
devuelve un valor: `(constant == CONST_PI) ? count_hits_pi(n) : count_draws_e(n)`.

**Una comparación vale 0 o 1** — en C, `(a <= b)` es un entero: 1 si es verdadero, 0 si es falso.
Por eso se puede escribir `hits += (x * x + y * y <= 1.0);`.

**Conversión explícita (cast)** — `(double)count` convierte un entero a real. Hace falta antes de
dividir: `7 / 2` entre enteros da `3`; `(double)7 / 2` da `3.5`.

---

## 2. `Makefile`

Un Makefile es una receta: dice qué archivos hay que generar, de cuáles dependen y con qué comando.
`make` solo recompila lo que cambió.

```make
CC     := gcc
MPICC  := mpicc
```

Variables. `gcc` compila los programas seriales. `mpicc` es un envoltorio de `gcc` que agrega solo
las rutas y bibliotecas de MPI.

```make
CFLAGS   := -std=c11 -O3 -march=native -Wall -Wextra -Wpedantic -D_POSIX_C_SOURCE=200809L
```

| Flag | Qué hace |
|---|---|
| `-std=c11` | Usa el estándar C11 puro, sin extensiones: el código es portable |
| `-O3` | Nivel alto de optimización: el compilador reordena, simplifica e integra funciones para que el programa corra más rápido |
| `-march=native` | Permite usar todas las instrucciones del procesador **donde se compila** (por ejemplo AVX2). Consecuencia: hay que recompilar en cada máquina |
| `-Wall -Wextra -Wpedantic` | Activa todas las advertencias. El proyecto compila sin ninguna |
| `-D_POSIX_C_SOURCE=200809L` | Define una macro que habilita `clock_gettime()`. Esa función es del estándar POSIX (Linux), no de C11 puro; con `-std=c11` hay que pedirla explícitamente |

```make
INCLUDES := -Isrc/common      # dónde buscar util.h y prng.h
LDLIBS   := -lm               # enlazar la biblioteca matemática (sqrt, pow, fabs)
```

```make
SERIAL_SRC := $(wildcard src/serial/*.c)
SERIAL_BIN := $(patsubst src/serial/%.c,$(BIN)/%,$(SERIAL_SRC))
```

`wildcard` lista todos los `.c` de la carpeta. `patsubst` transforma cada nombre:
`src/serial/serial_v0.c` → `bin/serial_v0`. Así, agregar una versión nueva no requiere tocar el Makefile.

```make
$(BIN)/%: src/serial/%.c $(HEADERS) | $(BIN)
	$(CC) $(CFLAGS) $(INCLUDES) $< -o $@ $(LDLIBS)
```

Regla patrón: "para generar `bin/ALGO` hace falta `src/serial/ALGO.c` y los `.h`; si alguno cambió,
ejecutar este comando". `$<` es el primer requisito (el `.c`), `$@` es el objetivo (el binario).
`| $(BIN)` significa "la carpeta `bin` tiene que existir antes". Hay otra regla igual para
`src/mpi/` que usa `$(MPICC)`.

`.PHONY` declara que `all`, `clean`, etc. son nombres de acciones y no archivos.

> **¿Por qué las mismas flags para todas las versiones?**
> Para que la comparación sea justa. Si V2 se compilara con más optimización que V0, no podría
> saber si la mejora viene del código o del compilador. Con flags idénticas, toda diferencia de
> tiempo se debe al código.
>
> **¿Por qué no `-ffast-math`?**
> Permite al compilador cambiar el orden de las operaciones de punto flotante y asumir que no hay
> casos especiales. Puede alterar resultados. Prefiero resultados exactos y reproducibles; además
> los contadores son enteros, así que no hace falta.
>
> **¿`-O3` no hace trampa con la V0?**
> Es un punto real: con `-O3` el compilador ya convierte `pow(x, 2)` en `x * x` por su cuenta. Por
> eso la ganancia V0 → V1 es moderada: parte del trabajo ya lo hacía el compilador. Lo que el
> compilador **no** puede hacer solo es cambiar la división por `RAND_MAX` por una multiplicación
> (daría un resultado ligeramente distinto en punto flotante, y sin `-ffast-math` no tiene permiso)
> ni eliminar la raíz cuadrada.

---

## 3. `src/common/util.h`

Utilidades que usan los cinco programas. Están en un solo lugar para no repetir código.

### Constantes

```c
#define PI_TRUE 3.14159265358979323846
#define E_TRUE  2.71828182845904523536
#define CONST_PI 0
#define CONST_E  1
```

Los valores reales, para calcular el error. Se definen a mano porque `M_PI` no es parte del
estándar C11 (con `-std=c11 -Wpedantic` no está garantizado).

### `parse_u64` — texto a entero de 64 bits

```c
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
```

- `const char *text`: el texto a convertir (`const` = no lo modifico). `uint64_t *value`: dónde dejar el resultado.
- `text[0] == '\0'`: texto vacío. `text[0] == '-'`: negativo. Se rechazan los dos.
- `strtoull(text, &end, 10)`: convierte texto en base 10 a entero sin signo. Deja en `end` la
  posición donde dejó de leer.
- `errno != 0`: el número no cabe en 64 bits. `*end != '\0'`: quedaron caracteres sin leer (por
  ejemplo `"100abc"`).
- Devuelve 1 si salió bien, 0 si no.

> **¿Por qué no `atoi`?**
> `atoi` devuelve `int` (no sirve para 10¹⁰) y no avisa de errores: `atoi("abc")` da 0 en silencio.
> `strtoull` permite detectar texto inválido y desborde. Un programa que acepta basura en silencio
> produce resultados que parecen válidos y no lo son.

### `parse_args` — los tres argumentos

```c
int ok = (argc == 4);
```

`argc` cuenta los argumentos, incluido el nombre del programa: `programa pi 1000 1` son 4.

```c
if (ok && strcmp(argv[1], "pi") == 0) {
    *constant = CONST_PI;
} else if (ok && strcmp(argv[1], "e") == 0) {
    *constant = CONST_E;
} else {
    ok = 0;
}
```

`strcmp` compara dos textos y devuelve 0 si son iguales. El `ok &&` adelante evita leer `argv[1]`
si no hay suficientes argumentos.

```c
ok = ok && parse_u64(argv[2], n) && *n > 0;
ok = ok && parse_u64(argv[3], seed);
```

N debe ser un entero válido y mayor que 0 (con N = 0 habría una división por cero al final). El
`&&` deja de evaluar en cuanto algo falla. Si algo falló, imprime el modo de uso por `stderr` (la
salida de errores, para no ensuciar el CSV) y devuelve 0.

### `wall_time` — el cronómetro

```c
struct timespec ts;
clock_gettime(CLOCK_MONOTONIC, &ts);
return (double)ts.tv_sec + (double)ts.tv_nsec * 1e-9;
```

Devuelve "segundos desde un punto fijo" con resolución de nanosegundos. `ts` tiene dos campos:
segundos enteros y nanosegundos; se combinan en un `double`.

> **¿Por qué `CLOCK_MONOTONIC` y no `clock()` o `time()`?**
> `time()` tiene resolución de 1 segundo. `clock()` mide tiempo de CPU del proceso, no tiempo real,
> y en programas paralelos suma el de todos los hilos. `CLOCK_MONOTONIC` mide tiempo real y **nunca
> retrocede**: no lo afecta un ajuste del reloj del sistema a mitad de la medición. En las versiones
> MPI se usa `MPI_Wtime()`, que cumple el mismo papel.

### `print_csv_row` — la salida

- `getenv("SYSTEM")`: lee la variable de entorno `SYSTEM` (la define el script de benchmarks: `pc`
  o `cluster`). Si no existe, usa `"local"`.
- `fabs(estimate - true_value)`: error absoluto. Dividido por el valor real: error relativo.
- `"%" PRIu64`: `PRIu64` es el formato correcto de `printf` para `uint64_t` en cualquier
  plataforma (viene de `<inttypes.h>`).
- `%.12f` = 12 decimales; `%.6e` = notación científica.

> **¿Por qué una línea CSV y no un mensaje para humanos?**
> Porque los resultados los procesa un script. Con una fila por ejecución, el script de benchmarks
> solo redirige la salida a un archivo y Python lo lee directo, sin tener que interpretar texto.

---

## 4. `src/common/prng.h`

### 4.1 Qué es un generador pseudoaleatorio

**En simple.** Una computadora no tira dados. Un generador pseudoaleatorio es una fórmula que, a
partir de un número (el *estado*), produce el siguiente; la sucesión *parece* azar. Es como una
lista larguísima de números ya escritos: la **semilla** dice por dónde empiezo a leer. Misma
semilla, misma lista: por eso los resultados son reproducibles.

Tres propiedades importan:

- **Período:** cuántos números da antes de repetirse. Tiene que ser mucho mayor que lo que consumo.
- **Calidad:** que no tenga patrones detectables (se evalúa con baterías de pruebas estadísticas como BigCrush).
- **Velocidad:** se llama miles de millones de veces.

### 4.2 Por qué no `rand()`

| Problema | Detalle |
|---|---|
| Estado global oculto | Hay un único estado para todo el programa; no puedo tener dos generadores independientes |
| Bloqueo en cada llamada | En glibc, `rand()` toma un candado (lock) para ser segura con hilos. Se paga en cada llamada aunque haya un solo hilo |
| 31 bits por llamada | `RAND_MAX` = 2³¹ − 1 en Linux: solo 2 × 10⁹ valores distintos entre 0 y 1 |
| Depende de la plataforma | En Windows (MinGW) `RAND_MAX` es 32 767. El mismo código da calidades distintas |
| Período modesto | En glibc, del orden de 2³⁵ ≈ 3,4 × 10¹⁰. Con N = 10¹⁰ se consumen 2 × 10¹⁰ números: del mismo orden que el período |
| Sin secuencias independientes | No hay forma de pedir "otra secuencia que no se solape con esta" |

> **Dos precisiones que el profesor puede pedir:**
> 1. 2³¹ − 1 es `RAND_MAX` (el valor máximo que devuelve), **no** el período. El período de la
>    `rand()` de glibc es de alrededor de 2³⁵.
> 2. En MPI cada proceso es un programa separado con su propia copia del estado, así que entre
>    procesos **no hay contención** por el candado. La contención es el argumento contra `rand()`
>    con **hilos** (OpenMP). En MPI los argumentos fuertes son: no se pueden garantizar secuencias
>    independientes, el período y la calidad. El candado igual cuesta tiempo en cada llamada.

### 4.3 El estado

```c
typedef struct {
    uint64_t s[4];
} prng_t;
```

Cuatro enteros de 64 bits = 256 bits = 32 bytes. Cada generador es una variable común: puedo tener
los que quiera, y cada proceso MPI tiene el suyo.

### 4.4 `splitmix64` — el inicializador

```c
static inline uint64_t splitmix64(uint64_t *state)
{
    *state += 0x9E3779B97F4A7C15ULL;          /* avanza un contador */
    uint64_t z = *state;
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;  /* mezcla los bits */
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
    return z ^ (z >> 31);
}
```

**En simple.** Es una licuadora de bits. Le doy un número simple (la semilla 1, 2, 3…) y devuelve
números de 64 bits que parecen no tener relación entre sí. Lo uso solo una vez, al inicio, para
llenar los cuatro enteros del estado de xoshiro.

Línea por línea:

- `*state += constante`: suma una constante grande e impar al contador (el `*` porque `state` es un
  puntero: modifico la semilla del que llamó, así la próxima llamada da otro valor).
- `z >> 30`: desplaza los bits 30 lugares a la derecha. `^` es XOR (o exclusivo bit a bit).
  `z ^ (z >> 30)` mezcla los bits altos con los bajos.
- Multiplicar por una constante impar grande propaga cada bit hacia los bits superiores.
- Se repite dos veces con constantes distintas. Resultado: cambiar **un** bit de la entrada cambia
  en promedio la mitad de los bits de la salida ("efecto avalancha").
- `ULL` al final de una constante significa "unsigned long long" (64 bits). `0x` es notación hexadecimal.

> **¿Por qué hace falta? ¿No puedo poner la semilla directo en el estado?**
> No conviene. Si el estado inicial fuera `{1, 0, 0, 0}` tendría casi todos los bits en cero, y
> estos generadores tardan muchos pasos en "despertar" de un estado así. Además las semillas 1 y 2
> darían estados casi idénticos. `splitmix64` garantiza un estado inicial bien mezclado para
> cualquier semilla, y que el estado nunca sea todo ceros (el único estado prohibido de xoshiro).
> Es el procedimiento que recomiendan los autores del generador.
>
> **¿De dónde salen esas constantes?**
> Son las publicadas por los autores de los algoritmos, elegidas por sus propiedades estadísticas.
> No las inventé ni las modifiqué: usar las constantes de referencia es lo correcto.

### 4.5 `prng_seed`

```c
for (int i = 0; i < 4; i++) {
    g->s[i] = splitmix64(&seed);
}
```

Llama cuatro veces a `splitmix64` y guarda cada resultado en un casillero del estado.

### 4.6 `rotl` — rotación de bits

```c
return (x << k) | (x >> (64 - k));
```

Desplaza los bits `k` lugares a la izquierda; los `k` que "se caen" por arriba vuelven a entrar por
abajo. Analogía: una fila de 64 personas en ronda donde todas se corren `k` asientos. `|` es OR bit
a bit: une las dos mitades.

### 4.7 `prng_next` — el generador

```c
uint64_t result = rotl(g->s[1] * 5, 7) * 9;

uint64_t t = g->s[1] << 17;
g->s[2] ^= g->s[0];
g->s[3] ^= g->s[1];
g->s[1] ^= g->s[2];
g->s[0] ^= g->s[3];
g->s[2] ^= t;
g->s[3] = rotl(g->s[3], 45);

return result;
```

Dos partes:

1. **Salida** (`result`): toma uno de los cuatro enteros, lo multiplica por 5, lo rota 7 bits y lo
   multiplica por 9. Los dos asteriscos del nombre *xoshiro256\*\** son esas dos multiplicaciones.
   Sirve para que la salida no deje ver la estructura interna.
2. **Avance del estado:** mezcla los cuatro enteros entre sí con XOR, un desplazamiento y una
   rotación. El nombre viene de ahí: **xo**r, **sh**ift, **ro**tate. Son las operaciones más
   baratas que tiene un procesador.

`a ^= b` es abreviatura de `a = a ^ b`.

> **¿Por qué xoshiro256\*\* y no otro?**
> - Período 2²⁵⁶ − 1: imposible de agotar.
> - 32 bytes de estado: entra en registros del procesador.
> - Pasa las baterías de pruebas estadísticas estándar (BigCrush).
> - Tiene `jump()`, que es lo que necesito para MPI.
> - El código completo son 10 líneas que puedo explicar.
>
> **Alternativas descartadas:**
> | Generador | Por qué no |
> |---|---|
> | `xorshift64*` | Período 2⁶⁴ y sin función de salto: la independencia entre procesos sería solo "muy probable", no garantizada |
> | PCG32 | Entrega 32 bits por llamada; la independencia entre sus "flujos" es discutida |
> | `rand_r`, `drand48_r` | Generadores congruenciales lineales viejos y de calidad pobre; `drand48_r` es específico de glibc |
> | Mersenne Twister | 2,5 KB de estado, más lento, incómodo de dividir en tramos |
> | Philox (basado en contador) | Excelente para paralelo, pero el algoritmo es más difícil de explicar |

### 4.8 `prng_uniform` — de entero a real en [0, 1]

```c
return (double)prng_next(g) / (double)UINT64_MAX;
```

`prng_next` da un entero entre 0 y `UINT64_MAX` (el mayor entero de 64 bits, 2⁶⁴ − 1). Dividirlo
por el máximo lo lleva a [0, 1]. Es regla de tres.

> **¿Por qué así?**
> Elegí la forma más legible: "valor dividido por el máximo posible".
>
> **Detalle fino 1 — el intervalo es cerrado.** Un `double` tiene 53 bits de precisión, así que al
> convertir enteros muy cercanos al máximo se redondean, y el resultado puede ser exactamente 1,0
> (probabilidad del orden de 2⁻⁵⁴, despreciable). No afecta a ninguno de los dos estimadores: en π
> el borde tiene área cero; en e, sumar 1,0 simplemente termina el ensayo.
>
> **Detalle fino 2 — costo medido.** Esta forma no es la más rápida. La alternativa habitual es
> quedarse con los 53 bits más altos del entero y multiplicar por 2⁻⁵³:
> `(double)(x >> 11) * (1.0 / 9007199254740992.0)`. En mi PC, con N = 10⁸ para π, la versión
> legible tardó unos 2,0 s y la alternativa unos 0,5 s: **cuatro veces más rápida**. La causa es
> que estos procesadores no tienen una instrucción directa para convertir un entero **sin signo**
> de 64 bits a `double` (existe recién con AVX-512), y el compilador genera una secuencia más
> larga. Decisión tomada: priorizar que el código sea explicable; la optimización queda anotada
> como mejora futura. El speedup y la eficiencia no cambian, porque comparan la misma versión
> contra sí misma con distinta cantidad de procesos.

### 4.9 `prng_jump` — el salto

```c
static const uint64_t JUMP[4] = { ... };

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

g->s[0] = s0;  g->s[1] = s1;  g->s[2] = s2;  g->s[3] = s3;
```

**En simple.** La secuencia completa del generador es una cinta larguísima de números (2²⁵⁶).
`jump()` es un teletransporte: adelanta la posición 2¹²⁸ lugares de un solo golpe. En MPI todos los
procesos arrancan en el mismo lugar de la cinta (misma semilla); el proceso 0 no salta, el 1 salta
una vez, el 2 salta dos veces… Cada uno queda al principio de un tramo propio de 2¹²⁸ números.
Como ningún proceso va a consumir 2¹²⁸ números (≈ 3,4 × 10³⁸; el proyecto usa como mucho ~10¹⁰),
**ningún proceso puede alcanzar el tramo del siguiente**.

```
cinta:  |---- tramo del proceso 0 ----|---- tramo del proceso 1 ----|---- tramo del 2 ----| ...
        ^ semilla                     ^ 1 salto                     ^ 2 saltos
        (cada tramo mide 2^128 números)
```

**Cómo funciona, en términos sencillos.** El avance del estado usa solo XOR, desplazamientos y
rotaciones. Esas operaciones son *lineales*: avanzar un paso equivale a multiplicar el estado por
una matriz fija. Avanzar 2¹²⁸ pasos equivale a multiplicar por esa matriz elevada a la 2¹²⁸, y eso
se puede calcular de antemano. Las cuatro constantes `JUMP` son ese cálculo ya hecho por los
autores. El bucle recorre los 256 bits de las constantes: avanza el generador 256 pasos y, cada vez
que el bit correspondiente es 1, acumula (con XOR) el estado actual. El acumulado final es el
estado 2¹²⁸ pasos más adelante. Costo: 256 pasos en lugar de 2¹²⁸.

- `1ULL << bit`: un 1 desplazado `bit` lugares; es una máscara con un solo bit encendido.
- `JUMP[i] & máscara`: AND bit a bit; distinto de cero si ese bit de la constante es 1.
- `static const`: la tabla se crea una sola vez y no se modifica.

> **¿Cómo sé que realmente salta 2¹²⁸ y no copié mal una constante?**
> Lo verifiqué de forma independiente: construí en Python la matriz de transición del generador
> (256 × 256 bits), la elevé a la 2¹²⁸ con 128 elevaciones al cuadrado sucesivas, la apliqué a un
> estado y el resultado coincide bit a bit con el que deja `prng_jump()` en C. También comprobé que
> `splitmix64` reproduce los valores de referencia publicados.
>
> **¿Por qué no simplemente `semilla + rango` en cada proceso?**
> Con semillas distintas cada proceso cae en un punto "al azar" de la cinta. Probablemente los
> tramos no se solapen, pero no hay **garantía**. Con `jump()` la separación es exacta y conocida:
> 2¹²⁸. Es la diferencia entre "muy probablemente independientes" y "demostrablemente disjuntos".
>
> **¿Cuántos procesos soporta?**
> Hasta 2¹²⁸ tramos de 2¹²⁸ números cada uno. Sobra.

---

## 5. `serial_v0.c` — la versión ingenua

### Límites

```c
#define MAX_N_PI ((uint64_t)INT_MAX)
#define MAX_N_E  ((uint64_t)INT_MAX / 4)
```

`INT_MAX` (de `<limits.h>`) es el mayor `int`: 2 147 483 647. Para π el contador de aciertos nunca
supera N, así que N puede llegar a `INT_MAX`. Para e el contador es el total de números generados,
que en promedio es 2,72 × N: crece más rápido que N. Limitar N a `INT_MAX / 4` deja margen.

### El núcleo de π

```c
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
```

- `rand()` devuelve un entero entre 0 y `RAND_MAX`. Dividido por `RAND_MAX` queda en [0, 1]. El
  `(double)` es indispensable: sin él sería una división entre enteros y daría casi siempre 0.
- `sqrt(pow(x, 2) + pow(y, 2))`: la distancia al origen por Pitágoras, tal como se escribe en el pizarrón.
- `if (distance <= 1.0) hits++`: si está dentro del círculo, cuento.

### El núcleo de e

```c
for (int i = 0; i < n; i++) {
    double sum = 0.0;
    int draws = 0;
    while (sum <= 1.0) {
        sum += (double)rand() / RAND_MAX;
        draws++;
    }
    total_draws += draws;
}
```

Un ensayo por vuelta del `for`. El `while` suma números hasta pasar de 1 y cuenta cuántos usó
(`draws`); al terminar el ensayo se acumula en `total_draws`. (Ver el ejemplo a mano en el apunte 01.)

### `main`

```c
if (!parse_args(argc, argv, &constant, &n, &seed)) {
    return 1;
}
```

Lee los argumentos; si son inválidos termina con código 1 (convención: 0 = todo bien, distinto de 0 = error).

```c
uint64_t max_n = (constant == CONST_PI) ? MAX_N_PI : MAX_N_E;
if (n > max_n) {
    fprintf(stderr, "serial_v0: N = ... desbordaría los contadores int ...");
    return 2;
}
```

Si N es demasiado grande para `int`, avisa y termina con código 2. **No calcula basura en silencio.**

```c
srand((unsigned int)seed);
```

Fija la semilla de `rand()`.

```c
double t0 = wall_time();
int count = (constant == CONST_PI) ? count_hits_pi((int)n) : count_draws_e((int)n);
double t1 = wall_time();
```

Solo se cronometra el núcleo: ni la lectura de argumentos ni la impresión.

```c
double estimate = (constant == CONST_PI) ? 4.0 * count / (double)n
                                         : (double)count / (double)n;
```

π = 4 × aciertos / N; e = números generados / N. El `4.0` (con punto) fuerza aritmética real.

> **¿Por qué existe la V0 si es "mala"?**
> Es la línea de base: la traducción directa de la matemática, sin pensar en rendimiento. Sin ella
> no podría medir cuánto aporta cada optimización.
>
> **¿Por qué rechaza N grandes en lugar de usar un tipo más grande?**
> Porque el objetivo de la V0 es mostrar la limitación de `int`, pero de forma segura. Dejar que
> desborde sería comportamiento indefinido y daría un resultado sin sentido. Rechazar con un
> mensaje claro es el comportamiento correcto; el tipo se corrige en la V1.

---

## 6. `serial_v1.c` — matemática, saltos y tipos

Cuatro cambios respecto de la V0; **el generador sigue siendo `rand()`**, así que V0 y V1 producen
las mismas estimaciones con la misma semilla. Eso es una verificación gratuita de que no rompí nada.

```c
static const double INV_RAND_MAX = 1.0 / RAND_MAX;
```

El inverso de `RAND_MAX`, calculado **una sola vez**.

```c
double x = rand() * INV_RAND_MAX;
double y = rand() * INV_RAND_MAX;
hits += (x * x + y * y <= 1.0);
```

| Cambio | V0 | V1 | Por qué es mejor |
|---|---|---|---|
| Sin raíz | `sqrt(x² + y²) <= 1` | `x² + y² <= 1` | Ambos lados son ≥ 0, y elevar al cuadrado conserva el orden: √a ≤ 1 ⇔ a ≤ 1. La raíz es de las operaciones más lentas del procesador |
| Sin `pow` | `pow(x, 2)` | `x * x` | `pow` es una función general (sirve para exponentes reales); para un cuadrado alcanza una multiplicación |
| Sin división | `rand() / RAND_MAX` | `rand() * INV_RAND_MAX` | Una división de punto flotante cuesta varias veces lo que una multiplicación. Se divide una vez, fuera del bucle |
| Sin `if` | `if (...) hits++` | `hits += (...)` | La comparación vale 0 o 1 y se suma directo. No hay salto condicional que el procesador tenga que adivinar |
| Tipos | `int` | `uint64_t` | Sin desborde para N grandes |

**Sobre los saltos (branches), en simple.** El procesador trabaja como una línea de montaje:
empieza a ejecutar las instrucciones siguientes antes de terminar la actual. Ante un `if` tiene que
**adivinar** por dónde va a seguir. Si acierta, no pierde tiempo. Si se equivoca, tira el trabajo
adelantado y vuelve a empezar (unos 15–20 ciclos perdidos). Con datos aleatorios, el `if` del
círculo sale "sí" el 78,5 % de las veces: es bastante impredecible. Sumar el resultado de la
comparación evita el problema.

En e, el contador por ensayo `draws` desaparece: se incrementa directamente `total_draws`.

> **¿Cuánto mejora la V1?**
> Menos de lo que uno esperaría, y hay que decirlo: los tiempos medidos están en el apunte 03. La
> razón es doble. Primero, con `-O3` el compilador ya transformaba `pow(x, 2)` en `x * x`. Segundo,
> el costo dominante de V0 y V1 es `rand()` (con su candado), que no se tocó. La V1 muestra que
> optimizar la aritmética tiene un techo cuando el cuello de botella está en otro lado: es la ley
> de Amdahl aplicada dentro de un programa serial.
>
> **¿El `while` de e no es también un salto impredecible?**
> Sí, y no se puede eliminar: cuántos números hacen falta depende de los números mismos. Es una
> limitación propia del algoritmo de e.

---

## 7. `serial_v2.c` — el generador nuevo

Único cambio respecto de V1: de dónde salen los números.

```c
#include "prng.h"

static uint64_t count_hits_pi(uint64_t n, prng_t *g)
{
    ...
        double x = prng_uniform(g);
        double y = prng_uniform(g);
        hits += (x * x + y * y <= 1.0);
```

Las funciones del núcleo reciben un parámetro más: `prng_t *g`, un puntero al generador. Se pasa
por puntero porque cada llamada a `prng_uniform` **modifica** el estado.

En `main`:

```c
prng_t g;                 // el generador es una variable local
prng_seed(&g, seed);      // se inicializa con la semilla
...
count_hits_pi(n, &g)      // se pasa su dirección
```

> **¿Qué gana esta versión?**
> 1. **Velocidad:** no hay candado ni estado global; las tres funciones del generador se integran
>    en el bucle (`inline`). Tiempos en el apunte 03.
> 2. **Calidad:** período 2²⁵⁶ en lugar de ~2³⁵; 64 bits por llamada en lugar de 31.
> 3. **Portabilidad:** da exactamente los mismos números en cualquier sistema. `rand()` no.
> 4. **Preparada para paralelo:** el estado es explícito, así que cada proceso puede tener el suyo
>    y posicionarlo con `jump()`.
>
> **¿Por qué las estimaciones de V2 son distintas a las de V0/V1 con la misma semilla?**
> Porque es otro generador: otra lista de números. Ambas son estimaciones válidas del mismo valor.

---

## 8. `mpi_v2.c` — la versión paralela principal

### 8.1 Qué es MPI, en simple

MPI (*Message Passing Interface*) lanza **P copias del mismo programa**. Cada copia es un proceso
separado, con su propia memoria: **no comparten variables**. Lo único que las distingue es un
número, el **rango** (*rank*), de 0 a P − 1. Si necesitan algo de otra, se lo tienen que mandar
por mensaje.

Analogía: P empleados en oficinas separadas, todos con el mismo manual de instrucciones. El manual
dice "si sos el número 0, hacé esto; todos, hagan aquello". Se comunican solo por correo.

`mpirun -np 4 ./bin/mpi_v2 pi 1000 1` lanza 4 copias.

### 8.2 El código, bloque por bloque

```c
MPI_Init(&argc, &argv);
```

Enciende MPI. Tiene que ser la primera llamada MPI. Recibe las direcciones de `argc` y `argv`
porque algunas implementaciones agregan argumentos propios y los quitan acá.

```c
int rank, size;
MPI_Comm_rank(MPI_COMM_WORLD, &rank);   /* quién soy: 0 .. P-1 */
MPI_Comm_size(MPI_COMM_WORLD, &size);   /* cuántos somos: P */
```

`MPI_COMM_WORLD` es el *comunicador* que incluye a todos los procesos (el "grupo de chat" general).
`rank` y `size` son `int` porque así lo define la interfaz de MPI.

**Paso 1 — leer y difundir los parámetros**

```c
uint64_t params[3] = {0, 0, 0};         /* constante, N, semilla */
if (rank == 0) {
    int constant = CONST_PI;
    uint64_t n = 0, seed = 0;

    if (!parse_args(argc, argv, &constant, &n, &seed)) {
        MPI_Abort(MPI_COMM_WORLD, 1);
    }
    params[0] = (uint64_t)constant;
    params[1] = n;
    params[2] = seed;
}
MPI_Bcast(params, 3, MPI_UINT64_T, 0, MPI_COMM_WORLD);
```

Solo el proceso 0 interpreta los argumentos. Si son inválidos, `MPI_Abort` termina **todos** los
procesos (si solo terminara el 0, los demás quedarían esperando para siempre).

`MPI_Bcast` (*broadcast*, difusión): el proceso raíz envía un dato a todos. Argumentos:

| Argumento | Valor | Significado |
|---|---|---|
| buffer | `params` | qué se envía / dónde se recibe |
| cantidad | `3` | cuántos elementos |
| tipo | `MPI_UINT64_T` | de qué tipo son |
| raíz | `0` | quién envía |
| comunicador | `MPI_COMM_WORLD` | a qué grupo |

**Todos** los procesos ejecutan la misma línea `MPI_Bcast`: en el 0 significa "enviar"; en los
demás, "recibir". Después de esa línea, los P procesos tienen los mismos tres valores.

> **¿Por qué `MPI_Bcast` si cada proceso podría leer `argv`?**
> En la práctica `mpirun` suele pasar los argumentos a todos, pero el estándar MPI no lo garantiza.
> Con un solo punto de lectura y una difusión explícita, todos trabajan con seguridad con los
> mismos parámetros, y la validación se hace una sola vez.
>
> **¿Por qué empaquetar los tres valores en un arreglo?**
> Para hacer una sola comunicación en lugar de tres.

**Paso 2 — repartir el trabajo**

```c
uint64_t p = (uint64_t)size;
uint64_t local_n = n / p + ((uint64_t)rank < n % p ? 1 : 0);
```

- `n / p`: división entera, lo que le toca a cada uno "como mínimo".
- `n % p`: el resto, lo que sobra.
- `rank < n % p ? 1 : 0`: los primeros "resto" procesos hacen una muestra extra.

**Ejemplo con N = 10 y P = 3:**

- `10 / 3 = 3` (cociente), `10 % 3 = 1` (resto).
- Proceso 0: `0 < 1` es verdadero → 3 + 1 = **4**
- Proceso 1: `1 < 1` es falso → 3 + 0 = **3**
- Proceso 2: `2 < 1` es falso → 3 + 0 = **3**
- Total: 4 + 3 + 3 = **10**. No se pierde ni se duplica ninguna muestra.

Otro: N = 11, P = 4 → cociente 2, resto 3 → reparto 3, 3, 3, 2 (suma 11).

Analogía: repartir 10 caramelos entre 3 chicos. Tres a cada uno, y el que sobra se lo lleva el primero.

> **¿Por qué así?**
> - La suma es **exactamente** N: la estimación usa las N muestras pedidas.
> - El desbalance máximo es de **una** muestra: ningún proceso queda esperando a otro.
> - Cada proceso calcula su parte **solo**, con N, P y su rango. No hace falta comunicación.
> - Alternativa descartada: dar todo el resto al último proceso. Con N = 10⁹ + 7 y P = 8 la
>   diferencia sería mínima, pero en general carga más a un proceso, y el tiempo total lo marca el más lento.
>
> **¿Puede haber condiciones de carrera?**
> No, por construcción. Una condición de carrera necesita memoria compartida modificada por más de
> un hilo. En MPI cada proceso tiene su memoria privada; `local_n`, el generador y los contadores
> son variables locales de cada proceso.
>
> **¿Y si N < P?**
> Algunos procesos reciben `local_n = 0`, no hacen ninguna vuelta del bucle y aportan 0 a la suma. Funciona.

**Paso 3 — números aleatorios independientes**

```c
prng_t g;
prng_seed(&g, seed);
for (int i = 0; i < rank; i++) {
    prng_jump(&g);
}
```

Todos siembran con la misma semilla y después el proceso de rango r salta r veces. El proceso 0 no
salta (su bucle hace 0 vueltas). Ver la explicación de `jump()` en la sección 4.9.

Consecuencia: con P = 1 el proceso 0 usa exactamente la misma secuencia que `serial_v2`, así que
`mpirun -np 1 ./bin/mpi_v2` y `./bin/serial_v2` dan **el mismo resultado**. Lo comprobé.

**Paso 4 — el cómputo cronometrado**

```c
MPI_Barrier(MPI_COMM_WORLD);
double t0 = MPI_Wtime();

uint64_t local_count = (constant == CONST_PI) ? count_hits_pi(local_n, &g)
                                              : count_draws_e(local_n, &g);

uint64_t total_count = 0;
MPI_Reduce(&local_count, &total_count, 1, MPI_UINT64_T, MPI_SUM, 0, MPI_COMM_WORLD);

double t1 = MPI_Wtime();
```

- **`MPI_Barrier`**: nadie pasa de esta línea hasta que **todos** llegaron. Es la línea de largada
  de una carrera: sincroniza el inicio.
- **`MPI_Wtime`**: devuelve el tiempo de reloj en segundos (un `double`). La resta `t1 - t0` es el
  tiempo transcurrido.
- El núcleo es el mismo de `serial_v2`, con `local_n` muestras.
- **`MPI_Reduce`**: combina un valor de cada proceso en uno solo, en el proceso raíz.

| Argumento | Valor | Significado |
|---|---|---|
| dato a enviar | `&local_count` | lo que aporta cada proceso |
| resultado | `&total_count` | dónde queda la combinación (solo válido en la raíz) |
| cantidad | `1` | un elemento |
| tipo | `MPI_UINT64_T` | entero sin signo de 64 bits |
| operación | `MPI_SUM` | sumar |
| raíz | `0` | quién recibe el resultado |
| comunicador | `MPI_COMM_WORLD` | qué grupo |

> **¿Por qué `MPI_Barrier` antes de tomar el tiempo?**
> Los procesos no arrancan todos en el mismo instante. Sin la barrera, el proceso 0 podría empezar
> a cronometrar cuando otros todavía no están listos, y mediría también esa espera. La barrera
> asegura que el cronómetro mida solo cómputo y reducción.
>
> **¿Por qué el tiempo lo toma el proceso 0 después de `MPI_Reduce`?**
> En la raíz, `MPI_Reduce` no termina hasta haber recibido el aporte de **todos**. Entonces
> `t1 - t0` en el proceso 0 abarca hasta que terminó el más lento más la comunicación: es el
> tiempo real de la parte paralela.
>
> **¿Por qué `MPI_Reduce` (colectiva) y no `MPI_Send`/`MPI_Recv` o comunicación no bloqueante?**
> El patrón es "P valores escalares → una suma": es exactamente lo que resuelve una reducción.
> - Con `MPI_Send`/`MPI_Recv` a mano, el proceso 0 recibiría P − 1 mensajes uno tras otro: O(P).
>   `MPI_Reduce` puede organizarse internamente como un árbol: O(log P) etapas.
> - Es una línea en lugar de un bucle con envíos y recepciones: menos lugar para errores.
> - La comunicación **no bloqueante** (`MPI_Isend`, `MPI_Ireduce`) sirve para seguir calculando
>   mientras el mensaje viaja. Acá no hay nada más que hacer mientras tanto: el cómputo ya terminó.
>   Solo agregaría complejidad (manejar *requests* y `MPI_Wait`) sin ningún beneficio.
>
> **¿Qué queda fuera del tiempo medido?**
> `MPI_Init`, la lectura de argumentos, `MPI_Bcast`, la siembra y los saltos del generador, y
> `MPI_Finalize`. El costo de arrancar MPI se mide aparte: el script de benchmarks registra el
> tiempo total del lanzamiento (`wall_s`). La diferencia entre los dos explica por qué con N chico
> no conviene paralelizar (apunte 03).
>
> **¿Por qué se reduce un entero y no la estimación?**
> Sumar enteros es exacto. Si cada proceso calculara su propio π y se promediaran, habría que
> ponderar por `local_n` (los procesos no hacen todos la misma cantidad) y se introducirían
> redondeos. Sumar contadores y dividir una vez al final es exacto y más simple.

**Paso 5 — resultado**

```c
if (rank == 0) {
    double estimate = (constant == CONST_PI) ? 4.0 * (double)total_count / (double)n
                                             : (double)total_count / (double)n;
    print_csv_row("mpi_v2", constant, n, size, seed, estimate, t1 - t0);
}

MPI_Finalize();
return 0;
```

Solo el proceso 0 tiene el total, así que solo él calcula e imprime. `MPI_Finalize` apaga MPI; debe
ser la última llamada MPI, y la ejecutan todos.

### 8.3 Resumen del flujo

```
todos:      MPI_Init → rank, size
proceso 0:  lee argumentos
todos:      MPI_Bcast            (0 envía, el resto recibe)
todos:      calculan local_n, siembran, saltan "rank" veces
todos:      MPI_Barrier          (largada)
todos:      cuentan local_n muestras, SIN comunicarse
todos:      MPI_Reduce           (los contadores se suman en el proceso 0)
proceso 0:  calcula la estimación e imprime
todos:      MPI_Finalize
```

Comunicaciones en total: **una difusión y una reducción**, sin importar N.

---

## 9. `mpi_v0.c` — la referencia ingenua

Misma estructura de cinco pasos que `mpi_v2`, con el núcleo de `serial_v0`. Diferencias:

| | `mpi_v0` | `mpi_v2` |
|---|---|---|
| Núcleo | `rand()`, `sqrt`, `pow`, `if` | xoshiro256\*\*, `x*x + y*y`, sin `if` |
| Tipos | `int` y `MPI_INT` | `uint64_t` y `MPI_UINT64_T` |
| N máximo | `INT_MAX` (π) o `INT_MAX / 4` (e) | sin límite práctico |
| Semilla por proceso | `srand(seed + rank)` | misma semilla + `rank` saltos |

```c
srand((unsigned int)seed + (unsigned int)rank);
```

> **¿Qué tiene de malo `seed + rank`?**
> Es lo único que se puede hacer con `rand()`, y **no da garantías**: dos semillas consecutivas
> producen secuencias que arrancan en lugares distintos del mismo ciclo, pero nadie asegura a qué
> distancia. Podrían solaparse o estar correlacionadas. En mis pruebas las estimaciones de `mpi_v0`
> fueron correctas, pero "funcionó en las pruebas" no es una garantía; `jump()` sí lo es.
>
> **¿Para qué está entonces?**
> Para comparar. Muestra que el **speedup** de la versión ingenua también es bueno (el problema es
> embarazosamente paralelo con cualquier núcleo), pero su **tiempo absoluto** es mucho peor.
> Conclusión: un buen speedup no significa un buen programa; primero hay que optimizar la versión
> serial y después paralelizar.

---

## 10. Los scripts, en breve

**`scripts/run_benchmark.sh`** — recorre todas las combinaciones (programa × constante × N × P ×
repetición) y agrega una fila al CSV por ejecución.

- `set -euo pipefail`: el script se detiene ante cualquier error en lugar de seguir con datos incompletos.
- `VARIABLE=${VARIABLE:-valor}`: usa el valor del entorno si existe, o el valor por defecto.
- `limit_for`: N máximo de cada programa (los límites `int` de V0, y topes para las versiones lentas).
- `run_one`: toma la hora, ejecuta, toma la hora otra vez; agrega al CSV la fila del programa más
  el tiempo total del lanzamiento (`wall_s`).
- Semilla = `100 × P + repetición`: cada ejecución usa una semilla distinta, así las estimaciones
  son muestras independientes y sirven para estudiar el error.
- Si P supera los núcleos físicos, agrega `--use-hwthread-cpus` (Open MPI cuenta núcleos físicos
  por defecto y se negaría a lanzar 8 procesos en 4 núcleos).
- `MPIRUN_FLAGS`: opciones extra para el clúster.
- `QUICK=1`: prueba corta que escribe en otra carpeta.

**`scripts/collect_sysinfo.sh`** — guarda procesador, memoria, compilador y versión de MPI en
`results/sysinfo/<sistema>.txt`. Es la fuente de la tabla de metodología.

**`scripts/slurm_job.sh`** — plantilla para enviar el benchmark a un clúster con SLURM.

**`analysis/analyze.py`** — lee los CSV y calcula mediana, speedup, eficiencia y errores.

**`analysis/plot_*.py`** — dibujan las figuras.

---

## 11. Preguntas de código probables

**¿Qué pasa si paso N = 0?** `parse_args` lo rechaza: habría división por cero al calcular la estimación.

**¿Qué pasa si paso letras en lugar de un número?** `parse_u64` detecta que quedaron caracteres sin convertir y el programa termina con el mensaje de uso.

**¿Por qué las funciones del núcleo están copiadas en cada archivo en lugar de compartirse?**
A propósito: cada versión es un archivo autocontenido, y `diff serial_v1.c serial_v2.c` muestra
exactamente qué cambió entre versiones. Lo que sí es común (argumentos, tiempo, salida, generador) está en los `.h`.

**¿El resultado de `mpi_v2` depende de P?** Sí: con otro P cada proceso usa otros tramos de la
secuencia. Todas son estimaciones válidas. Con el mismo P y la misma semilla el resultado es idéntico.

**¿Dónde podría desbordar `uint64_t`?** En ningún caso realista: llega a 1,8 × 10¹⁹. Con N = 10¹⁰
el mayor contador (números generados para e) ronda 2,7 × 10¹⁰.

**¿Se pierde precisión al pasar el contador a `double`?** Un `double` representa exactamente todos
los enteros hasta 2⁵³ ≈ 9 × 10¹⁵. Los contadores están muy por debajo.

**¿Por qué el generador se siembra fuera de la zona cronometrada?** Es preparación, no cómputo. Su
costo (unos cientos de pasos) es despreciable y no depende de N.

**¿Por qué se usa `fprintf(stderr, ...)` para los errores?** Para que los mensajes de error no se
mezclen con la línea CSV que va por la salida estándar y que el script guarda en el archivo.

**¿Cómo verifiqué que el código es correcto?**
- Compila sin advertencias con `-Wall -Wextra -Wpedantic`.
- Ejecutado con los detectores de errores de memoria y de comportamiento indefinido del compilador
  (`-fsanitize=address,undefined`): sin hallazgos.
- Las estimaciones caen dentro del margen estadístico esperado para todos los N probados.
- V0 y V1 dan la misma estimación con la misma semilla (mismo generador, misma matemática).
- `mpi_v2` con P = 1 da exactamente lo mismo que `serial_v2`.
- El reparto suma exactamente N (probado también con N no divisible por P, como 100 000 007 con P = 3 y 7).
- `jump()` verificado contra un cálculo independiente de la potencia 2¹²⁸ de la matriz de transición.
