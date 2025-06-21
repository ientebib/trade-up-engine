#!/usr/bin/env bash
set -e

# Check for required commands
for cmd in bc grep awk; do
  if ! command -v "$cmd" &> /dev/null; then
    echo "Error: Required command '$cmd' not found." >&2
    exit 1
  fi
done

# Run the stress test and capture output
if ! python tools/stress_test_smart_search.py 10 > perf.log; then
  echo "Error: Stress test script failed." >&2
  exit 1
fi

# Parse p99 value and validate
p99_line=$(grep -o 'p99 [0-9.]*s' perf.log)
if [ -z "$p99_line" ]; then
    echo "Error: Could not find p99 value in performance log." >&2
    exit 1
fi

p99=$(echo "$p99_line" | awk '{print $2}' | tr -d 's')
if ! [[ "$p99" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
    echo "Error: Invalid p99 value '$p99'." >&2
    exit 1
fi

threshold=${PERF_P99_THRESHOLD:-5}
if [ "$(echo "$p99 > $threshold" | bc -l)" = "1" ]; then
  echo "Performance regression: p99 ${p99}s > ${threshold}s"
  exit 1
fi

echo "Performance check passed: p99 ${p99}s <= ${threshold}s"
