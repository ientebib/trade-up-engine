#!/usr/bin/env bash
set -e
python tools/stress_test_smart_search.py 10 > perf.log
p99=$(grep -o 'p99 [0-9.]*s' perf.log | awk '{print $2}' | tr -d 's')
threshold=${PERF_P99_THRESHOLD:-5}
if [ "$(echo "$p99 > $threshold" | bc -l)" = "1" ]; then
  echo "Performance regression: p99 ${p99}s > ${threshold}s"
  exit 1
fi
