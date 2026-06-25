#!/bin/bash

set -ex

export BPFTRACE_MAX_STRLEN=200

for preload in "none" "orig" "fix"; do
    bpftrace -o strace-$$-${preload}.log trace.bt -c "sudo -u shenjm -- python3 -m demo --vivado=/tools/Xilinx/2025.1/Vivado/bin/vivado --preload=${preload}"
done
