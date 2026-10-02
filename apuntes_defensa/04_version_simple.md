# 04 — Cómo correr las pruebas y relación con la rama `main`

> **Apunte de estudio.** Describe la rama `version-simple`, que es la versión principal del proyecto.

Contenido:

1. Cómo correr el benchmark y hacer los gráficos
2. Qué pide la consigna y dónde está cada cosa
3. Relación con la rama `main`

Lo demás está en los otros apuntes: la teoría y el guion de apertura en el 01, el código y la
justificación de cada decisión en el 02, cómo leer cada gráfico y las conclusiones en el 03, y las
mejoras candidatas en el 05.

---

## 1. Cómo correr el benchmark y hacer los gráficos

### 1.1 En la PC (terminal de Ubuntu / WSL, en la carpeta del proyecto)

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

### 1.2 En el clúster

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

### 1.3 Experimento adicional (opcional): hasta 96 procesos

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

### 1.4 Los gráficos

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
sistemas que encuentre: con `pc` y `cluster_boogie` genera un gráfico de speedup por cada uno y el de
eficiencia con las dos líneas.

### 1.5 Verificaciones después de medir

1. **Coherencia:** en `resultados/resumen.csv`, el speedup con P = 1 debería estar cerca de 1
   (entre 0,9 y 1,1) para los N grandes. Si da 0,5 o 2, la máquina cambió de estado durante la
   corrida y hay que repetirla.
2. **Pendiente del error:** cerca de −0,5.
3. Subir `resultados/` al repositorio (la consigna pide tener resultados y gráficos listos).

---

## 2. Qué pide la consigna y dónde está cada cosa

| Consigna | Dónde |
|---|---|
| Investigar el problema, objetivos, limitaciones y estrategias | README: "El problema", "Convergencia", "Limitaciones". Apunte 01 |
| Implementación paralela, de la manera más adecuada de paralelizar | `montecarlo_mpi.c`. README: "Cómo se paralelizó". Apunte 02, sección 5 |
| Seleccionar o generar los datos para las pruebas | Los datos son los números aleatorios; se generan con `drand48` y semillas controladas |
| Correr en diferentes sistemas | `./benchmark.sh pc` y `./benchmark.sh cluster_boogie` (sección 1) |
| Speedup con la mediana de múltiples ejecuciones | `graficos.py`, función `calcular_resumen` |
| Múltiples simulaciones cambiando las variables | Se varían N (5 valores), P (4 valores) y la constante (π y e) |
| Convergencia y error al aumentar las simulaciones | `convergencia.png` y `error.png` |
| Concluir sobre los resultados | Se escribe después de medir (plantilla en el apunte 03, sección 8) |
| Mejoras para futuros casos | README: "Limitaciones y mejoras futuras". Apunte 03, sección 9, y apunte 05 |
| Bibliografía | README: "Bibliografía" |

Sobre la bibliografía: están listadas fuentes reales y pertinentes. Conviene al menos hojear las
que se citan (el capítulo de MPI de Pacheco y la página de manual de `drand48`, que se abre con
`man drand48`), porque pueden preguntar de dónde salió algo.

---

## 3. Relación con la rama `main`

El repositorio tiene dos ramas. `version-simple` es la versión principal; `main` es una versión
más extensa que se hizo antes, con más optimizaciones y más análisis. Para cambiar de rama:
`git switch main` o `git switch version-simple`.

| | `version-simple` | `main` |
|---|---|---|
| Programas | 2 (`montecarlo_serial`, `montecarlo_mpi`) | 5 (`serial_v0/v1/v2`, `mpi_v0/v2`) |
| Código C | unas 230 líneas, 3 archivos | unas 650 líneas, 7 archivos |
| Generador | `drand48()` de la biblioteca estándar | xoshiro256\*\* propio, con `splitmix64` y `jump()` |
| Números por proceso | Semilla + número de proceso (sin garantía formal) | Tramos disjuntos garantizados (`jump`) |
| Tipos | `long long`, `MPI_LONG_LONG` | `uint64_t`, `MPI_UINT64_T` |
| Progresión de optimizaciones | Una sola versión, ya sin `sqrt` | V0 → V1 → V2, medida |
| Lectura de argumentos | `atoll` y chequeo de N > 0 | `strtoull` con validación completa |
| Opciones de compilación | `-O2 -Wall -Wextra` | `-std=c11 -O3 -march=native -Wpedantic …` |
| Benchmark | Un bucle simple, 4 variables | Más opciones, límites por programa, tiempo total del lanzamiento |
| Repeticiones | 5 | 7 |
| Análisis | 1 script (`graficos.py`) | 5 scripts de Python, avisos de coherencia |
| Nombres | Español | Inglés |

**Lo que comparten**, porque es el corazón del trabajo: los dos experimentos, el reparto `N / P`
más el resto, `MPI_Bcast` + `MPI_Reduce`, `MPI_Barrier` + `MPI_Wtime`, la mediana, y las fórmulas
de speedup, eficiencia y error.

**Por qué la versión principal es la simple:** cada línea se puede explicar en una frase y no tiene
operaciones de bits. Lo que `main` tiene de más es material para responder "¿qué mejorarías?":

| Lo que tiene `main` | Qué aporta | Qué se aprendió de eso |
|---|---|---|
| xoshiro256\*\* con `jump()` | Secuencias por proceso separadas por construcción, y un generador más rápido | Es la solución rigurosa al punto débil de `semilla + rank` |
| Progresión V0 → V1 → V2 medida | Mide el efecto de cada optimización | Quitar la raíz cuadrada no cambió el tiempo (el compilador ya optimizaba y el costo dominante es el generador); cambiar el generador ganó unas 3 veces |
| Versión MPI ingenua (`mpi_v0`) | Comparar el escalado de un código lento y uno rápido | Escalan parecido, pero 8 procesos de la versión lenta apenas le ganan a 1 de la rápida: primero se optimiza el serial |
| Tiempo total del lanzamiento | Mide el costo de arrancar MPI | En la notebook, unos 0,3 a 0,4 s fijos |
| Avisos de coherencia | Detecta mediciones sospechosas | Hubo que repetir un bloque de mediciones porque la notebook cambió de velocidad a mitad de la corrida |

Los apuntes de la rama `main` describen su propio código; los de esta rama describen la versión simple.
