# Scenario Analysis Metrics

The scenario analysis mode uses a small sample of customers to estimate how the engine might perform across the full portfolio.
The process samples up to 100 customers, generates offers for each one and then extrapolates the metrics.

## Calculation Steps

1. **Average Offers per Customer**
   ```
   avg_offers_per_customer = total_offers / processed_customers
   ```
   where `total_offers` is the number of offers produced for the sample and `processed_customers` excludes any that failed.
2. **Average NPV per Offer**
   ```
   avg_npv_per_offer = total_npv / total_offers
   ```
3. **Portfolio Estimates**
   ```
   estimated_total_offers = avg_offers_per_customer * total_customers
   estimated_portfolio_npv = avg_npv_per_offer * estimated_total_offers
   ```
   `total_customers` is the count of all eligible customers in the dataset.

Because these figures are derived from a small sample, the extrapolated totals can be unrealistic if the sample is not representative
or if an unusually high number of offers is generated. Inspect the raw sample metrics and adjust the engine configuration
when numbers appear out of range.
