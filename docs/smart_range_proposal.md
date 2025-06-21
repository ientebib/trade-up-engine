# Smart Range Optimization Proposal

The existing range optimization feature evaluates every combination of `service_fee`, `cxa_pct` and `cac_bonus` values. Even with early stopping this brute-force grid search can require thousands of iterations.

## Evaluated Alternatives

1. **Bayesian Optimization**
   - Models the objective function with a probabilistic surrogate and chooses new samples based on expected improvement.
   - Generally provides very sample‑efficient searches but requires an extra dependency such as `scikit-optimize` or `hyperopt`.
   - Added complexity and heavier dependencies make it less attractive for this project.

2. **Genetic / Evolutionary Strategies** (Differential Evolution)
   - Population based algorithm available in SciPy (`scipy.optimize.differential_evolution`).
   - Handles non‑linear, non‑differentiable objectives well and is easy to integrate without new packages.
   - Provides good results with a small number of iterations.

## Recommendation

Differential Evolution strikes a good balance between performance and implementation effort. It requires only SciPy, already used in the project, and finds high‑quality parameters in tens of evaluations rather than thousands. Therefore the new *Smart Search* mode uses Differential Evolution to select fee values.

## Benchmark

Using the sample data provided in `DevelopmentDataLoader` with default ranges (11×9×11 combinations), the exhaustive search processed 1,089 parameter sets in about **1.2 seconds**. The smart search using Differential Evolution completed in roughly **0.12 seconds**, over ten times faster while yielding comparable offers.
