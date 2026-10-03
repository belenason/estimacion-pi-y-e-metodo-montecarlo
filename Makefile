# Compila las versiones serial y MPI para pi y e.
#   make         compila los cuatro programas
#   make clean   borra los ejecutables

CFLAGS = -O2 -Wall -Wextra

all: montecarlo_pi_serial montecarlo_e_serial montecarlo_pi_mpi montecarlo_e_mpi

montecarlo_pi_serial: montecarlo_pi_serial.c montecarlo.h montecarlo_pi.h
	gcc $(CFLAGS) montecarlo_pi_serial.c -o montecarlo_pi_serial -lm

montecarlo_e_serial: montecarlo_e_serial.c montecarlo.h montecarlo_e.h
	gcc $(CFLAGS) montecarlo_e_serial.c -o montecarlo_e_serial -lm

montecarlo_pi_mpi: montecarlo_pi_mpi.c montecarlo.h montecarlo_pi.h
	mpicc $(CFLAGS) montecarlo_pi_mpi.c -o montecarlo_pi_mpi -lm

montecarlo_e_mpi: montecarlo_e_mpi.c montecarlo.h montecarlo_e.h
	mpicc $(CFLAGS) montecarlo_e_mpi.c -o montecarlo_e_mpi -lm

clean:
	rm -f montecarlo_pi_serial montecarlo_e_serial montecarlo_pi_mpi montecarlo_e_mpi

.PHONY: all clean
