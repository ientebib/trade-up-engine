# 💰 Kavak Trade-Up Engine - Fee Configuration Review

## 🚨 **IMPORTANT: These are placeholder values that need confirmation!**

The current fee structure in `config.py` uses placeholder values. Please review and confirm the actual values used by Kavak.

## 📊 **Current Fee Structure**

### **1. Service Fee (`service_fee_pct`)**
- **Current Value:** `5%` of car price
- **How it works:** Spread over the loan term as monthly fee
- **Example:** Car worth $200,000 → $10,000 service fee → $167/month (60-month term)

### **2. Opening Fee / Comisión por Apertura (`cxa_pct`)**
- **Current Value:** `3%` of car price
- **How it works:** Deducted from customer's vehicle equity upfront
- **Example:** Car worth $200,000 → $6,000 opening fee (reduces available down payment)

### **3. Kavak Total (`kavak_total_pct`)**
- **Current Value:** `5%` of car price
- **How it works:** Optional add-on, financed over the loan term
- **Example:** Car worth $200,000 → $10,000 Kavak Total → $193/month extra (60-month term)

### **4. Insurance (`insurance_pct`)**
- **Current Value:** `5%` of car price
- **How it works:** Financed over 12 months (typical insurance term)
- **Example:** Car worth $200,000 → $10,000 insurance → $893/month for 12 months

### **5. Fixed Fee (`fixed_fee`)**
- **Current Value:** `$350 MXN`
- **How it works:** Fixed amount spread over loan term (with 16% IVA)
- **Example:** $350 × 1.16 = $406 → $6.77/month (60-month term)

### **6. CAC Bonus (`cac_bonus`)**
- **Current Value:** `$0 - $5,000 MXN` (subsidy range)
- **How it works:** Cash bonus added to customer's effective equity
- **Example:** $5,000 bonus increases customer's buying power

## 🧮 **Monthly Payment Calculation Example**

For a customer buying a $300,000 car with 60-month financing at 20% interest:

```
Base Loan Payment (20% APR + IVA):     $4,832/month
+ Service Fee (5% spread over term):   +$250/month
+ Kavak Total (5% financed):          +$289/month  
+ Insurance (5% over 12 months):      +$1,340/month (first 12 months)
+ Fixed Fee (with IVA):               +$10/month
─────────────────────────────────────
TOTAL MONTHLY PAYMENT:                $6,721/month
```

## ❓ **Questions for Confirmation**

1. **Service Fee:** Is 5% correct? How is it typically structured?
2. **Opening Fee:** Is 3% correct? Is this always deducted upfront?
3. **Kavak Total:** Is 5% correct? Is this always optional?
4. **Insurance:** Is 5% correct? Is it always financed over 12 months?
5. **Fixed Fee:** Is $350 MXN correct? What does this cover?
6. **Interest Rate Application:** Do we apply 16% IVA to the interest rate or separately?

## 🔧 **How to Update Values**

To change these values, edit the `DEFAULT_FEES` dictionary in `config.py`:

```python
DEFAULT_FEES = {
    'service_fee_pct': 0.05,      # ← Change this value
    'cxa_pct': 0.03,              # ← Change this value  
    'kavak_total_pct': 0.05,      # ← Change this value
    'insurance_pct': 0.05,        # ← Change this value
    'fixed_fee': 350.0            # ← Change this value
}
``` 
