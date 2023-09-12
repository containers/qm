#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/sysinfo.h>
#include <unistd.h>

int main() {
    struct sysinfo si;
    if (sysinfo(&si) != 0) {
        perror("sysinfo");
        return EXIT_FAILURE;
    }

    unsigned long total_memory = si.totalram * si.mem_unit;
    unsigned long memory_to_allocate = 0.2 * total_memory;

    char *buffer = malloc(memory_to_allocate);

    if (buffer == NULL) {
        perror("malloc");
        return EXIT_FAILURE;
    }

    // Filling the memory with zeros to ensure it's actually allocated
    memset(buffer, 0, memory_to_allocate);
    printf("Allocated %lu bytes out of %lu total bytes.\n", memory_to_allocate, total_memory);

    // Writing data to the allocated memory
    const char *message = "Test, Test!";
    if (memory_to_allocate > strlen(message)) {
        memcpy(buffer, message, strlen(message));
        // Reading and printing the written data
        printf("Data in buffer: %s\n", buffer);
    } else {
        printf("Not enough space to write message.\n");
    }

    // Keeping the program running to hold onto the memory
    while (1) {
        sleep(1);
    }

    free(buffer);
    return EXIT_SUCCESS;
}
