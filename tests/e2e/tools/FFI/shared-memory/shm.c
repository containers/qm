#include <sys/mman.h>
#include <sys/stat.h>        /* For mode constants */

#include <fcntl.h>           /* For O_* constants */
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>


/* simple SHM access test which can be used to test access e.g. through
 * container boundaries */

int main(int argc, char* argv[]) {

  /* use the hostname to pepper the seed because we start this several times
   * quickly within separate containers or on the bare system, so time() alone
   * is not good enough */
  char hostname[HOST_NAME_MAX];
  gethostname(hostname, HOST_NAME_MAX);
  int sum = 0;
  for (char *c = hostname; *c != '\0'; c++) {
    sum += (int)*c;
  }

  srand(time(NULL) + sum);

  int timeout = 2;
  int value = rand();
  char shm_name[NAME_MAX];
  struct timespec ts_start, ts_elapsed;

  if (argc > 1) {
    strncpy(shm_name, argv[1], NAME_MAX-1);
    shm_name[NAME_MAX] = '\0';
  } else {
    strcpy(shm_name, "/memtest");
  }
  if (argc > 2) {
    value = atoi(argv[2]);
  }
  if (argc > 3) {
    timeout = atoi(argv[3]);
  }

  printf("Test is starting!\n"
         "Hostname: %s  |  IPC name: %s  |  Initial value: %d\n",
         hostname, shm_name, value);

  int fd = shm_open(shm_name, O_CREAT | O_RDWR, S_IRUSR | S_IWUSR);
  if (fd < 0) {
    perror("shm_open");
    return 1;
  }

  if (ftruncate(fd, sizeof(int)) < 0) {
    perror("ftruncate");
    return 1;
  }

  int *payload = mmap(NULL, sizeof(int), PROT_READ | PROT_WRITE, MAP_SHARED,
                      fd, 0);

  if (payload == MAP_FAILED) {
    perror("mmap");
    return 1;
  }

  *payload = value;

  clock_gettime(CLOCK_MONOTONIC, &ts_start);
  long elapsed = 0;

  // barrier
  while(*payload == value) {
    clock_gettime(CLOCK_MONOTONIC, &ts_elapsed);
    // keep it coarse, +-1sec is totally unimportant
    elapsed = ts_elapsed.tv_sec - ts_start.tv_sec;
    if (elapsed >= timeout) {
      fprintf(stderr, "Test aborted, timeout!\n");
      munmap(payload, sizeof(int));
      shm_unlink(shm_name);
      return 1;
    }
  }
  printf("SHM access - value changed to: %d\n", *payload);

  // signal the other process to also stop
  *payload = value;

  munmap(payload, sizeof(int));
  shm_unlink(shm_name);

  return 0;
}

