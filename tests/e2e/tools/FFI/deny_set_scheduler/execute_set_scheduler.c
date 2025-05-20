#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sched.h>
#include <errno.h>
#include <string.h>

int main(int argc, char *argv[]) {
    int pid = getpid();
    int policy;  // Desired scheduling policy
    char *policy_name;
    struct sched_param param;

    if (argc == 2)
    {
        policy_name = argv[1];

        if (strcmp(policy_name, "SCHED_OTHER")==0) {
            policy = SCHED_OTHER;
        } else if (strcmp(policy_name, "SCHED_BATCH")==0) {
            policy = SCHED_BATCH;
        } else if (strcmp(policy_name, "SCHED_IDLE")==0) {
            policy = SCHED_IDLE;
        } else if (strcmp(policy_name, "SCHED_FIFO")==0) {
            policy = SCHED_FIFO;
        } else if (strcmp(policy_name, "SCHED_RR")==0) {
            policy = SCHED_RR;
        } else {
            printf("Unknown policy.\n");
            return EXIT_FAILURE;
        }
    }
    else if (argc > 2)
    {
        printf("Too many policies supplied.\n");
        return EXIT_FAILURE;
    }
    else
    {
        printf("One policy expected.\n");
        return EXIT_FAILURE;
    }

    // Assign the maximum priority for the policy
    param.sched_priority = sched_get_priority_max(policy);
    if (param.sched_priority == -1) {
        fprintf(stderr, "Failed to get max priority for %s: %s\n", policy_name, strerror(errno));
        return EXIT_FAILURE;
    }

    // Attempt to set the scheduling policy and priority
    if (sched_setscheduler(pid, policy, &param) == -1) {
        printf("sched_setscheduler(%s) failed: errno=%d (%s)", policy_name, errno, strerror(errno));
        return EXIT_FAILURE;
    } else {
        printf("sched_setscheduler(%s) succeeded.", policy_name);
        return EXIT_SUCCESS;
    }
}
