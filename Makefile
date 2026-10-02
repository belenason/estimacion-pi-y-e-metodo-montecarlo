# Makefile del proyecto: estimación de pi y e por Monte Carlo (serial y MPI).
#
#   make          compila todo lo que haya en src/serial y src/mpi
#   make serial   compila solo las versiones seriales
#   make mpi      compila solo las versiones MPI
#   make info     muestra compiladores y flags en uso
#   make clean    borra los binarios
#
# Todas las versiones se compilan con las MISMAS flags, para que las diferencias
# de tiempo entre versiones se deban solo al código y no al compilador.

CC     := gcc
MPICC  := mpicc

# -O3            optimización máxima estándar
# -march=native  usa las instrucciones del procesador donde se compila
#                (por eso hay que recompilar en cada sistema: PC y clúster)
# -Wall -Wextra -Wpedantic   todas las advertencias activadas
# -D_POSIX_C_SOURCE=200809L  habilita clock_gettime(), que es POSIX y no C11 puro
# No se usa -ffast-math: cambiaría la aritmética de punto flotante.
CFLAGS   := -std=c11 -O3 -march=native -Wall -Wextra -Wpedantic -D_POSIX_C_SOURCE=200809L
INCLUDES := -Isrc/common
LDLIBS   := -lm

BIN := bin

HEADERS    := $(wildcard src/common/*.h)
SERIAL_SRC := $(wildcard src/serial/*.c)
MPI_SRC    := $(wildcard src/mpi/*.c)
SERIAL_BIN := $(patsubst src/serial/%.c,$(BIN)/%,$(SERIAL_SRC))
MPI_BIN    := $(patsubst src/mpi/%.c,$(BIN)/%,$(MPI_SRC))

.PHONY: all serial mpi info clean

all: serial mpi

serial: $(SERIAL_BIN)

mpi: $(MPI_BIN)

$(BIN)/%: src/serial/%.c $(HEADERS) | $(BIN)
	$(CC) $(CFLAGS) $(INCLUDES) $< -o $@ $(LDLIBS)

$(BIN)/%: src/mpi/%.c $(HEADERS) | $(BIN)
	$(MPICC) $(CFLAGS) $(INCLUDES) $< -o $@ $(LDLIBS)

$(BIN):
	mkdir -p $(BIN)

info:
	@echo "CC     = $(CC)    ($$($(CC) --version | head -n 1))"
	@echo "MPICC  = $(MPICC) ($$($(MPICC) --version | head -n 1))"
	@echo "CFLAGS = $(CFLAGS)"
	@echo "Serial : $(SERIAL_BIN)"
	@echo "MPI    : $(MPI_BIN)"

clean:
	rm -rf $(BIN)
