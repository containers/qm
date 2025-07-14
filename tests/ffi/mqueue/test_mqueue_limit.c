// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>
#include <sys/stat.h>
#include <mqueue.h>

// Allow MAX_QUEUES to be set via the environment variable "QM_QUEUE_COUNT", defaulting to 6 if not set
int get_max_queues() {
    const char *env = getenv("QM_QUEUE_COUNT");
    if (env) {
        int val = atoi(env);
        if (val > 0 && val < 1000) {
            return val;
        }
    }
    return 6;
}
#define MAX_QUEUES (get_max_queues())
#define QUEUE_NAME_PREFIX "/test_queue_"

int main() {
    mqd_t queues[MAX_QUEUES];
    char queue_names[MAX_QUEUES][32];
    int i, created_queues = 0;
    struct mq_attr attr;

    // Initialize queue attributes (minimal to avoid memory limits)
    attr.mq_flags = 0;
    attr.mq_maxmsg = 1;      // Minimal: only 1 message per queue
    attr.mq_msgsize = 64;    // Minimal: small message size
    attr.mq_curmsgs = 0;

    printf("Testing message queue limit enforcement...\n");

    // Clean up any existing queues from previous runs
    for (i = 0; i < MAX_QUEUES; i++) {
        snprintf(queue_names[i], sizeof(queue_names[i]), "%s%d", QUEUE_NAME_PREFIX, i);
        mq_unlink(queue_names[i]);
    }

    // Try to create message queues
    for (i = 0; i < MAX_QUEUES; i++) {
        printf("Attempting to create queue %s... ", queue_names[i]);

        queues[i] = mq_open(queue_names[i], O_CREAT | O_RDWR, 0666, &attr);

        if (queues[i] == -1) {
            printf("FAILED: %s\n", strerror(errno));
            if (errno == ENOSPC) {
                printf("Queue limit reached as expected at queue %d\n", i);
                break;
            } else {
                printf("Unexpected error: %s\n", strerror(errno));
                // Clean up before exiting
                for (int j = 0; j < i; j++) {
                    mq_close(queues[j]);
                    mq_unlink(queue_names[j]);
                }
                return 1;
            }
        } else {
            printf("SUCCESS\n");
            created_queues++;
        }
    }

    printf("\nSuccessfully created %d message queues\n", created_queues);

    // Expected behavior: should be able to create exactly 4 queues
    if (created_queues == 4) {
        printf("PASS: Created exactly 4 queues as expected (limit is working)\n");
    } else if (created_queues < 4) {
        printf("FAIL: Created fewer than 4 queues (%d), limit may be too restrictive\n", created_queues);
    } else {
        printf("FAIL: Created more than 4 queues (%d), limit is not enforced properly\n", created_queues);
    }

    // Clean up created queues
    for (i = 0; i < created_queues; i++) {
        mq_close(queues[i]);
        mq_unlink(queue_names[i]);
    }

    return (created_queues == 4) ? 0 : 1;
}
