# Performance Budgets

The engine targets the following performance characteristics:

| Metric | Budget |
|-------|--------|
| Cold start time | < 2s |
| Steady-state RPS | > 50 |
| Memory usage | < 300MB |
| Range search p99 latency | < 5s |

`run_perf_gate.sh` executes a small stress test of the smart range search and fails if the 99th percentile latency exceeds the budget. CI should call this script after unit tests to detect regressions.
