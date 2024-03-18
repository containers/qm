CC = gcc
CFLAGS = -Wall -g
CFLAGS_SHM = -lrt -Wall -Werror

VPATH=disk/QM:memory:shared-memory
QM_BIN=./bin/QM
ASIL_BIN=./bin/ASIL

all: cratetestqm cratetestasil

cratetestqm: createqmbin file-allocate 90_percent_memory_eat tst_shm

cratetestasil: createasilbin 20_percent_memory_eat tst_sys_shm

createqmbin:
	@mkdir -p $(QM_BIN)

createasilbin:
	@mkdir -p $(ASIL_BIN)

20_percent_memory_eat: memory_eat.c
	$(CC) $(CFLAGS) -DMEM_PERCENT=0.2 -o $(ASIL_BIN)/$@ $<

file-allocate: file-allocate.c
	$(CC) $(CFLAGS) -o $(QM_BIN)/$@ $<

90_percent_memory_eat: memory_eat.c
	$(CC) $(CFLAGS) -DMEM_PERCENT=0.9 -o $(QM_BIN)/$@ $<

tst_sys_shm: shm.c
	$(CC) $(CFLAGS_SHM) -o $(ASIL_BIN)/$@ $<

tst_shm: shm.c
	$(CC) $(CFLAGS_SHM) -o $(QM_BIN)/$@ $<

clean:
	rm -rf $(QM_BIN) $(ASIL_QM)

.PHONY: all clean createtestqm createtestasil
