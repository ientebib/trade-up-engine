# SANITY CHECK - Trade-Up Engine Issues

## 1. AMORTIZATION TABLE MATH PROBLEM

The columns don't add up because:
- Interest is calculated as: base_rate * (1 + IVA) = 0.18 * 1.16 = 0.2088
- But displayed as: base interest + IVA separately
- This creates a mismatch

**Current Display:**
- Capital: $1,703.57
- Interés: $2,002.34 (base interest without IVA)
- IVA: $320.37 (16% of base interest)
- Cargos: $1,276.00
- **Sum: $5,302.28**
- **Exigible: $5,316.96** 
- **DIFFERENCE: $14.68**

**The Real Calculation:**
- Principal: $1,703.57
- Interest WITH IVA: $2,337.38
- GPS fees: $1,276.00
- **Total: $5,316.95**

## 2. FRONTEND/BACKEND MISMATCHES

### Custom Config API
- Frontend sends: `kavak_total_enabled` (boolean)
- Backend expects: `kavak_total_amount` (number)
- **Fixed in offers.py line 138-139**

### Amortization Display
- Template `amortization_table.html` is NOT USED
- Actual display is in `modern_customer_detail_enhanced.html` lines 1168-1197
- **This is why template changes don't show up!**

## 3. CONFIGURATION NOT APPLIED

The basic_matcher was ignoring custom config values:
- `kavak_total_amount` always used DEFAULT_FEES (fixed line 146)
- GPS fees always used constants (fixed lines 152-155)

## 4. ROOT CAUSES OF CONFUSION

1. **Multiple calculation methods**: Some use IVA-inclusive rates, others apply IVA separately
2. **Display logic scattered**: Amortization display in customer detail page, not in template
3. **Silent failures**: Config values ignored without error
4. **Naming mismatches**: Frontend/backend use different parameter names

## 5. WHAT NEEDS TO BE FIXED

1. **Amortization math**: Make columns add up correctly
2. **Use correct template**: Either use amortization_table.html or remove it
3. **Validate config**: Check all custom config values are actually used
4. **Consistent naming**: Frontend and backend should use same parameter names