#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sched.h>
#include <errno.h>
#include <string.h>

int main() {
    int pid = getpid(); 
    int policy = SCHED_FIFO;  // Desired scheduling policy
    struct sched_param param;

    // Assign the maximum priority for the SCHED_FIFO policy
    param.sched_priority = sched_get_priority_max(policy);
    if (param.sched_priority == -1) {
        fprintf(stderr, "Failed to get max priority for SCHED_FIFO: %s\n", strerror(errno));
        return EXIT_FAILURE;
    }

    // Attempt to set the scheduling policy and priority
    if (sched_setscheduler(pid, policy, &param) == -1) {
        fprintf(stderr, "Failed to set scheduler: %s\n", strerror(errno));
        return EXIT_FAILURE;
    }

    printf("Scheduler set to SCHED_FIFO with priority %d\n", param.sched_priority);
    return EXIT_SUCCESS;
}
