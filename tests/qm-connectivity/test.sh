#!/bin/bash -eux

# shellcheck source=tests/e2e/lib/utils
. ../e2e/lib/utils

# shellcheck source=tests/e2e/lib/tests
. ../e2e/lib/tests

test_hirte_list_all_units
