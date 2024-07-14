CC = gcc
CFLAGS = -Wall -g

VPATH=disk/QM:memory:deny_set_scheduler:deny_sched_setattr
QM_BIN=./bin/QM
ASIL_BIN=./bin/ASIL

all: cratetestqm cratetestasil

cratetestqm: createqmbin file-allocate 90_percent_memory_eat test_sched_setscheduler execute_sched_setattr

cratetestasil: createasilbin 20_percent_memory_eat

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

test_sched_setscheduler: execute_set_scheduler.c
	$(CC) $(CFLAGS) -o $(QM_BIN)/$@ $<

execute_sched_setattr: execute_sched_setattr.c
	$(CC) $(CFLAGS) -o $(QM_BIN)/$@ $<

clean:
	rm -rf $(QM_BIN) $(ASIL_QM)

.PHONY: all clean createtestqm createtestasil
