# 04 — La versión simple (rama `version-simple`)

> **Apunte de estudio.** Describe la rama `version-simple`. Está en las dos ramas, con el mismo contenido.

Contenido:

1. Qué es esta rama y en qué se diferencia de `main`
2. Qué pide la consigna y dónde está cada cosa
3. Decisiones y sus justificaciones
4. El código, bloque por bloque
5. Cómo correr el benchmark y hacer los gráficos
6. Qué esperar en cada gráfico
7. Guion de introducción para esta versión
8. Limitaciones y mejoras futuras
9. Preguntas probables
10. Cuál de las dos versiones presentar

---

## 1. Qué es esta rama y en qué se diferencia de `main`

Es el mismo proyecto, reducido a lo que pide la consigna: una versión serial, una versión MPI, un
script de pruebas y un script de gráficos. Unas 230 líneas de C en total, contra unas 650 de `main`.

Para cambiar de rama: `git switch version-simple` o `git switch main`.

| | `main` | `version-simple` |
|---|---|---|
| Programas | 5 (`serial_v0/v1/v2`, `mpi_v0/v2`) | 2 (`montecarlo_serial`, `montecarlo_mpi`) |
| Archivos de código | 7 en `src/` | 3 en la raíz (`montecarlo.h` + 2 `.c`) |
| Generador | xoshiro256\*\* propio (`prng.h`) con `splitmix64` y `jump()` | `drand48()` de la biblioteca estándar |
| Números por proceso | Tramos disjuntos garantizados (`jump`) | Semilla + número de proceso (sin garantía) |
| Tipos | `uint64_t`, `MPI_UINT64_T` | `long long`, `MPI_LONG_LONG` |
| Progresión de optimizaciones | V0 → V1 → V2, medida | No hay: una sola versión, ya sin `sqrt` |
| Lectura de argumentos | `strtoull` con validación completa | `atoll` y chequeo de N > 0 |
| Flags | `-std=c11 -O3 -march=native -Wpedantic …` | `-O2 -Wall -Wextra` |
| Benchmark | 12 variables de entorno, límites por programa, `wall_s` | Un bucle simple, 4 variables |
| Repeticiones | 7 | 5 |
| Análisis | 5 scripts de Python | 1 script (`graficos.py`) |
| Figuras | 10 | 7 |
| Nombres | Inglés | Español |

**Lo que se mantiene igual**, porque es el corazón del trabajo: los dos experimentos, el reparto
`N / P` más el resto, `MPI_Bcast` + `MPI_Reduce`, `MPI_Barrier` + `MPI_Wtime`, la mediana, y las
fórmulas de speedup, eficiencia y error.

**Lo que va "un poco más lejos" de la consigna** en esta versión:

- Eficiencia además de speedup.
- Comparación del error medido con la recta teórica σ/√N y la pendiente ajustada.
- Gráfico de intuición de los dos experimentos.
- Se guarda la descripción del sistema (`lscpu`) junto con los resultados.
- Semillas distintas en cada ejecución, para que las estimaciones sirvan para estudiar el error.

**Importante:** los números del apunte 03 y del informe en `docs/` se midieron con el código de
`main`. **No valen para esta rama.** Si se presenta esta versión, hay que correr el benchmark de
nuevo (sección 5) y reescribir las cifras. La teoría (apunte 01) vale igual para las dos.

---

## 2. Qué pide la consigna y dónde está cada cosa

| Consigna | Dónde |
|---|---|
| Investigar el problema, objetivos, limitaciones y estrategias | README: "El problema", "Convergencia", "Limitaciones". Apunte 01 |
| Implementación paralela, de la manera más adecuada de paralelizar | `montecarlo_mpi.c`. README: "Cómo se paralelizó" |
| Seleccionar o generar los datos para las pruebas | Los datos son los números aleatorios; se generan con `drand48` y semillas controladas |
| Correr en diferentes sistemas | `./benchmark.sh pc` y `./benchmark.sh servidor` |
| Speedup con la mediana de múltiples ejecuciones | `graficos.py`, función `calcular_resumen` |
| Múltiples simulaciones cambiando las variables | Se varían N (5 valores), P (4 valores) y la constante (π y e) |
| Convergencia y error al aumentar las simulaciones | `convergencia.png` y `error.png` |
| Concluir sobre los resultados | Se escribe después de medir (guía en la sección 6) |
| Mejoras para futuros casos | README: "Limitaciones y mejoras futuras" |
| Bibliografía | README: "Bibliografía" |

Sobre la bibliografía: están listadas fuentes reales y pertinentes. Conviene al menos hojear las
que se citan (el capítulo de MPI de Pacheco y la página de manual de `drand48`, que se abre con
`man drand48`), porque pueden preguntar de dónde salió algo.

---

## 3. Decisiones y sus justificaciones

### 3.1 Un encabezado compartido (`montecarlo.h`)

**Qué:** los dos experimentos están en un `.h` que incluyen el programa serial y el MPI.

**Por qué:** así el serial y el paralelo ejecutan **exactamente el mismo código** de cómputo. El
speedup compara entonces solo el efecto de repartir el trabajo, no dos implementaciones distintas.
Además no hay código duplicado que mantener.

**Por qué `static`:** las funciones están definidas en el encabezado; `static` hace que cada
programa tenga su copia privada y no haya conflictos al enlazar.

### 3.2 `drand48()` como generador

**Qué:** `drand48()` devuelve un real uniforme en [0, 1). `srand48(semilla)` fija la semilla.

**En simple:** es una fórmula que a partir de un número de 48 bits calcula el siguiente:
Xₙ₊₁ = (a · Xₙ + c) mod 2⁴⁸. Se llama *generador congruencial lineal*. El resultado dividido por
2⁴⁸ da un número entre 0 y 1.

**Por qué y no `rand()`:**

| | `rand()` | `drand48()` |
|---|---|---|
| Bits | El estándar solo garantiza 15 (`RAND_MAX` ≥ 32767) | 48 siempre |
| Resultado | Entero: hay que dividir por `RAND_MAX` | Directamente un real en [0, 1) |
| Portabilidad | La calidad depende del sistema | El algoritmo está fijado por el estándar POSIX: da los mismos números en cualquier Linux |
| Período | Depende de la implementación | 2⁴⁸ ≈ 2,8 × 10¹⁴ |

**¿Alcanza el período?** El caso más grande (N = 10⁹ para e) consume unos 2,7 × 10⁹ números. El
período es cien mil veces mayor.

**¿No tiene estado global? ¿No es un problema en paralelo?** Tiene estado global, sí. Pero en MPI
cada proceso es un programa aparte con **su propia memoria**: cada uno tiene su propia copia del
estado y no se pisan. El estado global sería un problema con **hilos** (OpenMP), donde todos
comparten memoria; ahí habría que usar `erand48` con un estado por hilo.

**Por qué no el generador de `main` (xoshiro256\*\*):** es mejor, pero son 60 líneas más de código
con operaciones de bits que hay que poder explicar. Para lo que pide la consigna, `drand48` alcanza
y viene en la biblioteca estándar. Queda mencionado como mejora futura.

### 3.3 Semilla distinta por proceso: `srand48(semilla + rank)`

**Qué:** el proceso 0 usa la semilla, el 1 usa semilla + 1, etc.

**Por qué:** si todos usaran la misma semilla, generarían **los mismos números**. Con 4 procesos
tendría 4 copias de las mismas muestras: el tiempo bajaría pero el error no mejoraría, porque en
realidad habría N/4 muestras distintas. Es el error clásico de Monte Carlo en paralelo.

**Limitación, dicha con honestidad:** semillas distintas hacen que cada proceso arranque en otro
punto de la misma secuencia de 2⁴⁸ números. Como la secuencia es enorme frente a lo que se consume,
es muy improbable que dos tramos se solapen, pero **no está garantizado**. La solución rigurosa es
un generador con secuencias independientes por proceso (lo que hace `main` con `jump()`).

**Cómo sé que funciona bien en la práctica:** el error de las ejecuciones paralelas sigue la recta
teórica σ/√N. En una prueba con 40 ejecuciones de 8 procesos y N = 10⁶, el cociente entre el error
medido y el teórico fue 1,01 para π y 0,84 para e. Si los procesos repitieran números, el error
sería claramente mayor que el teórico. El gráfico `error.png` muestra lo mismo con todos los datos.

### 3.4 `long long` para los contadores

Un `int` llega a 2 147 483 647 (≈ 2,1 × 10⁹). Para e con N = 10⁹ el contador de números generados
ronda 2,7 × 10⁹: **ya desborda**. `long long` tiene al menos 64 bits (hasta ≈ 9 × 10¹⁸). Su tipo
MPI correspondiente es `MPI_LONG_LONG`.

(En `main` se usa `uint64_t`, que fija el tamaño en exactamente 64 bits. `long long` garantiza "al
menos 64", que para este uso es equivalente y es más conocido.)

### 3.5 `x * x + y * y <= 1.0` sin raíz

La condición "distancia al origen ≤ 1" es √(x² + y²) ≤ 1. Como los dos lados son no negativos,
elevar al cuadrado no cambia la desigualdad: x² + y² ≤ 1. Se ahorra una raíz por muestra.

Dato para tener a mano (medido en `main`): con optimización activada, quitar la raíz y el `pow` no
cambió el tiempo, porque el costo dominante es generar los números aleatorios. Se escribe así igual
porque es más simple y no cuesta nada.

### 3.6 Estructura MPI

| Decisión | Justificación |
|---|---|
| El proceso 0 lee los argumentos y hace `MPI_Bcast` | Un solo punto de lectura y validación; todos trabajan con los mismos parámetros. El estándar MPI no garantiza que todos los procesos reciban `argv` |
| Los tres datos van en un arreglo | Una sola comunicación en lugar de tres |
| `MPI_Abort` si los argumentos son inválidos | Termina **todos** los procesos; si solo saliera el 0, los demás quedarían esperando el `MPI_Bcast` |
| `n_local = n / procesos`, más 1 si `rank < n % procesos` | Se hacen exactamente N muestras y la diferencia entre procesos es como mucho 1. Ejemplo: N = 10, P = 3 → 4, 3, 3 |
| `MPI_Barrier` antes de `MPI_Wtime` | Los procesos no arrancan en el mismo instante; la barrera los sincroniza para medir solo el cómputo |
| `MPI_Reduce` con `MPI_SUM` | El patrón es "P números → una suma": es exactamente una reducción. Internamente puede organizarse en árbol (log P pasos) y es una sola línea. Con `MPI_Send`/`MPI_Recv` el proceso 0 recibiría P − 1 mensajes uno por uno |
| No se usa comunicación no bloqueante | Sirve para seguir calculando mientras viaja un mensaje; acá el cómputo ya terminó cuando se comunica |
| Se reducen contadores, no estimaciones | La suma de enteros es exacta; promediar estimaciones exigiría ponderar por `n_local` |
| El tiempo lo toma el proceso 0 después de `MPI_Reduce` | La reducción termina cuando llegaron todos los aportes: el tiempo incluye al proceso más lento |

### 3.7 Tiempo en la versión serial: `clock_gettime(CLOCK_MONOTONIC)`

Mide tiempo real de reloj con resolución de nanosegundos, igual que `MPI_Wtime` en la paralela.
`clock()` mide tiempo de CPU, que no es lo mismo; `time()` solo tiene resolución de 1 segundo.

### 3.8 `-O2 -Wall -Wextra`

`-O2` es el nivel de optimización habitual y seguro. `-Wall -Wextra` activa las advertencias; el
código compila sin ninguna. Se usan las mismas opciones en el serial y en el paralelo, para que la
comparación sea justa.

### 3.9 Decisiones del benchmark

- **5 repeticiones y mediana:** el sistema operativo puede demorar una ejecución, nunca
  acelerarla. La mediana ignora ese valor atípico; el promedio no. Impar, para que la mediana sea una medición real.
- **Semillas `REP × 100000` (serial) y `REP × 100000 + P × 1000` (MPI):** cada proceso suma su
  número a la semilla. Si las ejecuciones usaran semillas 1, 2, 3…, el proceso 1 de la ejecución 1
  repetiría la semilla del proceso 0 de la ejecución 2. Dejando huecos de 1000 entre un P y el
  siguiente, ninguna ejecución repite semillas de otra (vale mientras P sea menor que 100).
  La primera versión usaba huecos de 100, que alcanzaban para P hasta 8 pero producían 20
  semillas repetidas con P hasta 24; se corrigió al conocer los datos del servidor.
- **`--oversubscribe`:** Open MPI cuenta núcleos físicos y se niega a lanzar 8 procesos en una PC
  de 4 núcleos. Esta opción lo permite.
- **Speedup contra el programa serial**, no contra MPI con 1 proceso: es la comparación honesta.

---

## 4. El código, bloque por bloque

(Los conceptos generales de C y de cada función MPI están explicados en el apunte 02; valen igual acá.)

### `montecarlo.h`

- **Guardas `#ifndef MONTECARLO_H … #endif`:** evitan incluir el archivo dos veces.
- **`PI_REAL`, `E_REAL`:** los valores reales, para calcular el error.
- **`contar_aciertos_pi(n)`:** `for` de n vueltas; en cada una genera x e y con `drand48()` y, si
  x² + y² ≤ 1, suma 1 a `aciertos`. Devuelve el contador.
- **`contar_sumandos_e(n)`:** `for` de n ensayos. En cada uno `suma` arranca en 0 y un `while`
  agrega números al azar hasta pasar de 1; cada número generado incrementa `sumandos`, que **no**
  se reinicia entre ensayos. Devuelve el total.
- **`calcular_estimacion`:** π = 4 × cuenta / N; e = cuenta / N. El `(double)` evita la división entera.
- **`leer_argumentos`:** verifica que haya al menos 2 argumentos, compara el primero con `"pi"` y
  `"e"` usando `strcmp` (devuelve 0 si son iguales), convierte N con `atoll` (texto → `long long`)
  y exige N > 0. La semilla es opcional: si no se pasa, usa 12345.
- **`imprimir_resultado`:** una línea CSV. `fabs` es el valor absoluto para `double`.

### `montecarlo_serial.c`

Lee argumentos → `srand48(semilla)` → toma el tiempo → ejecuta el experimento → toma el tiempo →
calcula la estimación → imprime. Solo se cronometra el experimento.

### `montecarlo_mpi.c`

```
MPI_Init                         enciende MPI
MPI_Comm_rank / MPI_Comm_size    quién soy (0..P-1) y cuántos somos (P)
proceso 0: leer_argumentos       (si falla, MPI_Abort)
MPI_Bcast                        el 0 envía, el resto recibe
n_local                          mi parte de las N muestras
srand48(semilla + rank)          mis propios números aleatorios
MPI_Barrier                      largada
MPI_Wtime                        inicio
experimento con n_local          sin comunicación
MPI_Reduce                       suma de los contadores en el proceso 0
MPI_Wtime                        fin
proceso 0: calcula e imprime
MPI_Finalize                     apaga MPI
```

Con P = 1, `montecarlo_mpi` da **exactamente** el mismo resultado que `montecarlo_serial` con la
misma semilla (misma semilla, mismo código). Lo comprobé.

### `benchmark.sh`

- `${1:-pc}`: el primer argumento, o `pc` si no se pasó.
- `${TAMANIOS:-"…"}`: usa la variable de entorno si existe, o el valor por defecto.
- `make || exit 1`: compila; si falla, no sigue.
- `lscpu > resultados/sistema_…txt`: guarda la descripción del procesador.
- Tres bucles anidados (constante, N, repetición) y uno más para P.
- `echo "serial,$(./montecarlo_serial …)" >> $SALIDA`: ejecuta el programa, le antepone la columna
  `programa` y agrega la línea al CSV.

### `graficos.py`

- `cargar_datos`: une todos los `tiempos_<sistema>.csv` y agrega la columna `sistema`.
- `calcular_resumen`: agrupa por configuración y toma la **mediana** del tiempo; une la tabla MPI
  con la serial y calcula `speedup = t_serial / t_mediana` y `eficiencia = speedup / P`.
- `grafico_error`: para cada N calcula la raíz del error cuadrático medio de todas las ejecuciones
  y ajusta la pendiente con `np.polyfit` sobre los logaritmos.
- El resto dibuja.

---

## 5. Cómo correr el benchmark y hacer los gráficos

### En la PC (terminal de Ubuntu / WSL, en la carpeta del proyecto)

```bash
git switch version-simple
./benchmark.sh pc
```

Tarda alrededor de 20 a 25 minutos con los valores por defecto (estimación a partir de una prueba
informal: unos 19 ns por muestra para π y 46 ns para e). **Dejar la notebook enchufada y sin usar
mientras corre**; en la corrida de `main` la máquina cambió de velocidad a mitad de camino y hubo
que repetir mediciones.

Prueba rápida antes de la corrida larga (1 minuto):

```bash
TAMANIOS="100000 1000000" REPETICIONES=3 ./benchmark.sh prueba
rm resultados/*prueba*          # borrar la prueba para que no entre en los gráficos
```

### En el servidor

El servidor (`cluster_boogie`, AMD EPYC 7B12) se usa desde la terminal de JupyterLab, con 12 o 24
núcleos asignados y `mpirun` directo (sin SLURM). Conviene pedir **24 núcleos**.

```bash
git clone <url del repositorio>  &&  cd <carpeta>
git switch version-simple

# 1) Comprobar que hay compilador y MPI, y cuántos núcleos reales hay (1 minuto)
OPCIONES_MPI="--bind-to none --oversubscribe" ./verificar_sistema.sh 24

# 2) El benchmark
PROCESOS="1 2 4 8 12 16 24" OPCIONES_MPI="--bind-to none --oversubscribe" ./benchmark.sh cluster_boogie
```

Qué mirar en el paso 1:

- **Si dice "NO ESTÁ INSTALADO" para `mpicc` o `mpirun`:** la imagen "Python Científico" puede no
  traer MPI. Sin permisos de administrador, la salida habitual es
  `conda install -c conda-forge openmpi` (si hay conda). Si tampoco se puede, hay que pedirlo a la cátedra.
- **Si el usuario es `root`:** Open MPI se niega a correr; agregar `--allow-run-as-root` a `OPCIONES_MPI`.
- **La prueba de escalado:** si con 24 procesos tarda casi lo mismo que con 12, los "24 núcleos"
  son 12 núcleos físicos con dos hilos cada uno (es lo habitual en máquinas virtuales con este
  procesador). No es un error: es un dato para explicar dónde se dobla la curva de speedup.

Por qué esas opciones: `--bind-to none` porque dentro de un contenedor Open MPI no siempre puede
fijar cada proceso a un núcleo y puede fallar o amontonarlos; `--oversubscribe` porque puede
contar mal cuántos núcleos tiene disponibles.

No pedir más procesos que núcleos asignados: el contenedor limita la CPU y el speedup se aplana.

Después, descargar desde JupyterLab (clic derecho → Download) los archivos
`resultados/tiempos_cluster_boogie.csv` y `resultados/sistema_cluster_boogie.txt` y copiarlos a la
carpeta `resultados/` de la PC.

Tiempo estimado en el servidor: del orden de 30 a 40 minutos (depende de la velocidad de cada
núcleo, que no conozco hasta medir).

### Experimento adicional (opcional): hasta 96 procesos

Hacerlo **después** de la corrida de 24, en otra sesión con el perfil de 96 núcleos (384 GB). Va
con otro nombre de sistema, así queda en archivos aparte y no pisa nada.

```bash
# 1) Comprobación previa con 96
OPCIONES_MPI="--bind-to none --oversubscribe" ./verificar_sistema.sh 96

# 2) Barrido acotado: solo N = 10^9, 3 repeticiones (del orden de 10 a 15 minutos)
TAMANIOS="1000000000" REPETICIONES=3 PROCESOS="1 2 4 8 16 24 32 48 64 96" \
OPCIONES_MPI="--bind-to none --oversubscribe" ./benchmark.sh cluster_boogie_96
```

Si se quiere agregar N = 10¹⁰, usar `TAMANIOS="1000000000 10000000000"`; con esta versión eso lleva
del orden de dos horas (el generador `drand48` es más lento que el de `main`), así que solo vale la
pena si sobra tiempo. Los tiempos son estimaciones con la velocidad de la notebook.

**Por qué alcanza con N = 10⁹ acá:** con 96 procesos cada uno hace unos 10⁷ muestras, que con esta
versión son unas décimas de segundo. Es poco pero medible. Con N más chicos el cómputo por proceso
dura milisegundos y el gráfico solo mostraría ruido; por eso no se incluyen.

**Qué archivos descargar:** `resultados/tiempos_cluster_boogie_96.csv` y
`resultados/sistema_cluster_boogie_96.txt`.

**Qué cambia en los gráficos.** `graficos.py` lo trata como un sistema más:

- Genera `speedup_cluster_boogie_96.png` y `tiempo_cluster_boogie_96.png`.
- Como P pasa de 32, esos gráficos usan **escala logarítmica en los dos ejes**. En escala lineal
  los puntos 1, 2, 4 y 8 quedarían amontonados en una esquina. En log-log el speedup ideal S = P
  sigue siendo una recta diagonal, y cada duplicación de P ocupa el mismo ancho.
- En `eficiencia.png` aparece como una tercera línea.

**Cómo leer la curva de speedup hasta 96.** Mirar dónde se separa de la diagonal:

| Lo que se ve | Explicación más probable | Cómo confirmarlo |
|---|---|---|
| Sigue la diagonal hasta cierto P y ahí se dobla | Se acabaron los núcleos físicos; a partir de ahí son hilos lógicos (dos hilos comparten un núcleo) | En `sistema_cluster_boogie_96.txt`: "Thread(s) per core: 2". El quiebre debería estar cerca de la mitad de las CPU asignadas |
| Se dobla de forma gradual desde antes | Menor frecuencia del procesador con muchos núcleos activos, o carga de otros usuarios | Comparar con la corrida de 24: si a P = 24 da distinto, hubo ruido |
| Se aplana del todo en un valor | El contenedor limita la CPU a ese valor | La línea "cpu.max" del archivo de sistema |
| Sube y baja sin patrón | Ruido: el servidor es compartido | Mirar la dispersión entre las 3 repeticiones; repetir en otro momento |

Dato de contexto: el procesador tiene 64 núcleos físicos por zócalo. 96 "cores" asignados no entran
en un zócalo como núcleos físicos, así que son hilos lógicos o abarcan dos zócalos. El archivo de
sistema (líneas "Socket(s)", "Core(s) per socket", "Thread(s) per core") dice cuál de los dos.

**Qué decir.** "Además del barrido hasta 24 procesos, hice una prueba hasta 96 para ver dónde deja
de escalar. El speedup sigue cerca del ideal hasta P = [completar] y después se dobla, porque
[completar con la causa confirmada]. Como el programa no tiene parte serial ni comunicación
apreciable, el límite lo pone el hardware."

**Qué NO decir** sin haberlo confirmado: que el quiebre es por la ley de Amdahl (el programa casi no
tiene fracción serial) o por la comunicación (es una sola reducción).

**Cuándo dejarlo afuera.** Si la curva sale errática o no se llega a entender por qué se dobla, no
incluirla: la corrida de 24 ya cumple la consigna. Borrar los dos archivos `*cluster_boogie_96*` de
`resultados/` y volver a ejecutar `graficos.py`.

### Los gráficos

En PowerShell, en la carpeta del proyecto (el entorno de Python ya está creado):

```powershell
.\.venv\Scripts\python.exe graficos.py
```

o en Ubuntu, la primera vez:

```bash
python3 -m venv .venv-linux && source .venv-linux/bin/activate
pip install -r requirements.txt
python graficos.py
```

Imprime la tabla resumen y la pendiente del error, y deja todo en `resultados/`. Usa todos los
sistemas que encuentre: con `pc` y `servidor` genera un gráfico de speedup por cada uno y el de
eficiencia con las dos líneas.

### Verificaciones después de medir

1. **Coherencia:** en `resultados/resumen.csv`, el speedup con P = 1 debería estar cerca de 1
   (entre 0,9 y 1,1) para los N grandes. Si da 0,5 o 2, la máquina cambió de estado durante la
   corrida y hay que repetirla.
2. **Pendiente del error:** cerca de −0,5.
3. Subir `resultados/` al repositorio (la consigna pide tener resultados y gráficos listos).

---

## 6. Qué esperar en cada gráfico

Las explicaciones detalladas de por qué cada curva tiene su forma están en el apunte 03 y valen
para esta versión; lo que cambia son los números.

| Gráfico | Qué esperar | Qué decir |
|---|---|---|
| `intuicion.png` | Puntos dentro/fuera del arco; barras que coinciden con los puntos teóricos | Así funciona cada experimento |
| `convergencia.png` | Un embudo que se cierra sobre el valor real | Con más muestras, las estimaciones se concentran; se cierra lento |
| `error.png` | Puntos sobre dos rectas paralelas de pendiente −1/2 | log(error) = log σ − ½ log N; e queda más abajo porque su σ es menor (0,875 contra 1,642) |
| `tiempo_*.png` | Líneas que bajan con P, separadas por un factor 10 entre N | El tiempo es proporcional a N y baja al repartir |
| `speedup_*.png` | Cerca del ideal hasta los núcleos físicos; se dobla después | En la notebook: límite de potencia/temperatura y, pasados los 4 núcleos, hilos lógicos. Con N chico las curvas son ruidosas (se miden milisegundos) |
| `eficiencia.png` | Empieza cerca de 1 y baja; el servidor debería mantenerse más alto | Diferencias de hardware (apunte 03, sección 8) |

Diferencias esperables respecto de `main`:

- El escalado debería ser parecido (en `main` con 4 procesos y N = 10⁹: speedup 2,72 para π).
- El tiempo por muestra es distinto porque el generador es otro.
- No hay gráfico del costo de arranque de MPI. Si preguntan por qué con N chico el speedup es
  errático: el cómputo dura milisegundos, el ruido de medición pesa mucho, y lanzar MPI cuesta unos
  0,35 s fijos (medido en `main`) que no entran en el tiempo cronometrado.

**Para las conclusiones**, una vez medidos los números, la estructura es la del apunte 03, sección
10, quitando lo que es propio de `main` (la comparación V0/V1/V2 y la versión ingenua).

---

## 7. Guion de introducción para esta versión

> "El proyecto estima π y e con el método de Monte Carlo: en lugar de calcularlas con una fórmula,
> repito muchísimas veces un experimento aleatorio y de la frecuencia de los resultados obtengo la
> constante. Para π genero puntos al azar en un cuadrado y cuento cuántos caen dentro de un cuarto
> de círculo. Para e sumo números al azar entre 0 y 1 hasta pasar de 1 y cuento cuántos hicieron
> falta; el promedio de esa cantidad es e.
>
> La limitación principal del método es que converge lento: el error baja como uno sobre raíz de
> N, así que un decimal más cuesta cien veces más muestras. Eso obliga a usar N muy grandes. La
> ventaja es que cada muestra es independiente de las demás, y por eso es un problema ideal para
> paralelizar: reparto las muestras entre los procesos, cada uno cuenta por su lado sin
> comunicarse, y al final sumo los contadores con una sola operación colectiva de MPI.
>
> Dos cuidados que tuve al implementar: contadores de 64 bits, porque con N de mil millones un
> entero común se desborda; y una semilla distinta por proceso, porque si todos generaran los
> mismos números tendría menos muestras reales de las que creo. Medí el tiempo con la mediana de
> cinco ejecuciones, variando N y la cantidad de procesos, en mi PC y en el servidor, y verifiqué
> que el error medido sigue la ley teórica."

---

## 8. Limitaciones y mejoras futuras

| Limitación de esta versión | Mejora | Estado |
|---|---|---|
| Semilla + rango no garantiza tramos disjuntos | Generador con secuencias independientes por proceso (xoshiro256\*\* con `jump`, o Philox) | Hecho en `main` |
| `drand48` es un generador viejo (congruencial lineal) | Generador moderno que pasa las pruebas estadísticas actuales | Hecho en `main` |
| `atoll` no detecta texto inválido (`"abc"` da 0, que se rechaza por N > 0, pero `"100abc"` se acepta como 100) | Validar con `strtoll` | Hecho en `main` |
| Convergencia 1/√N | Cuasi-Monte Carlo (Sobol, Halton): error cerca de 1/N | Futuro |
| Un proceso por núcleo | Híbrido MPI + OpenMP | Futuro |
| Una muestra por vez | Vectorización (SIMD) o GPU | Futuro |

Si preguntan "¿qué harías distinto?", la primera fila es la respuesta más sólida: muestra que se
entiende el punto débil del diseño.

---

## 9. Preguntas probables

**¿Por qué `drand48` y no `rand`?** Sección 3.2: 48 bits garantizados, devuelve directamente un real, mismo algoritmo en todo sistema POSIX.

**¿Cómo se asegura de que los procesos no generan los mismos números?** Semilla distinta por
proceso. No es una garantía matemática de que no se solapen; lo respaldo con que el error medido
sigue la teoría. La solución rigurosa es un generador con saltos.

**¿Qué pasaría si todos usaran la misma semilla?** El tiempo bajaría igual, pero el error sería el
de N/P muestras: el speedup se vería bien y el resultado sería peor. Por eso el speedup solo no alcanza; hay que mirar también el error.

**¿Por qué `long long`?** Con N = 10⁹ el contador de e llega a 2,7 × 10⁹ y un `int` desborda en 2,1 × 10⁹.

**¿Por qué el `if` en lugar de sumar la comparación?** Es la forma más clara. El compilador con
`-O2` puede convertirlo en una suma sin salto.

**¿Qué pasa si N no es divisible por P?** Los primeros N % P procesos hacen una muestra más. N = 10, P = 3 → 4, 3, 3.

**¿Por qué `MPI_Reduce`?** Sección 3.6.

**¿Por qué el speedup no es igual a P?** Apunte 03, sección 5: en la notebook, por el límite de
potencia y temperatura del procesador y, más allá de 4 procesos, por los hilos lógicos. No por el
programa, que casi no tiene parte serial ni comunicación.

**¿El resultado es reproducible?** Sí, con la misma semilla y el mismo P da exactamente el mismo valor.

**¿Por qué el serial y el paralelo comparten el encabezado?** Para que ejecuten el mismo código de
cómputo y el speedup mida solo el efecto de repartir.

---

## 10. Cuál de las dos versiones presentar

| | `main` | `version-simple` |
|---|---|---|
| Cumple la consigna | Sí, y la excede bastante | Sí, y la excede un poco |
| Código a defender | ~650 líneas de C, con operaciones de bits en el generador | ~230 líneas de C, sin operaciones de bits |
| Preguntas difíciles que abre | `splitmix64`, `jump`, rotaciones, la progresión V0–V2 | El punto débil de semilla + rango |
| Resultados | Ya medidos en la PC | **Hay que medirlos** |
| Fortaleza | Rigor: independencia garantizada, verificaciones, más análisis | Cada línea se explica en una frase |

Criterio práctico: presentar la versión de la que se pueda explicar **cada línea** sin dudar. Si se
presenta la simple, lo aprendido en `main` (por qué `jump` es mejor, qué pasó al medir V0/V1/V2,
el costo de arranque) sirve como respuesta a "¿qué mejorarías?" y muestra que se investigó más allá.

Una aclaración que conviene tener presente: en la defensa van a preguntar por qué se tomó cada
decisión y cómo se escribió el código. Lo que sostiene esas respuestas es haber entendido el
trabajo, sea cual sea la versión; por eso estos apuntes están escritos para entender y no para
memorizar. Si la cátedra tiene reglas sobre el uso de herramientas de IA, hay que respetarlas y,
si preguntan, decir con franqueza qué se usó.
