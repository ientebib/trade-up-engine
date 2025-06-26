# Context of Business Logic and App Intended Functionality

## 🎯 Executive Summary

The **Trade-Up Engine** is a financial technology platform that helps Kavak customers upgrade their vehicles while maintaining similar monthly payments. It analyzes customer loan data, vehicle inventory, and financial parameters to identify profitable trade-up opportunities that benefit both the customer and Kavak.

## 🚗 What Problem Are We Solving?

### Customer Pain Points
1. **Payment Shock**: Customers want better cars but can't afford significantly higher monthly payments
2. **Equity Trap**: Many customers have equity in their current vehicle but don't know how to leverage it
3. **Complex Math**: Calculating new loan terms with taxes, fees, and insurance is overwhelming

### Business Opportunity
- **Inventory Turnover**: Move slower-selling vehicles by matching them with qualified buyers
- **Customer Retention**: Keep customers in the Kavak ecosystem with upgrade paths
- **Revenue Growth**: Generate additional revenue through service fees and financing

## 💰 What Are We Calculating?

### 1. **Effective Customer Equity**
```
Starting Equity = Current Vehicle Value - Outstanding Loan Balance
Effective Equity = Starting Equity + CAC Bonus - Opening Fees - GPS Installation
```

The customer's true buying power after accounting for all upfront costs.

### 2. **New Monthly Payment**
Complex calculation including:
- **Principal & Interest**: Mexican loans require IVA (16% tax) on interest
- **GPS Tracking**: Monthly fee (350 MXN + IVA)
- **Insurance**: Annual premium financed over 12-month cycles
- **Kavak Total**: Extended warranty protection (optional)

### 3. **Payment Change Percentage**
```
Payment Delta = (New Payment / Current Payment) - 1
```

This determines which tier the offer falls into:
- **Refresh Tier**: -5% to +5% (similar payment)
- **Upgrade Tier**: +5% to +25% (moderate increase)
- **Max Upgrade Tier**: +25% to +100% (significant increase)

### 4. **Net Present Value (NPV)**
Profitability calculation for Kavak:
```
NPV = Service Fees + Opening Fees - Risk Adjustment
```

Offers are ranked by NPV within each tier to maximize profitability.

## 🔄 What Are We Matching?

### Customer Profile ← → Vehicle Inventory

The matching algorithm considers:

1. **Financial Constraints**
   - Can the customer afford the down payment?
   - Does the new payment fit their budget?
   - Is the loan amount within risk limits?

2. **Vehicle Upgrade Path**
   - Only shows vehicles MORE expensive than current car
   - Filters by year (must be same year or newer)
   - Considers mileage (prefers lower mileage options)

3. **Risk-Based Pricing**
   - Interest rates vary by customer risk profile (A1 = 19.49%, E5 = 43.99%)
   - Down payment requirements increase with risk
   - Some profiles restricted from certain loan terms

## 📊 The Matching Process

### Stage 1: Database Pre-Filtering
```sql
SELECT * FROM inventory 
WHERE price > customer_current_price
  AND year >= customer_current_year
  AND mileage < customer_current_mileage + 20000
```
Reduces 4,000+ vehicles to ~300-500 candidates.

### Stage 2: Financial Viability Check
For each vehicle and loan term (12, 24, 36, 48, 60, 72 months):
1. Calculate required down payment
2. Check if customer has sufficient equity
3. Calculate new monthly payment
4. Determine payment tier
5. Calculate NPV for ranking

### Stage 3: Offer Organization
- Group by payment tier
- Sort by NPV (highest first)
- Return top offers in each tier

## 🏦 Why These Specific Calculations?

### Mexican Auto Loan Regulations
- **IVA on Interest**: 16% tax must be added to interest portions
- **GPS Requirement**: All financed vehicles must have GPS tracking
- **Insurance Mandate**: Comprehensive insurance required for loan duration

### Business Model Requirements
- **Service Fees**: 4% of vehicle price (Kavak's primary revenue)
- **Opening Fees**: 4% CXA (Comisión por Apertura)
- **Risk Management**: NPV ensures profitable transactions

### Customer Protection
- **Transparent Pricing**: All fees shown upfront
- **Payment Tiers**: Clear categorization of affordability
- **No Hidden Costs**: Amortization table shows every peso

## 🎨 User Experience Flow

1. **Customer Selection**
   - Staff selects customer from database
   - Views current loan details and equity position

2. **Offer Generation**
   - Click "Generate Offers" 
   - System runs matching algorithm (~2 seconds)
   - Returns categorized offers

3. **Offer Review**
   - See payment change clearly displayed
   - Review full loan terms
   - View detailed amortization table

4. **Configuration**
   - Adjust fees, rates, and bonuses
   - Regenerate offers with custom parameters
   - Find the perfect match for each customer

## 🚀 Business Impact

### For Customers
- **Easy Upgrades**: Find better cars with similar payments
- **Transparent Process**: See all costs upfront
- **Flexible Options**: Multiple terms and tiers to choose from

### For Kavak
- **Increased Sales**: Convert browsers into upgraders
- **Better Margins**: NPV optimization ensures profitability
- **Data-Driven**: Every offer backed by financial analysis

### Success Metrics
- **Offer Acceptance Rate**: % of customers who proceed with upgrade
- **Average NPV**: Profitability per transaction
- **Payment Tier Distribution**: Balance between tiers
- **Processing Time**: Sub-2 second offer generation

## 🔧 Technical Innovation

### Performance Optimization
- **Two-Stage Filtering**: 85-92% reduction in processing
- **Parallel Processing**: Uses all CPU cores
- **Smart Caching**: 4-hour TTL on inventory data

### Financial Accuracy
- **Decimal Precision**: No floating-point errors
- **Audit Trail**: Every calculation logged
- **Excel Compatibility**: Matches spreadsheet calculations exactly

### Scalability
- **No Global State**: Supports multiple server instances
- **On-Demand Queries**: Memory efficient
- **Modular Architecture**: Easy to extend and maintain

## 📈 Future Enhancements

1. **Machine Learning**: Predict which offers customers most likely to accept
2. **Real-Time Inventory**: Direct integration with sales system
3. **Mobile App**: Allow customers to explore upgrades themselves
4. **A/B Testing**: Optimize tier boundaries and fee structures
5. **Regional Pricing**: Adjust for local market conditions

---

The Trade-Up Engine transforms complex financial calculations into simple, actionable upgrade opportunities that drive business growth while delighting customers with their new vehicles.