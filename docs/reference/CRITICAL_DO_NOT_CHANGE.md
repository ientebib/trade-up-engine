# CRITICAL: DO NOT CHANGE THESE CALCULATIONS

## VALIDATED CALCULATION LOGIC (MATCHES EXCEL)

The following calculation logic has been validated against Excel and MUST NOT BE CHANGED:

### 1. NPV Calculation (engine/calculator.py)
- `calculate_final_npv()` function - Lines 6-29
- Uses audited method: contractual rate for cash flows, IVA-inclusive rate for discounting
- **DO NOT MODIFY**

### 2. Monthly Payment Calculation (engine/payment_utils.py)
- Bucketized payment calculation with separate principal/interest for each component
- IVA applied once to interest rate at beginning: `rate_with_iva = rate * (1 + IVA_RATE)`
- **DO NOT MODIFY**

### 3. Amortization Logic (engine/calculator.py - generate_amortization_table)
- Multi-bucket amortization with main loan, service fee, Kavak Total, insurance
- Insurance resets every 12 months
- GPS fees added separately
- **DO NOT MODIFY THE CORE CALCULATION**

## WHAT CAN BE CHANGED

Only fix these issues WITHOUT touching calculations:
1. Frontend/backend parameter name mismatches
2. Display formatting and column headers
3. API endpoint routing
4. Configuration parameter passing
5. Validation and error handling

## GROUND TRUTH VALUES

These values have been validated:
- IVA_RATE = 0.16 (NOT 1.16)
- Interest calculations use rate * (1 + IVA_RATE)
- NPV matches risk team's Excel model
- Monthly payments match production calculations