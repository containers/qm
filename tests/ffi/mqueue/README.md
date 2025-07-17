# FFI - Message Queue Limit Test

This test verifies that the `fs.mqueue.queues_max=4` sysctl setting is properly applied in the QM container and that the limit is correctly enforced while the host maintains independent message queue capacity.

## Test Overview

The test validates message queue isolation by:

1. **Host baseline**: Creates message queues on the host before container testing
2. **Container limit verification**: Confirms QM container can create exactly 4 queues then hits limit
3. **Host isolation verification**: Creates additional message queues on host after container limit reached
4. **Comprehensive isolation**: Demonstrates that container limits don't affect host queue availability

## Test Components

### test_mqueue_limit.c

A C program that runs inside the QM container:

- Creates message queues using the POSIX message queue API
- Attempts to create up to `QM_QUEUE_COUNT` message queues (default: 6)
- Validates that exactly 4 queues can be created (container limit)
- Properly handles the `ENOSPC` error when the limit is reached
- Uses minimal queue sizes (1 message, 64 bytes) to test count limits, not memory limits

### test_host_mqueue.c

A C program that runs on the host system:

- Creates individual message queues on the host filesystem
- Uses same minimal queue attributes as container test
- Demonstrates host queue creation capability independent of container limits

### test.sh

The main test script that:

- Follows enhanced FFI test pattern with three phases
- **Phase 1**: Creates `HOST_QUEUE_COUNT` message queues on host
- **Phase 2**: Verifies container sysctl and runs container limit test
- **Phase 3**: Creates `HOST_QUEUE_COUNT` additional queues on host
- Comprehensive cleanup of both host and container artifacts

## Configuration

### Environment Variables

- `HOST_QUEUE_COUNT`: Number of queues to create on host in each phase (default: 3)
- `QM_QUEUE_COUNT`: Number of queues to attempt in container test (default: 6)

## Expected Results

- **PASS**:
  - Host creates `HOST_QUEUE_COUNT` queues successfully (before)
  - Container creates exactly 4 message queues then hits limit
  - Host creates `HOST_QUEUE_COUNT` additional queues successfully (after)
  - Total: `2 * HOST_QUEUE_COUNT` host queues + 4 container queues (isolated)

- **FAIL**:
  - Host queue creation affected by container limits
  - Container creates more/fewer than 4 queues
