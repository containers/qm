CC = gcc
CFLAGS = -Wall -g

VPATH=disk/QM:memory/ASIL:memory/QM
QM_BIN=./bin/QM
ASIL_BIN=./bin/ASIL

all: cratetestqm cratetestasil

cratetestqm: createqmbin file-allocate 90_percent_memory_eat

cratetestasil: createasilbin 20_percent_memory_eat

createqmbin:
	@mkdir -p $(QM_BIN)

createasilbin:
	@mkdir -p $(ASIL_BIN)

20_percent_memory_eat: 20_percent_memory_eat.c
	$(CC) $(CFLAGS) -o $(ASIL_BIN)/$@ $<

file-allocate: file-allocate.c
	$(CC) $(CFLAGS) -o $(QM_BIN)/$@ $<

90_percent_memory_eat: 90_percent_memory_eat.c
	$(CC) $(CFLAGS) -o $(QM_BIN)/$@ $<

clean:
	rm -rf $(QM_BIN) $(ASIL_QM)

.PHONY: all clean createtestqm createtestasil
