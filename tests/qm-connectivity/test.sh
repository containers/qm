#!/bin/bash -eux

# shellcheck disable=SC1094
# shellcheck source=tests/e2e/lib/utils
. ../e2e/lib/utils

# shellcheck disable=SC1094
# shellcheck source=tests/e2e/lib/utils
. ../e2e/lib/tests

test_hirte_list_all_units
