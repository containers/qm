# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

CC = gcc
CFLAGS = -Wall -Wextra -std=c99
LDFLAGS = -lrt

TARGETS = test_mqueue_limit test_host_mqueue
SOURCES = test_mqueue_limit.c test_host_mqueue.c

all: $(TARGETS)

test_mqueue_limit: test_mqueue_limit.c
	$(CC) $(CFLAGS) -o test_mqueue_limit test_mqueue_limit.c $(LDFLAGS)

test_host_mqueue: test_host_mqueue.c
	$(CC) $(CFLAGS) -o test_host_mqueue test_host_mqueue.c $(LDFLAGS)

clean:
	rm -f $(TARGETS)

.PHONY: all clean
