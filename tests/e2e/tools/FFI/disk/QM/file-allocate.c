#include <stdio.h>
#include <stdlib.h>

int main() {
    const size_t chunkSize = 500L * 1024 * 1024;  // 500 MB
    const char *filePath = "/foobar.file";   // Change this path as needed
    char *data = malloc(chunkSize);
    FILE *fp;
    int count = 0;

    if (data == NULL) {
        perror("Failed to allocate memory");
        return 1;
    }

    // Fill the data array with some dummy content
    for (size_t i = 0; i < chunkSize; i++) {
        data[i] = '+';
    }

    fp = fopen(filePath, "w");
    if (fp == NULL) {
        perror("Failed to open file");
        free(data);
        return 1;
    }

    while (1) {
        size_t written = fwrite(data, 1, chunkSize, fp);
        if (written < chunkSize) {
            printf("Failed to write after %d x 500 MB\n", count);
            break;
        } else {
            count++;
            printf("Written %d x 500 MB\n", count);
        }
        fflush(fp);  // Make sure data is flushed to disk
    }

    fclose(fp);
    free(data);
    return 0;
}
