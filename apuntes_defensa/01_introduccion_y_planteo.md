# 01 — Introducción y planteo (guion de apertura del examen)

> **Apunte de estudio.** Guía para preparar la defensa oral. Describe la rama `version-simple`.
> Orden sugerido de estudio: este archivo → `02_codigo_linea_por_linea.md` → `03_graficos_speedup_y_conclusiones.md`.

Cada tema tiene dos capas:

- **En simple:** la idea con una analogía cotidiana, para entenderla.
- **Para el profesor:** la justificación técnica exacta, para decirla.

Contenido:

1. Guion de apertura (para decir en 2 a 3 minutos)
2. Qué es el problema
3. Ejemplos a mano, paso a paso
4. Por qué lo encaré de esta forma
5. Limitaciones, y cómo cada una influyó en la implementación
6. Fundamento matemático completo (demostraciones)
7. Preguntas probables y respuestas

---

## 1. Guion de apertura

Para decir casi textual al empezar. Tres bloques: qué, por qué así, limitaciones.

> **Qué.** "El proyecto estima dos constantes matemáticas, π y e, con el método de Monte Carlo.
> Las constantes son valores fijos, pero en lugar de calcularlas con una fórmula las estimo con
> un experimento aleatorio repetido muchísimas veces: cuento con qué frecuencia ocurre algo y de
> esa frecuencia despejo la constante. Para π tiro puntos al azar en un cuadrado y cuento cuántos
> caen dentro de un cuarto de círculo. Para e sumo números al azar entre 0 y 1 hasta pasar de 1 y
> cuento cuántos hicieron falta; el promedio de esa cantidad es e."
>
> **Por qué así.** "Elegí Monte Carlo porque cada muestra es independiente de las demás: ninguna
> necesita el resultado de otra. Eso lo hace un problema *embarazosamente paralelo*: reparto las
> muestras entre procesos MPI, cada uno cuenta por su lado sin comunicarse, y al final sumo los
> contadores con una sola operación colectiva. Además el valor exacto se conoce, así que puedo
> medir el error real y compararlo con la teoría."
>
> **Limitaciones.** "El método converge lento: el error baja como uno sobre raíz de N, así que un
> decimal más cuesta cien veces más muestras. Por eso necesito N muy grandes, y eso trae tres
> cuidados que guiaron la implementación: contadores de 64 bits, porque con N de mil millones un
> entero común se desborda; un generador de números aleatorios de 48 bits, `drand48`, en lugar de
> `rand()`; y una semilla distinta en cada proceso, porque si todos generaran los mismos números
> tendría menos muestras reales de las que creo. Escribí una versión serial, que es la referencia,
> y una versión MPI que comparte con ella exactamente el mismo código de cómputo. Medí tiempo,
> speedup y eficiencia con la mediana de cinco ejecuciones, variando N y la cantidad de procesos,
> en mi PC y en el clúster, y verifiqué que el error medido sigue la ley teórica."

Una frase sobre un error común de vocabulario: las constantes son **deterministas** (valores
fijos); lo que es **estocástico** (aleatorio) es el *método de estimación*. No decir "estimar de
forma determinista".

---

## 2. Qué es el problema

### 2.1 Monte Carlo en general

**En simple.** Quiero saber qué fracción de una pared está pintada de azul, pero no tengo regla.
Tiro mil dardos con los ojos vendados y cuento cuántos pegan en la parte azul. Si pegaron 300, la
parte azul ocupa más o menos el 30 %. Con más dardos, la estimación mejora.

**Para el profesor.** Monte Carlo escribe la cantidad buscada como el valor esperado de una
variable aleatoria, θ = E[X], y la estima con el promedio de N muestras independientes. La ley de
los grandes números garantiza que el promedio converge a θ; el teorema central del límite dice que
el error típico es σ/√N, donde σ es el desvío estándar de una muestra.

### 2.2 El experimento de π

**En simple.** Dibujo un cuadrado de lado 1 y, adentro, un cuarto de círculo de radio 1 con centro
en una esquina. Llueve parejo sobre el cuadrado. La fracción de gotas que cae dentro del cuarto de
círculo es igual a la fracción de área que ocupa: π/4 ≈ 0,785. Si cuento gotas, obtengo π/4;
multiplico por 4 y tengo π.

**Para el profesor.**

- Punto (x, y) con x e y uniformes e independientes en [0, 1].
- Cae dentro si x² + y² ≤ 1 (distancia al origen menor o igual que el radio).
- Probabilidad de caer dentro = área del cuarto de círculo / área del cuadrado = (π/4) / 1.
- Estimador: **π ≈ 4 × aciertos / N**.

### 2.3 El experimento de e

**En simple.** Un juego: saco números al azar entre 0 y 1 y los voy sumando. Paro cuando la suma
pasa de 1 y anoto cuántos números usé. A veces alcanzan 2, a veces hacen falta 3 o 4. Si juego
muchísimas veces y promedio esas cantidades, el promedio da 2,718… que es e.

**Para el profesor.**

- Ensayo: N = menor n tal que U₁ + U₂ + … + Uₙ > 1, con Uᵢ uniformes en [0, 1].
- Resultado teórico: E[N] = e (demostración en la sección 6).
- Estimador: **e ≈ total de números generados / cantidad de ensayos**.

En el código, "N" (el argumento del programa) es la cantidad de **puntos** para π y la cantidad de
**ensayos** para e.

---

## 3. Ejemplos a mano

### 3.1 π con 5 puntos

| Punto | x | y | x² + y² | ¿≤ 1? | aciertos acumulados |
|---|---|---|---|---|---|
| 1 | 0,2 | 0,3 | 0,04 + 0,09 = 0,13 | sí | 1 |
| 2 | 0,9 | 0,8 | 0,81 + 0,64 = 1,45 | no | 1 |
| 3 | 0,5 | 0,5 | 0,25 + 0,25 = 0,50 | sí | 2 |
| 4 | 0,7 | 0,6 | 0,49 + 0,36 = 0,85 | sí | 3 |
| 5 | 0,95 | 0,4 | 0,9025 + 0,16 = 1,0625 | no | 3 |

π ≈ 4 × 3 / 5 = **2,4**. Muy lejos de 3,14: con 5 puntos el error esperado es enorme
(1,64/√5 ≈ 0,73). Con un millón de puntos el error típico baja a 0,0016.

En el código esto es exactamente `if (x * x + y * y <= 1.0) aciertos++;` dentro de un `for` de
N vueltas (función `contar_aciertos_pi` de `montecarlo.h`), y al final `4.0 * aciertos / N`.

### 3.2 e con 4 ensayos

Hay dos contadores: `suma` (la suma parcial, que vuelve a 0 en cada ensayo) y `sumandos` (cuántos
números se generaron en total, que nunca se reinicia).

| Ensayo | Números que salen | Suma parcial paso a paso | Números usados | `sumandos` |
|---|---|---|---|---|
| 1 | 0,4 · 0,7 | 0,4 → 1,1 (pasó de 1, paro) | 2 | 2 |
| 2 | 0,2 · 0,3 · 0,6 | 0,2 → 0,5 → 1,1 (paro) | 3 | 5 |
| 3 | 0,9 · 0,5 | 0,9 → 1,4 (paro) | 2 | 7 |
| 4 | 0,1 · 0,3 · 0,2 · 0,5 | 0,1 → 0,4 → 0,6 → 1,1 (paro) | 4 | 11 |

e ≈ 11 / 4 = **2,75**. El valor real es 2,718.

En el código (función `contar_sumandos_e` de `montecarlo.h`):

```c
for (long long i = 0; i < n; i++) {    // un ensayo por vuelta
    double suma = 0.0;                 // la suma arranca en 0 en cada ensayo
    while (suma <= 1.0) {              // mientras no pase de 1...
        suma += drand48();             // ...sumo otro número al azar
        sumandos++;                    // ...y cuento que generé uno más
    }
}
// e ≈ sumandos / n
```

Detalle para no confundirse: un ensayo **nunca** termina con un solo número, porque un número
entre 0 y 1 no puede superar 1 por sí solo. El mínimo es 2.

---

## 4. Por qué lo encaré de esta forma

### 4.1 Ventajas de Monte Carlo

- **Simple:** el núcleo son cinco líneas.
- **El error no depende de la dimensión del problema.** Una regla de integración sobre una grilla
  necesita muchísimos más puntos al aumentar la dimensión; Monte Carlo mantiene 1/√N siempre. Por
  eso es el método de uso real en integrales de muchas dimensiones (finanzas, física de
  partículas, renderizado).
- **El error se puede estimar** con un intervalo de confianza.
- **Paraleliza casi perfecto.**

**Respuesta honesta si preguntan "¿es la mejor forma de calcular π?":** no. Una serie da 15
decimales en microsegundos. π y e se eligen como problema de estudio porque el valor exacto se
conoce (el error se puede medir) y porque el algoritmo es ideal para estudiar paralelismo.

### 4.2 Por qué es "embarazosamente paralelo"

**En simple.** Una encuesta nacional. Si tengo 4 encuestadores, cada uno entrevista a un cuarto de
la gente en su zona, sin hablar con los otros, y al final sumo las planillas. Nadie espera a
nadie. La única coordinación es la suma final.

**Para el profesor.** Las muestras son independientes e idénticamente distribuidas y el estimador
depende solo de una **suma** (asociativa y conmutativa). No hay dependencia de datos entre
iteraciones ni memoria compartida. La comunicación se reduce a difundir los parámetros al inicio
(`MPI_Bcast`) y reducir P contadores al final (`MPI_Reduce`): costo O(log P), frente a O(N/P) de
cómputo por proceso.

La **única condición** es que cada proceso use números aleatorios distintos e independientes de
los demás. Si dos encuestadores entrevistan a las mismas personas, tengo menos información de la
que creo. En esta versión se resuelve dándole a cada proceso una semilla distinta; cómo funciona y
cuál es su limitación está en el apunte 02, sección 5.2, paso 3.

### 4.3 Por qué el cuarto de círculo

- La proporción es la misma que con el círculo completo en un cuadrado de lado 2 (π/4), por simetría.
- Usa directamente números en [0, 1], que es lo que entrega el generador: no hay que transformar a [−1, 1].
- La condición es la más barata posible: dos multiplicaciones, una suma, una comparación.

### 4.4 Por qué la suma de uniformes para e

- Usa el mismo ingrediente que π (uniformes en [0, 1]), así que las dos estimaciones comparten
  generador y estructura de código, y los tiempos son comparables.
- La demostración es corta y se puede hacer en el pizarrón (sección 6).
- Tiene menor varianza que el estimador de π (σ = 0,875 contra 1,642).
- Alternativas descartadas: estimar 1/e con permutaciones sin puntos fijos (hay que generar y
  barajar un arreglo en cada ensayo: más memoria y más costo por muestra) o con el máximo de
  uniformes (demostración menos directa).

---

## 5. Limitaciones, y cómo cada una influyó en la implementación

| Limitación | Consecuencia práctica | Qué se hizo |
|---|---|---|
| Convergencia lenta, O(1/√N) | Hacen falta N de 10⁸ a 10⁹ (o más) para pocos decimales | Motiva todo: un núcleo de cómputo barato y la paralelización |
| Desborde de enteros | `int` llega a 2 147 483 647 (≈ 2,1 × 10⁹). Con N = 10⁹ el contador de e ya llega a 2,7 × 10⁹ y daría la vuelta | Contadores `long long` (hasta ≈ 9,2 × 10¹⁸) |
| Operaciones caras por muestra | Una raíz cuadrada por punto si se compara la distancia | Se compara x² + y² con 1, que es equivalente |
| Calidad y portabilidad de `rand()` | El estándar solo garantiza 15 bits; algoritmo y calidad dependen del sistema | `drand48`: 48 bits, período 2⁴⁸ ≈ 2,8 × 10¹⁴, mismo algoritmo en todo sistema POSIX |
| Independencia entre procesos | Con la misma semilla todos generarían los mismos números | Semilla distinta por proceso (`semilla + rank`). Sin garantía matemática de que los tramos no se solapen; se respalda midiendo que el error sigue la teoría |
| Tiempo total | Un solo núcleo no alcanza para N grandes | MPI: reparto de las N muestras entre P procesos |
| Costo fijo de arrancar MPI | Con N chico, lanzar los procesos cuesta más que el cálculo | No se puede evitar: se documenta a partir de qué N conviene paralelizar |

**Paralelizar no cambia la ley de convergencia.** Con P procesos hago P veces más muestras en el
mismo tiempo, pero el error solo baja √P veces. Paralelizar compra tiempo, no una convergencia mejor.

**Lo que quedó como mejora futura**, y por qué (detalle en el apunte 05): un generador con
secuencias independientes garantizadas por proceso (xoshiro256\*\* con función de salto), que
resolvería el punto débil de `semilla + rank` a cambio de bastante más código; y validar los
argumentos con `strtoll` en lugar de `atoll`.

---

## 6. Fundamento matemático completo

### 6.1 π

Cada punto es un ensayo de Bernoulli: Xᵢ = 1 si cae dentro, 0 si no, con p = P(x² + y² ≤ 1) = π/4.

$$\hat{\pi} = 4 \cdot \frac{\text{aciertos}}{N}, \qquad E[\hat{\pi}] = 4p = \pi \ \text{(insesgado)}$$

Varianza de una Bernoulli: p(1 − p). Multiplicar por 4 multiplica el desvío por 4:

$$\sigma_\pi = 4\sqrt{p(1-p)} = 4\sqrt{\tfrac{\pi}{4}\left(1-\tfrac{\pi}{4}\right)} \approx 1{,}642$$

### 6.2 e, en tres pasos

Sea Sₙ = U₁ + … + Uₙ y N = min{n : Sₙ > 1}.

**Paso 1.** Para 0 ≤ t ≤ 1: P(Sₙ ≤ t) = tⁿ/n!. Por inducción: para n = 1, P(U₁ ≤ t) = t. Si vale
para n, condicionando en el valor u del último sumando:

$$P(S_{n+1} \le t) = \int_0^t \frac{(t-u)^n}{n!}\,du = \frac{t^{n+1}}{(n+1)!}$$

Intuición geométrica: 1/n! es el volumen de la región {u₁ + … + uₙ ≤ 1} dentro del cubo unitario.
En 2D es un triángulo de área 1/2; en 3D, una pirámide de volumen 1/6.

**Paso 2.** Hacen falta **más de** n números exactamente cuando los primeros n todavía no pasaron de 1:

$$P(N > n) = P(S_n \le 1) = \frac{1}{n!}$$

**Paso 3.** Para una variable entera no negativa, E[N] = Σₙ≥₀ P(N > n) (fórmula de la cola):

$$E[N] = \sum_{n=0}^{\infty}\frac{1}{n!} = e$$

que es la serie de Taylor de eˣ en x = 1.

**Distribución del conteo** (es lo que muestra el panel derecho de `intuicion.png`):

$$P(N = n) = \frac{1}{(n-1)!} - \frac{1}{n!} = \frac{n-1}{n!}, \quad n \ge 2$$

| n | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|
| P(N = n) | 0,5000 | 0,3333 | 0,1250 | 0,0333 | 0,0069 | 0,0012 |

**Varianza.** E[N(N−1)] = Σₙ≥₂ (n−1)/(n−2)! = 2e, entonces E[N²] = 3e y

$$\sigma_e = \sqrt{3e - e^2} \approx 0{,}875$$

**Costo.** Un ensayo de e consume en promedio e ≈ 2,72 números aleatorios; un punto de π consume 2.
Por eso, a igual N, el programa de e tarda algo más.

### 6.3 Convergencia

$$\text{error típico}(N) \approx \frac{\sigma}{\sqrt{N}}, \qquad \text{con 95 \% de confianza: } |\text{error}| < 1{,}96\,\frac{\sigma}{\sqrt{N}}$$

| N | error esperado de π | error esperado de e |
|---|---|---|
| 10⁵ | 5,2 × 10⁻³ | 2,8 × 10⁻³ |
| 10⁶ | 1,6 × 10⁻³ | 8,8 × 10⁻⁴ |
| 10⁷ | 5,2 × 10⁻⁴ | 2,8 × 10⁻⁴ |
| 10⁸ | 1,6 × 10⁻⁴ | 8,8 × 10⁻⁵ |
| 10⁹ | 5,2 × 10⁻⁵ | 2,8 × 10⁻⁵ |
| 10¹⁰ | 1,6 × 10⁻⁵ | 8,8 × 10⁻⁶ |

- **Un decimal más cuesta 100 veces más muestras:** dividir el error por 10 exige multiplicar N por 100.
- **En log-log es una recta de pendiente −1/2:** log(error) = log σ − ½ · log N.
- **El error de una corrida es aleatorio:** σ/√N es su tamaño típico, no su valor exacto.

### 6.4 Monte Carlo contra métodos deterministas

| Método | Error con N evaluaciones en dimensión d |
|---|---|
| Trapecios | O(N^(−2/d)) |
| Simpson | O(N^(−4/d)) |
| Monte Carlo | O(N^(−1/2)), sin importar d |

En 1 o 2 dimensiones ganan los deterministas. Monte Carlo le gana a trapecios cuando d > 4 y a
Simpson cuando d > 8.

---

## 7. Preguntas probables

**¿Por qué el error de e es menor que el de π con el mismo N?**
Porque la variable que se promedia tiene menos dispersión (σ = 0,875 contra 1,642). La pendiente −1/2 es la misma.

**¿Importa si comparo con ≤ 1 o con < 1?**
No. El borde del círculo tiene área cero: la probabilidad de caer exactamente ahí es nula.

**¿Cuántas muestras harían falta para 10 decimales de π?**
σ/√N = 10⁻¹⁰ da N ≈ 2,7 × 10²⁰. Inviable. Confirma que el interés del proyecto es el estudio del paralelismo.

**¿El resultado es reproducible?**
Sí, para la misma semilla y la misma cantidad de procesos da exactamente el mismo valor. Cambia si
cambia P, porque cambia qué números usa cada proceso. Eso es esperado y no es un error.

**¿La precisión de `double` limita el resultado?**
No. El error estadístico con N = 10¹⁰ es ~10⁻⁵; el de la doble precisión es ~10⁻¹⁶. Además los
contadores son enteros: se acumulan sin error de redondeo.

**¿Se puede bajar el error sin aumentar N?**
Sí: técnicas de reducción de varianza (bajan σ) o cuasi-Monte Carlo con secuencias de baja
discrepancia como Sobol o Halton (error cercano a 1/N). Están en mejoras futuras (apunte 03).

**¿Por qué no usar el círculo completo?**
Da lo mismo (misma proporción π/4), pero obliga a transformar los números a [−1, 1]: una operación extra sin beneficio.
