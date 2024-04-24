#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <linux/sched.h>
#include <sys/syscall.h>
#include <linux/types.h>
#include <sched.h>

struct sched_attr {
    __u32 size;

    __u32 sched_policy;
    __u64 sched_flags;

    // SCHED_NORMAL, SCHED_BATCH
    __s32 sched_nice;

    // SCHED_FIFO, SCHED_RR
    __u32 sched_priority;

    // SCHED_DEADLINE
    __u64 sched_runtime;
    __u64 sched_deadline;
    __u64 sched_period;
};

int sched_setattr(pid_t pid, const struct sched_attr *attr, unsigned int flags) {
    return syscall(SYS_sched_setattr, pid, attr, flags);
}

// Function to get the scheduling policy and priority of the current process
void get_sched() {
    int policy;
    struct sched_param param;

    // Get current scheduling policy
    policy = sched_getscheduler(0);
    if (policy == -1) {
        perror("sched_getscheduler");
        exit(EXIT_FAILURE);
    }

    // Get the current priority
    if (sched_getparam(0, &param) == -1) {
        perror("sched_getparam");
        exit(EXIT_FAILURE);
    }

    printf("Current Scheduling Policy: ");
    switch (policy) {
        case SCHED_OTHER:
            printf("SCHED_OTHER\n");
            break;
        case SCHED_FIFO:
            printf("SCHED_FIFO\n");
            break;
        case SCHED_RR:
            printf("SCHED_RR\n");
            break;
        case SCHED_DEADLINE:
            printf("SCHED_DEADLINE\n");
            break;
        default:
            printf("Unknown\n");
    }

    printf("Current Priority: %d\n", param.sched_priority);
}

int main() {
    struct sched_attr attr;
    memset(&attr, 0, sizeof(attr));  // initialization
    attr.size = sizeof(attr);
    attr.sched_policy = SCHED_DEADLINE;
    attr.sched_runtime = 10 * 1000 * 1000;  // 10 ms
    attr.sched_deadline = 20 * 1000 * 1000;  // 20 ms
    attr.sched_period = 30 * 1000 * 1000;  // 30 ms

    get_sched();

    if (sched_setattr(0, &attr, 0) == -1) {
        perror("sched_setattr failed");
        return 1;
    }

    // Now the thread should be running under SCHED_DEADLINE
    get_sched();

    return 0;
}
