# 02 — El código, línea por línea

> **Apunte de estudio.** Describe el código de la rama `version-simple`. Conviene leerlo con el
> archivo de código abierto al lado.

Contenido:

0. Mapa del proyecto
1. Conceptos de C que aparecen en el código
2. `Makefile`
3. `montecarlo.h`
4. `montecarlo_serial.c`
5. `montecarlo_mpi.c`
6. `benchmark.sh`
7. `verificar_sistema.sh`
8. `graficos.py`
9. Cómo se verificó que el código es correcto
10. Preguntas de código probables

Los recuadros **"¿Por qué así y no de otra forma?"** son las respuestas para el profesor.

---

## 0. Mapa del proyecto

```
montecarlo.h            los dos experimentos, la lectura de argumentos y la salida (compartido)
montecarlo_serial.c     versión serial: la referencia para el speedup
montecarlo_mpi.c        versión paralela con MPI
Makefile                cómo se compilan los dos programas
benchmark.sh            corre todas las pruebas y guarda los tiempos en un CSV
verificar_sistema.sh    comprobación previa: herramientas, núcleos y una prueba de escalado
graficos.py             mediana, speedup, eficiencia, error y los gráficos
requirements.txt        librerías de Python necesarias
resultados/             lo que generan benchmark.sh y graficos.py
```

**Los dos programas tienen la misma forma:**

1. Leer los argumentos: qué constante (`pi` o `e`), N y, opcionalmente, la semilla.
2. Inicializar el generador de números aleatorios.
3. Tomar el tiempo, ejecutar el experimento, tomar el tiempo otra vez.
4. Convertir el contador en la estimación.
5. Imprimir una línea CSV.

La diferencia es que la versión MPI reparte las N muestras entre P procesos y al final suma los
contadores.

Se usan así:

```bash
./montecarlo_serial pi 1000000
./montecarlo_serial e 1000000 42          # con semilla 42
mpirun -np 4 ./montecarlo_mpi pi 100000000
```

y cada ejecución imprime una línea con siete campos:

```
constante,N,P,semilla,estimacion,error_abs,tiempo_s
pi,100000000,4,12345,3.1416764000,8.375e-05,0.553131
```

---

## 1. Conceptos de C que aparecen en el código

**`#include`** — "pegar acá el contenido de otro archivo". Con `< >` busca en las bibliotecas del
sistema (`<stdio.h>`); con `" "` busca en la carpeta del proyecto (`"montecarlo.h"`).

**Guardas de inclusión** — al principio y al final de `montecarlo.h`:

```c
#ifndef MONTECARLO_H
#define MONTECARLO_H
...
#endif
```

"Si todavía no se definió `MONTECARLO_H`, definilo y procesá el archivo." Evita que el mismo
archivo se incluya dos veces y aparezcan funciones definidas dos veces.

**`#define NOMBRE valor`** — una sustitución de texto antes de compilar. `#define CONSTANTE_PI 0`
hace que cada `CONSTANTE_PI` del código se reemplace por `0`. Sirve para dar nombre a los números.

**Tipos:**

| Tipo | Tamaño | Rango | Dónde se usa |
|---|---|---|---|
| `int` | 32 bits | hasta 2 147 483 647 (≈ 2,1 × 10⁹) | `rank`, `procesos`, `constante`: valores chicos, y lo que exige MPI |
| `long long` | al menos 64 bits | hasta ≈ 9,2 × 10¹⁸ | N, contadores, semilla |
| `double` | 64 bits, punto flotante | ≈ 15–16 dígitos significativos | coordenadas, sumas, estimación, tiempos |

**Arreglos** — `long long datos[3]` son tres `long long` seguidos en memoria: `datos[0]`,
`datos[1]` y `datos[2]`. Cuando un arreglo se pasa a una función, en realidad se pasa **la
dirección** de su primer elemento. Por eso `leer_argumentos(argc, argv, datos)` puede escribir
dentro de `datos` y el cambio se ve en `main`.

**Punteros y `&`** — `&x` es "la dirección de x". Se usa cuando una función tiene que **escribir**
en una variable de quien la llama: `MPI_Comm_rank(MPI_COMM_WORLD, &rank)` deja el número de proceso
en `rank`; `clock_gettime(CLOCK_MONOTONIC, &t)` llena la estructura `t`.

Analogía: en vez de darle a alguien una fotocopia de mi cuaderno, le digo en qué cajón está; lo que
escriba queda en **mi** cuaderno.

**`struct`** — varias variables agrupadas. `struct timespec` (de la biblioteca estándar) tiene dos
campos: `tv_sec` (segundos) y `tv_nsec` (nanosegundos). Se accede con punto: `t.tv_sec`.

**`static` delante de una función** — la función es privada del archivo donde queda. Como
`montecarlo.h` se incluye en los dos `.c`, cada programa recibe su propia copia y no hay conflicto.

**Operador ternario** — `condición ? valor_si_verdadero : valor_si_falso`. Es un `if/else` que
devuelve un valor: `(argc >= 4) ? atoll(argv[3]) : 12345`.

**Conversión explícita (cast)** — `(double)cuenta` convierte un entero a real. Hace falta antes de
dividir: `7 / 2` entre enteros da `3`; `(double)7 / 2` da `3.5`. `(int)datos[0]` convierte un
`long long` a `int`.

**`argc` y `argv`** — los argumentos de la línea de comandos. `argc` cuenta cuántos hay, incluido
el nombre del programa; `argv[0]` es el nombre, `argv[1]` el primero, etc. Son textos.

**Valor de retorno de `main`** — `return 0` significa "terminó bien"; cualquier otro valor
significa error. El script de pruebas y la terminal pueden leerlo.

---

## 2. `Makefile`

Un Makefile es una receta: qué archivos generar, de cuáles dependen y con qué comando. `make` solo
recompila lo que cambió.

```make
CFLAGS = -O2 -Wall -Wextra
```

| Opción | Qué hace |
|---|---|
| `-O2` | Optimización estándar: el compilador reordena y simplifica el código para que corra más rápido, sin transformaciones arriesgadas |
| `-Wall -Wextra` | Activa las advertencias. El proyecto compila sin ninguna |

```make
all: montecarlo_serial montecarlo_mpi
```

`all` es el objetivo por defecto: `make` sin argumentos compila los dos programas.

```make
montecarlo_serial: montecarlo_serial.c montecarlo.h
	gcc $(CFLAGS) montecarlo_serial.c -o montecarlo_serial -lm
```

"Para generar `montecarlo_serial` hacen falta `montecarlo_serial.c` y `montecarlo.h`; si alguno
cambió, ejecutar este comando." `-o` da el nombre del ejecutable; `-lm` enlaza la biblioteca
matemática (para `fabs`). Como `montecarlo.h` figura entre las dependencias, si cambia el `.h` se
recompilan los dos programas.

```make
montecarlo_mpi: montecarlo_mpi.c montecarlo.h
	mpicc $(CFLAGS) montecarlo_mpi.c -o montecarlo_mpi -lm
```

`mpicc` es un envoltorio de `gcc` que agrega las rutas y bibliotecas de MPI. Por dentro es el mismo compilador.

`clean` borra los ejecutables; `.PHONY` declara que `all` y `clean` son nombres de acciones, no de archivos.

> **¿Por qué las mismas opciones para los dos programas?**
> Para que la comparación sea justa: si el paralelo se compilara con más optimización, no sabría si
> la mejora viene de repartir el trabajo o del compilador.
>
> **¿Por qué `-O2` y no `-O3`?**
> `-O2` es el nivel habitual y seguro. `-O3` agrega transformaciones más agresivas; para este
> programa, cuyo costo está en generar números aleatorios, no cambia de forma apreciable el
> resultado. Con `-O2` hay menos que explicar y nada que perder.
>
> **¿Por qué no se pide un estándar de C con `-std=...`?**
> Sin esa opción `gcc` usa su modo por defecto (C17 con extensiones GNU), que incluye las funciones
> POSIX que usa el programa: `drand48` y `clock_gettime`. Con `-std=c11` estricto habría que
> habilitarlas a mano.

---

## 3. `montecarlo.h`

Todo lo que comparten los dos programas.

### 3.1 Constantes

```c
#define PI_REAL 3.14159265358979323846
#define E_REAL  2.71828182845904523536

#define CONSTANTE_PI 0
#define CONSTANTE_E  1
```

Los valores reales, para calcular el error, y dos nombres para identificar qué constante se estima.

> **¿Por qué no `M_PI`?** No es parte del estándar C; depende de cómo se compile. Definirlo a mano
> es portable y deja a la vista el valor usado.

### 3.2 `contar_aciertos_pi` — el experimento de π

```c
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
```

- `n` es cuántos puntos generar.
- `drand48()` devuelve un número al azar en [0, 1). Se llama dos veces: una coordenada cada vez.
- `x * x + y * y <= 1.0`: el punto está dentro del cuarto de círculo de radio 1.
- Devuelve **cuántos** cayeron dentro, no la estimación. La división se hace afuera.

> **¿Por qué `x * x + y * y <= 1.0` y no `sqrt(x*x + y*y) <= 1.0`?**
> La condición es "distancia al origen ≤ 1", o sea √(x² + y²) ≤ 1. Como los dos lados son no
> negativos, elevar al cuadrado no cambia la desigualdad: x² + y² ≤ 1. Se evita una raíz cuadrada
> en cada iteración, que es una operación cara. Con `x * x` en lugar de `pow(x, 2)` se evita además
> llamar a una función general de potencias para un simple cuadrado.
>
> **¿Por qué `<=` y no `<`?** Da lo mismo: el borde del círculo tiene área cero, la probabilidad de
> caer exactamente sobre él es nula.
>
> **¿Por qué devuelve el contador y no π?** Para que la versión MPI pueda **sumar** los contadores
> de todos los procesos. Sumar enteros es exacto; promediar estimaciones exigiría ponderar por la
> cantidad de muestras de cada proceso.
>
> **¿El `if` no es lento?** El procesador tiene que "adivinar" hacia dónde va un `if`, y con datos
> al azar a veces se equivoca. Con `-O2` el compilador puede convertir este `if` en una suma sin
> salto. En la rama `main` se probó escribir `aciertos += (condición)` directamente y no cambió el
> tiempo: el costo dominante es generar los números aleatorios. Se dejó el `if` porque es más claro.

### 3.3 `contar_sumandos_e` — el experimento de e

```c
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
```

- `n` es la cantidad de **ensayos**.
- Un ensayo por vuelta del `for`. `suma` vuelve a 0 al empezar cada ensayo.
- El `while` agrega números al azar mientras la suma no pase de 1, y cuenta cada número generado.
- `sumandos` **no** se reinicia entre ensayos: al final es el total de números generados.
- La estimación es `sumandos / n` (ejemplo a mano en el apunte 01, sección 3.2).

> **¿Por qué no se guarda la cantidad de cada ensayo?** No hace falta: para el promedio alcanza con
> el total. Guardar cada valor necesitaría un arreglo de n elementos (8 GB para n = 10⁹).
>
> **¿Por qué `long long`?** Con n = 10⁹ ensayos se generan en promedio 2,72 × 10⁹ números: un
> `int` (hasta 2,1 × 10⁹) ya desbordaría. `long long` llega a 9,2 × 10¹⁸.
>
> **¿El `while` se puede evitar?** No: cuántos números hacen falta depende de los números mismos.
> Es una característica del algoritmo de e.

### 3.4 `drand48` — el generador de números aleatorios

**En simple.** Una computadora no tira dados. Un generador pseudoaleatorio es una fórmula que, a
partir de un número (el *estado*), calcula el siguiente, y la sucesión *parece* azar. Es como una
lista larguísima de números ya escrita: la **semilla** dice desde dónde empiezo a leer. Misma
semilla, misma lista: por eso los resultados son reproducibles.

**Para el profesor.** `drand48` es un *generador congruencial lineal* de 48 bits:

$$X_{n+1} = (a \cdot X_n + c) \bmod 2^{48}, \qquad a = \texttt{0x5DEECE66D},\; c = 11$$

y devuelve X / 2⁴⁸, un real en [0, 1). Su período es 2⁴⁸ ≈ 2,8 × 10¹⁴. El algoritmo y las
constantes los fija el estándar POSIX: da los mismos números en cualquier Linux.
`srand48(semilla)` pone el estado inicial: los 32 bits altos son la semilla y los 16 bajos un
valor fijo (0x330E).

> **¿Por qué `drand48` y no `rand()`?**
>
> | | `rand()` | `drand48()` |
> |---|---|---|
> | Bits | El estándar solo garantiza 15 (`RAND_MAX` ≥ 32767) | 48 siempre |
> | Resultado | Entero: hay que dividir por `RAND_MAX` | Directamente un real en [0, 1) |
> | Portabilidad | Algoritmo y calidad dependen del sistema | El algoritmo está fijado por POSIX |
> | Período | Depende de la implementación | 2⁴⁸ ≈ 2,8 × 10¹⁴ |
>
> **¿Alcanza el período?** El caso más grande (N = 10⁹ para e) consume unos 2,7 × 10⁹ números. El
> período es cien mil veces mayor.
>
> **¿Tiene estado global? ¿No es un problema en paralelo?** Sí, tiene estado global, pero en MPI
> cada proceso es un programa aparte con **su propia memoria**: cada uno tiene su propia copia del
> estado y no se pisan. Sería un problema con **hilos** (OpenMP), que comparten memoria: ahí habría
> que usar `erand48`, que recibe el estado como parámetro.
>
> **¿Es un buen generador?** Es suficiente para este trabajo: el error medido sigue la ley
> teórica. No es moderno: los generadores congruenciales tienen patrones conocidos en sus bits bajos
> y no pasan las baterías de pruebas estadísticas más exigentes. La alternativa moderna
> (xoshiro256\*\*, en la rama `main`) es más rápida y de mejor calidad, a cambio de unas 60 líneas
> de código con operaciones de bits.

### 3.5 `calcular_estimacion`

```c
if (constante == CONSTANTE_PI) {
    return 4.0 * (double)cuenta / (double)n;    /* pi = 4 * aciertos / N */
}
return (double)cuenta / (double)n;              /* e = sumandos / N */
```

Convierte el contador en la estimación. Los `(double)` fuerzan la división real: sin ellos,
`cuenta / n` entre enteros daría 0 (π) o 2 (e).

> **¿Se pierde precisión al pasar el contador a `double`?** No: un `double` representa exactamente
> todos los enteros hasta 2⁵³ ≈ 9 × 10¹⁵, y los contadores están muy por debajo.

### 3.6 `leer_argumentos`

```c
static int leer_argumentos(int argc, char *argv[], long long datos[3])
```

Recibe los argumentos de la línea de comandos y deja tres valores en `datos`: la constante, N y la
semilla. Devuelve 1 si son válidos y 0 si no.

```c
if (argc < 3) {
    fprintf(stderr, "Uso: %s <pi|e> <N> [semilla]\n", argv[0]);
    return 0;
}
```

Hacen falta al menos 3: el nombre del programa, la constante y N. `fprintf(stderr, …)` escribe en
la **salida de errores**, separada de la salida normal: así un mensaje de error no se mezcla con la
línea CSV que guarda el script.

```c
if (strcmp(argv[1], "pi") == 0) {
    datos[0] = CONSTANTE_PI;
} else if (strcmp(argv[1], "e") == 0) {
    datos[0] = CONSTANTE_E;
} else { ... return 0; }
```

`strcmp` compara dos textos y devuelve 0 si son iguales. (En C no se pueden comparar textos con `==`:
eso compara direcciones de memoria, no contenidos.)

```c
datos[1] = atoll(argv[2]);
if (datos[1] <= 0) { ... return 0; }
```

`atoll` convierte texto en `long long`. Se exige N > 0: con N = 0 habría una división por cero al
calcular la estimación.

```c
datos[2] = (argc >= 4) ? atoll(argv[3]) : 12345;
```

La semilla es opcional; si no se pasa, se usa 12345.

> **¿Por qué los tres valores en un arreglo y no en tres variables?** Para que la versión MPI los
> pueda enviar a todos los procesos con **una sola** comunicación (sección 5).
>
> **Limitación conocida de `atoll`:** no avisa si el texto no es un número. `atoll("abc")` da 0 (y
> se rechaza por N > 0), pero `atoll("100abc")` da 100 y se acepta. La forma robusta es `strtoll`,
> que indica dónde dejó de leer. Está en la lista de mejoras (apunte 05).

### 3.7 `imprimir_resultado`

```c
double real = (constante == CONSTANTE_PI) ? PI_REAL : E_REAL;

printf("%s,%lld,%d,%lld,%.10f,%.3e,%.6f\n",
       (constante == CONSTANTE_PI) ? "pi" : "e",
       n, procesos, semilla, estimacion, fabs(estimacion - real), tiempo);
```

Una línea CSV. `%lld` es el formato de `long long`; `%.10f`, 10 decimales; `%.3e`, notación
científica; `fabs`, valor absoluto de un `double`.

> **¿Por qué CSV y no un mensaje para humanos?** Porque los resultados los procesa un script: el
> benchmark solo agrega cada línea a un archivo y Python lo lee directo.

---

## 4. `montecarlo_serial.c`

```c
static double segundos(void)
{
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec + t.tv_nsec / 1e9;
}
```

El cronómetro: devuelve segundos desde un punto fijo, con resolución de nanosegundos. Suma los
segundos enteros y los nanosegundos convertidos a segundos.

> **¿Por qué `CLOCK_MONOTONIC` y no `clock()` o `time()`?**
> `time()` tiene resolución de 1 segundo. `clock()` mide tiempo de **CPU**, no tiempo real.
> `CLOCK_MONOTONIC` mide tiempo real y **nunca retrocede**: no lo afecta que el sistema ajuste la
> hora en medio de la medición. Es el equivalente de `MPI_Wtime()` de la versión paralela.

```c
long long datos[3];

if (!leer_argumentos(argc, argv, datos)) {
    return 1;
}
int constante = (int)datos[0];
long long n = datos[1];
long long semilla = datos[2];
```

Lee los argumentos; si son inválidos, termina con código 1. Después copia cada dato a una variable
con nombre, para que el resto se lea mejor.

```c
srand48(semilla);
```

Inicializa el generador.

```c
double inicio = segundos();

long long cuenta;
if (constante == CONSTANTE_PI) {
    cuenta = contar_aciertos_pi(n);
} else {
    cuenta = contar_sumandos_e(n);
}

double fin = segundos();
```

Solo se cronometra el experimento: ni la lectura de argumentos ni la impresión.

```c
double estimacion = calcular_estimacion(constante, cuenta, n);
imprimir_resultado(constante, n, 1, semilla, estimacion, fin - inicio);
return 0;
```

El `1` es P: la versión serial usa un proceso.

> **¿Para qué existe la versión serial si la MPI con P = 1 hace lo mismo?** Porque el speedup se
> define contra el **mejor programa serial**, sin nada de MPI. Así la comparación incluye lo que
> cuesta usar MPI. Además sirve de verificación: con la misma semilla, `montecarlo_mpi` con un
> proceso da exactamente el mismo resultado que `montecarlo_serial` (lo comprobé).

---

## 5. `montecarlo_mpi.c`

### 5.1 Qué es MPI, en simple

MPI (*Message Passing Interface*) lanza **P copias del mismo programa**. Cada copia es un proceso
separado, con su propia memoria: **no comparten variables**. Lo único que las distingue es un
número, el **rango** (*rank*), de 0 a P − 1. Si una necesita algo de otra, se lo tiene que enviar
por mensaje.

Analogía: P empleados en oficinas separadas, todos con el mismo manual. El manual dice "si sos el
número 0, hacé esto; todos, hagan aquello". Se comunican solo por correo.

`mpirun -np 4 ./montecarlo_mpi pi 1000000` lanza 4 copias.

### 5.2 El código, bloque por bloque

```c
int rank, procesos;
long long datos[3] = {0, 0, 0};     /* constante, N, semilla */

MPI_Init(&argc, &argv);
MPI_Comm_rank(MPI_COMM_WORLD, &rank);
MPI_Comm_size(MPI_COMM_WORLD, &procesos);
```

- `MPI_Init` enciende MPI; tiene que ser la primera llamada MPI.
- `MPI_COMM_WORLD` es el grupo que incluye a todos los procesos.
- `MPI_Comm_rank` deja en `rank` quién soy (0 a P − 1); `MPI_Comm_size` deja en `procesos` cuántos somos (P).
- `datos` se inicializa en ceros para que los procesos que no leen argumentos no tengan basura antes de recibirlos.

**Paso 1 — leer y difundir los parámetros**

```c
if (rank == 0) {
    if (!leer_argumentos(argc, argv, datos)) {
        MPI_Abort(MPI_COMM_WORLD, 1);
    }
}
MPI_Bcast(datos, 3, MPI_LONG_LONG, 0, MPI_COMM_WORLD);
```

Solo el proceso 0 interpreta los argumentos. `MPI_Bcast` (*broadcast*, difusión) envía un dato del
proceso raíz a todos:

| Argumento | Valor | Significado |
|---|---|---|
| buffer | `datos` | qué se envía / dónde se recibe |
| cantidad | `3` | cuántos elementos |
| tipo | `MPI_LONG_LONG` | de qué tipo son |
| raíz | `0` | quién envía |
| comunicador | `MPI_COMM_WORLD` | a qué grupo |

**Todos** los procesos ejecutan la misma línea: en el 0 significa "enviar"; en los demás,
"recibir". Después de esa línea, todos tienen los mismos tres valores.

> **¿Por qué `MPI_Bcast` si cada proceso podría leer `argv`?** En la práctica `mpirun` suele pasar
> los argumentos a todos, pero el estándar MPI no lo garantiza. Con un único punto de lectura y una
> difusión explícita, todos trabajan con los mismos parámetros y la validación se hace una vez.
>
> **¿Por qué `MPI_Abort` si los argumentos son inválidos?** Termina **todos** los procesos. Si solo
> terminara el 0, los demás quedarían esperando para siempre en `MPI_Bcast` un mensaje que nunca llega.
>
> **¿Por qué en un arreglo?** Una sola comunicación en lugar de tres.

```c
int constante = (int)datos[0];
long long n = datos[1];
long long semilla = datos[2];
```

**Paso 2 — repartir el trabajo**

```c
long long n_local = n / procesos;
if (rank < n % procesos) {
    n_local++;
}
```

- `n / procesos`: división entera, lo que le toca a cada uno como mínimo.
- `n % procesos`: el resto, lo que sobra.
- Los primeros "resto" procesos hacen una muestra más.

**Ejemplo con N = 10 y P = 3:** 10 / 3 = 3 y 10 % 3 = 1.

| Proceso | ¿rank < 1? | n_local |
|---|---|---|
| 0 | sí | 3 + 1 = **4** |
| 1 | no | **3** |
| 2 | no | **3** |
| Total | | **10** |

Otro: N = 11, P = 4 → cociente 2, resto 3 → 3, 3, 3, 2.

Analogía: repartir 10 caramelos entre 3 chicos; tres a cada uno y el que sobra para el primero.

> **¿Por qué así?**
> - La suma es **exactamente** N: no se pierde ni se duplica ninguna muestra.
> - El desbalance máximo es de **una** muestra: ningún proceso espera a otro de forma apreciable.
> - Cada proceso calcula su parte solo, con N, P y su rango: no hace falta comunicación.
> - Alternativa descartada: darle todo el resto al último proceso. Lo carga más, y el tiempo total
>   lo marca el proceso más lento.
>
> **¿Puede haber condiciones de carrera?** No, por construcción: una condición de carrera necesita
> memoria compartida, y en MPI cada proceso tiene la suya.
>
> **¿Y si N < P?** Algunos procesos reciben `n_local = 0`, no hacen ninguna vuelta del bucle y
> aportan 0 a la suma. Funciona.

**Paso 3 — números aleatorios distintos en cada proceso**

```c
srand48(semilla + rank);
```

El proceso 0 usa la semilla, el 1 usa semilla + 1, y así.

> **¿Por qué una semilla distinta por proceso?**
> Si todos usaran la misma, generarían **los mismos números**. Con 4 procesos tendría 4 copias de
> las mismas muestras: el tiempo bajaría, pero el error sería el de N/4 muestras. El speedup se
> vería bien y el resultado sería peor. Es el error clásico de Monte Carlo en paralelo.
>
> **¿Garantiza que no se repitan?** **No**, y hay que decirlo así. Semillas distintas hacen que cada
> proceso arranque en otro punto de la misma secuencia de 2⁴⁸ números. Como cada proceso consume una
> porción ínfima de esa secuencia (como mucho unos 10⁹ números de 2,8 × 10¹⁴), es muy improbable
> que dos tramos se solapen, pero no está garantizado.
>
> **¿Cómo sé que en la práctica funciona?** El error de las ejecuciones paralelas sigue la recta
> teórica σ/√N. En una prueba con 40 ejecuciones de 8 procesos y N = 10⁶, el cociente entre el
> error medido y el teórico fue 1,01 para π y 0,84 para e. Si los procesos repitieran números, el
> error sería claramente mayor que el teórico. El gráfico `error.png` lo muestra con todos los datos.
>
> **¿Cuál sería la solución rigurosa?** Un generador con secuencias independientes garantizadas por
> proceso: por ejemplo xoshiro256\*\* con su función de salto (*jump*), que adelanta la secuencia
> 2¹²⁸ posiciones, o generadores basados en contador como Philox. Está implementado en la rama
> `main` y figura como mejora futura.
>
> **Experimento para entenderlo:** cambiar la línea por `srand48(semilla);`, correr con 4 procesos
> varias veces y comparar el error con el de la versión correcta. Después volverla atrás.

**Paso 4 — el cómputo cronometrado**

```c
MPI_Barrier(MPI_COMM_WORLD);
double inicio = MPI_Wtime();

long long cuenta_local;
if (constante == CONSTANTE_PI) {
    cuenta_local = contar_aciertos_pi(n_local);
} else {
    cuenta_local = contar_sumandos_e(n_local);
}

long long cuenta_total = 0;
MPI_Reduce(&cuenta_local, &cuenta_total, 1, MPI_LONG_LONG, MPI_SUM, 0, MPI_COMM_WORLD);

double fin = MPI_Wtime();
```

- **`MPI_Barrier`**: nadie pasa de esta línea hasta que **todos** llegaron. Es la línea de largada.
- **`MPI_Wtime`**: tiempo de reloj en segundos (`double`).
- Cada proceso ejecuta el mismo experimento que la versión serial, con `n_local` muestras y **sin comunicarse**.
- **`MPI_Reduce`**: combina un valor de cada proceso en uno solo, en el proceso raíz.

| Argumento | Valor | Significado |
|---|---|---|
| dato a enviar | `&cuenta_local` | lo que aporta cada proceso |
| resultado | `&cuenta_total` | dónde queda la combinación (solo válido en la raíz) |
| cantidad | `1` | un elemento |
| tipo | `MPI_LONG_LONG` | entero de 64 bits |
| operación | `MPI_SUM` | sumar |
| raíz | `0` | quién recibe el resultado |
| comunicador | `MPI_COMM_WORLD` | qué grupo |

> **¿Por qué `MPI_Barrier` antes de tomar el tiempo?** Los procesos no arrancan en el mismo
> instante. Sin la barrera, el proceso 0 podría empezar a cronometrar con otros todavía sin llegar,
> y mediría esa espera. La barrera hace que el cronómetro mida solo cómputo y reducción.
>
> **¿Por qué el tiempo lo toma el proceso 0 después de `MPI_Reduce`?** En la raíz, `MPI_Reduce` no
> termina hasta recibir el aporte de **todos**. Entonces `fin - inicio` incluye hasta el proceso más
> lento más la comunicación: es el tiempo real de la parte paralela.
>
> **¿Por qué `MPI_Reduce` y no `MPI_Send`/`MPI_Recv`?** El patrón es "P números → una suma": es
> exactamente una reducción. Con envíos a mano, el proceso 0 recibiría P − 1 mensajes uno tras otro;
> `MPI_Reduce` puede organizarse internamente en forma de árbol (unas log₂ P etapas). Además es una
> línea en lugar de un bucle: menos lugar para errores.
>
> **¿Por qué no comunicación no bloqueante (`MPI_Ireduce`)?** Sirve para seguir calculando mientras
> el mensaje viaja. Acá el cálculo ya terminó cuando se comunica: no hay nada que superponer.
>
> **¿Qué queda fuera del tiempo medido?** `MPI_Init`, la lectura de argumentos, `MPI_Bcast`,
> `srand48` y `MPI_Finalize`. El costo de lanzar los procesos e inicializar MPI es fijo (en la
> notebook ronda 0,3 a 0,4 s, medido en la rama `main`) y no depende de N. Por eso con N chico no
> conviene paralelizar (apunte 03).

**Paso 5 — el resultado**

```c
if (rank == 0) {
    double estimacion = calcular_estimacion(constante, cuenta_total, n);
    imprimir_resultado(constante, n, procesos, semilla, estimacion, fin - inicio);
}

MPI_Finalize();
return 0;
```

Solo el proceso 0 tiene el total, así que solo él calcula e imprime. `MPI_Finalize` apaga MPI; la
ejecutan todos y es la última llamada MPI.

### 5.3 Resumen del flujo

```
todos:      MPI_Init → rank, procesos
proceso 0:  leer_argumentos            (si falla, MPI_Abort)
todos:      MPI_Bcast                  (0 envía, el resto recibe)
todos:      n_local, srand48(semilla + rank)
todos:      MPI_Barrier                (largada)
todos:      inicio = MPI_Wtime()
todos:      experimento con n_local    (sin comunicarse)
todos:      MPI_Reduce                 (los contadores se suman en el proceso 0)
todos:      fin = MPI_Wtime()
proceso 0:  calcula la estimación e imprime
todos:      MPI_Finalize
```

Comunicaciones en total: **una difusión y una reducción**, sin importar N.

> **¿Por qué el serial y el paralelo comparten `montecarlo.h`?** Para que ejecuten **exactamente el
> mismo código** de cómputo. Así el speedup mide solo el efecto de repartir el trabajo, no dos
> implementaciones distintas.

---

## 6. `benchmark.sh`

Corre todas las pruebas y guarda una línea CSV por ejecución.

```bash
SISTEMA=${1:-pc}
TAMANIOS=${TAMANIOS:-"100000 1000000 10000000 100000000 1000000000"}
PROCESOS=${PROCESOS:-"1 2 4 8"}
REPETICIONES=${REPETICIONES:-5}
OPCIONES_MPI=${OPCIONES_MPI:-"--oversubscribe"}
```

- `${1:-pc}`: el primer argumento del script, o `pc` si no se pasó. Define el nombre de los archivos de salida.
- `${TAMANIOS:-"…"}`: usa la variable de entorno si existe, o el valor por defecto. Así se puede cambiar qué se prueba sin editar el script.
- `--oversubscribe`: Open MPI cuenta núcleos físicos y se niega a lanzar más procesos que esos
  (por ejemplo, 8 en una notebook de 4 núcleos). Esta opción lo permite.

```bash
make || exit 1
```

Compila; si falla, no sigue.

```bash
lscpu > resultados/sistema_$SISTEMA.txt
echo "CPUs disponibles (nproc): $(nproc)" >> resultados/sistema_$SISTEMA.txt
if [ -f /sys/fs/cgroup/cpu.max ]; then
    echo "Limite de CPU del contenedor (cpu.max): ..." >> resultados/sistema_$SISTEMA.txt
fi
```

Guarda la descripción del sistema para el informe. `>` crea el archivo; `>>` agrega al final.
Dentro de un contenedor (como el del clúster), `lscpu` describe la máquina completa; lo que
realmente se asignó se ve con `nproc` y con el límite de CPU del contenedor.

```bash
echo "programa,constante,N,P,semilla,estimacion,error_abs,tiempo_s" > $SALIDA
```

La primera línea del CSV: los nombres de las columnas.

```bash
for CONSTANTE in pi e; do
    for N in $TAMANIOS; do
        for REP in $(seq 1 $REPETICIONES); do
            SEMILLA=$((REP * 100000))
            echo "serial,$(./montecarlo_serial $CONSTANTE $N $SEMILLA)" >> $SALIDA

            for P in $PROCESOS; do
                SEMILLA=$((REP * 100000 + P * 1000))
                echo "mpi,$(mpirun $OPCIONES_MPI -np $P ./montecarlo_mpi $CONSTANTE $N $SEMILLA)" >> $SALIDA
            done
        done
    done
done
```

- `$(comando)` ejecuta el comando y pone su salida en ese lugar. `echo "serial,$(...)"` antepone la
  columna `programa` a la línea que imprime el programa.
- `$((...))` hace una cuenta entera en bash.
- Por cada constante, cada N y cada repetición: una ejecución serial y una MPI por cada P.

> **¿Por qué varias repeticiones y la mediana?** El sistema operativo puede **demorar** una
> ejecución (otra tarea, una interrupción), nunca acelerarla. La mediana ignora ese valor atípico;
> el promedio no. Se usa un número impar (5) para que la mediana sea una medición real y no el
> promedio de dos.
>
> **¿Por qué esas semillas?** Cada proceso MPI suma su rango a la semilla. Si las ejecuciones
> usaran semillas 1, 2, 3…, el proceso 1 de una ejecución repetiría la semilla del proceso 0 de la
> siguiente. Con huecos de 1000 entre valores de P y de 100000 entre repeticiones, ninguna ejecución
> repite semillas de otra mientras P sea menor que 100. (La primera versión usaba huecos de 100 y
> repetía 20 semillas con P hasta 24; se corrigió al conocer los datos del clúster.)
>
> **¿Por qué semillas distintas en cada repetición, si lo que interesa es el tiempo?** Porque así
> cada ejecución es una muestra independiente y sirve también para estudiar el error.
>
> **¿Por qué el serial se corre dentro del mismo bucle y no todo junto al principio?** Para que
> serial y paralelo se midan en el mismo momento y con el mismo estado de la máquina.
>
> **Limitación:** si una ejecución falla, `echo` igual escribe una línea incompleta (`mpi,`). Al
> analizar, esa línea queda sin datos y se descarta, pero conviene revisar el CSV después de correr.

---

## 7. `verificar_sistema.sh`

Comprobación previa, pensada para el clúster.

- Recorre `gcc make mpicc mpirun python3` y con `command -v` dice si cada uno está instalado.
- Muestra el procesador (`lscpu`), cuántas CPU hay disponibles (`nproc`), el límite de CPU del
  contenedor si existe, y el usuario (Open MPI se niega a correr como `root` salvo que se le indique).
- Compila y hace una prueba de escalado: π con N = 2 × 10⁸, en serie y con 1, la mitad y el máximo
  de procesos indicado.

> **¿Para qué la prueba de escalado?** Para saber si los "núcleos" asignados son núcleos físicos o
> hilos lógicos. Si con el doble de procesos el tiempo casi no baja, cada par de "núcleos"
> comparte un núcleo físico (dos hilos lógicos). Es un dato necesario para explicar dónde se dobla
> la curva de speedup.

---

## 8. `graficos.py`

Lee los CSV, calcula las métricas y dibuja. Lo importante es entender **qué calcula**; el código
de dibujo no hace falta saberlo de memoria.

**Constantes del principio.** `REAL` tiene π y e; `SIGMA` el desvío teórico de una muestra
(1,642 para π y 0,875 para e, ver apunte 01, sección 6), que se usa para dibujar la recta teórica
del error.

**`cargar_datos`.** Busca todos los `resultados/tiempos_*.csv`, los une en una sola tabla y agrega
una columna `sistema` con el nombre tomado del archivo (`tiempos_pc.csv` → `pc`).

**`calcular_resumen`** — el corazón del análisis:

```python
medianas = (datos.groupby(["sistema", "programa", "constante", "N", "P"])["tiempo_s"]
            .median()...)
```

Agrupa las ejecuciones de la misma configuración y toma la **mediana** del tiempo.

```python
serial = medianas[medianas["programa"] == "serial"]
resumen = medianas[medianas["programa"] == "mpi"].merge(serial, on=["sistema", "constante", "N"])
resumen["speedup"] = resumen["t_serial"] / resumen["t_mediana"]
resumen["eficiencia"] = resumen["speedup"] / resumen["P"]
```

Pone, al lado de cada configuración MPI, el tiempo serial del mismo sistema, constante y N, y calcula:

$$S_P = \frac{T_{\text{serial}}}{T_P}, \qquad E_P = \frac{S_P}{P}$$

**`grafico_error`.** Para cada N calcula la raíz del error cuadrático medio de todas las
ejecuciones, √(promedio de error²), que es lo que se compara con σ/√N. Después ajusta una recta a
log(error) contra log(N) con `np.polyfit`; la pendiente debería dar cerca de −0,5.

> **¿Por qué la raíz del error cuadrático medio y no el promedio del error?** Porque σ/√N es,
> justamente, la raíz del error cuadrático medio esperado. El promedio del valor absoluto del error
> da un poco menos (alrededor de 0,8 σ/√N), y la comparación con la recta no sería directa.

**`eje_de_procesos`.** Marca en el eje los valores de P medidos. Si el barrido pasa de 32 procesos
usa escala logarítmica, porque en escala lineal 1, 2, 4 y 8 quedarían amontonados.

**Los demás `grafico_*`** dibujan: `intuicion` (genera sus propios puntos con NumPy, no usa los
resultados), `convergencia`, `tiempo_<sistema>`, `speedup_<sistema>` y `eficiencia`. Qué muestra
cada uno y por qué tiene esa forma está en el apunte 03.

---

## 9. Cómo se verificó que el código es correcto

- Compila sin advertencias con `-Wall -Wextra`.
- Las estimaciones caen dentro del margen estadístico esperado.
- Con la misma semilla, `montecarlo_mpi` con un proceso da exactamente el mismo resultado que `montecarlo_serial`.
- La fórmula de reparto se comprobó con 20 000 combinaciones al azar de N y P: siempre suma exactamente N y la diferencia entre procesos nunca pasa de 1.
- Argumentos inválidos (sin argumentos, N negativo, constante desconocida) se rechazan con un mensaje.
- El error de las ejecuciones paralelas sigue la ley teórica (40 ejecuciones con 8 procesos: cociente medido/teórico 1,01 en π y 0,84 en e).

---

## 10. Preguntas de código probables

**¿Qué pasa si paso N = 0?** `leer_argumentos` lo rechaza: habría división por cero al calcular la estimación.

**¿Qué pasa si escribo letras en lugar de N?** `atoll("abc")` da 0 y se rechaza. `atoll("100abc")` se acepta como 100: es la limitación de `atoll` (sección 3.6).

**¿El resultado de la versión MPI depende de P?** Sí: con otro P cada proceso usa otros tramos de la
secuencia. Todas son estimaciones válidas. Con el mismo P y la misma semilla el resultado es idéntico.

**¿Dónde podría desbordar `long long`?** En ningún caso realista: llega a 9,2 × 10¹⁸ y el mayor
contador (los sumandos de e con N = 10¹⁰) ronda 2,7 × 10¹⁰.

**¿Por qué `int` para `rank` y `procesos`?** Porque así lo define la interfaz de MPI, y nunca van a ser grandes.

**¿Por qué `srand48` va fuera de la zona cronometrada?** Es preparación, no cómputo, y su costo no depende de N.

**¿Qué pasa si un proceso termina antes que otros?** Espera en `MPI_Reduce`. Con el reparto de a lo
sumo una muestra de diferencia, la espera es despreciable.

**¿Se podría usar OpenMP en lugar de MPI?** Sí, dentro de una sola máquina. Habría que cambiar
`drand48` por `erand48` con un estado por hilo, porque los hilos comparten memoria. MPI permite,
además, usar varias máquinas.

**¿Cuánto tarda cada muestra?** En una prueba informal en la notebook: unos 19 ns por punto para π y
unos 46 ns por ensayo para e (cada ensayo genera en promedio 2,72 números). Los valores medidos del
benchmark están en `resultados/resumen.csv`.
