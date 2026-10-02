# Compila la versión serial y la versión MPI.
#   make         compila los dos programas
#   make clean   borra los ejecutables

CFLAGS = -O2 -Wall -Wextra

all: montecarlo_serial montecarlo_mpi

montecarlo_serial: montecarlo_serial.c montecarlo.h
	gcc $(CFLAGS) montecarlo_serial.c -o montecarlo_serial -lm

montecarlo_mpi: montecarlo_mpi.c montecarlo.h
	mpicc $(CFLAGS) montecarlo_mpi.c -o montecarlo_mpi -lm

clean:
	rm -f montecarlo_serial montecarlo_mpi

.PHONY: all clean
