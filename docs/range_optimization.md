# Range Optimization Overview

This document describes how the Trade-Up engine searches across ranges of service fee, CXA and CAC bonus values.

## Configurable Parameters

- `service_fee_range`: default `[0.0, 5.0]`
- `cxa_range`: default `[0.0, 4.0]`
- `cac_bonus_range`: default `[0.0, 10000.0]`
- `service_fee_step`: default `0.01`
- `cxa_step`: default `0.01`
- `cac_bonus_step`: default `100`
- `max_combinations_to_test`: default `1000`
- `early_stop_on_offers`: default `100`
- `min_npv_threshold`: offers below this NPV are discarded
- GPS and insurance amounts are taken from the current fee configuration.

## Search Loop

The engine iterates through every combination of the ranges above. For each combination it generates offers using the chosen `term_priority`. Offers whose NPV is below the configured threshold are ignored.

Early stopping occurs when the number of tested combinations exceeds `max_combinations_to_test` or the number of valid offers found reaches `early_stop_on_offers`.

## Payment Delta Tiers

Offers are classified into Refresh, Upgrade and Max Upgrade tiers according to the `payment_delta_tiers` configuration. Within each tier, offers are ranked by NPV.

## Validation

Range bounds must be in ascending order and step sizes must be positive. Invalid settings result in an HTTP 400 error when generating offers.
