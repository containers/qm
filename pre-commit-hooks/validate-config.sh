#!/usr/bin/bash

set -eu

if command -v packit; then
  packit -d validate-config
else
  echo "packit not installed, can't validate the config"
  echo "either install packit or try the validate-config-in-container hook"
fi
