#!/bin/bash

# shellcheck disable=SC1094
# shellcheck source=tests/e2e/lib/utils
source ../e2e/lib/utils

# shellcheck disable=SC1094
# shellcheck source=tests/e2e/lib/utils
source ../e2e/lib/tests

test_bluechi_list_all_units
