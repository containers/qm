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
#include <mqueue.h>
#include <sys/stat.h>
#include <errno.h>
#include <string.h>

int main(int argc, char *argv[]) {
    if (argc != 2) {
        fprintf(stderr, "Usage: %s <queue_name>\n", argv[0]);
        return 1;
    }

    struct mq_attr attr;
    attr.mq_flags = 0;
    attr.mq_maxmsg = 1;      // Minimal: only 1 message per queue
    attr.mq_msgsize = 64;    // Minimal: small message size
    attr.mq_curmsgs = 0;

    mqd_t mq = mq_open(argv[1], O_CREAT | O_RDWR, 0666, &attr);
    if (mq == -1) {
        fprintf(stderr, "Failed to create queue %s: %s\n", argv[1], strerror(errno));
        return 1;
    }

    printf("Successfully created queue %s\n", argv[1]);
    mq_close(mq);
    return 0;
}
