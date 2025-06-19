import numpy_financial as npf
from scipy.optimize import fsolve
from .config import IVA_RATE

def solve_for_max_loan(
    desired_monthly_payment: float,
    interest_rate: float,
    term_months: int,
    fees_config: dict,
    car_price: float = None
) -> float:
    """
    Finds the maximum loan amount for a given desired monthly payment.
    This is the core "goal-seek" function.
    """
    # Unpack fee configuration for the calculation
    kavak_total_amount = fees_config.get('kavak_total_amount', 0)
    insurance_amount = fees_config.get('insurance_amount', 0)
    service_fee_pct = fees_config.get('service_fee_pct', 0)
    fixed_fee = fees_config.get('fixed_fee', 0)

    tasa_mensual_sin_iva = interest_rate / 12
    tasa_mensual_con_iva = tasa_mensual_sin_iva * IVA_RATE

    def objective_function(max_loan_amount_guess):
        # We don't want to test negative loan amounts
        if max_loan_amount_guess < 0:
            return 9999999  # Return a large number to push the solver away

        # Calculate financed amounts for add-ons
        # Kavak Total and Insurance are fixed amounts
        valor_kt = kavak_total_amount if kavak_total_amount > 0 else 0
        valor_seguro = insurance_amount if insurance_amount > 0 else 0
        
        # Service fee is 5% of car price
        if car_price:
            valor_service_fee = car_price * service_fee_pct
        else:
            # If car price not provided, estimate it from loan amount
            # Assuming average 25% down payment
            estimated_car_price = max_loan_amount_guess / 0.75
            valor_service_fee = estimated_car_price * service_fee_pct
        
        # Calculate each component of the monthly payment
        principal_loan = npf.ppmt(tasa_mensual_con_iva, 1, term_months, -max_loan_amount_guess)
        interest_loan = npf.ipmt(tasa_mensual_sin_iva, 1, term_months, -max_loan_amount_guess) * IVA_RATE
        
        # Service fee financed over the full loan term
        principal_service = npf.ppmt(tasa_mensual_con_iva, 1, term_months, -valor_service_fee) if valor_service_fee > 0 else 0
        interest_service = npf.ipmt(tasa_mensual_sin_iva, 1, term_months, -valor_service_fee) * IVA_RATE if valor_service_fee > 0 else 0
        
        principal_kt = npf.ppmt(tasa_mensual_con_iva, 1, term_months, -valor_kt) if valor_kt > 0 else 0
        interest_kt = npf.ipmt(tasa_mensual_sin_iva, 1, term_months, -valor_kt) * IVA_RATE if valor_kt > 0 else 0
        
        # Insurance is financed over 12 months
        principal_seguro = npf.ppmt(tasa_mensual_con_iva, 1, 12, -valor_seguro) if valor_seguro > 0 else 0
        interest_seguro = npf.ipmt(tasa_mensual_sin_iva, 1, 12, -valor_seguro) * IVA_RATE if valor_seguro > 0 else 0

        calculated_payment = (
            principal_loan + interest_loan +
            principal_service + interest_service +
            principal_kt + interest_kt +
            principal_seguro + interest_seguro +
            (fixed_fee * IVA_RATE) / term_months  # Fixed fee spread over term
        )
        
        # The solver tries to make this value zero
        return calculated_payment - desired_monthly_payment

    try:
        # Start with a reasonable guess for the loan amount
        initial_guess = desired_monthly_payment * term_months * 0.6
        max_loan_solution = fsolve(objective_function, x0=initial_guess)[0]
        return max(0, max_loan_solution)
    except Exception as e:
        print(f"Error in solver: {e}")
        return 0.0

def calculate_final_npv(loan_amount, interest_rate, term_months):
    """
    Calculates the Net Present Value of the interest income for the loan,
    discounted at the loan's own monthly rate. The result represents the
    present value of the interest cash-flows that Kavak earns over the
    life of the loan (therefore it should always be ≥ 0).
    """
    if loan_amount <= 0:
        return 0.0
    
    # Generate the cash-flow of interest income for each month.
    # `numpy_financial.ipmt` returns a POSITIVE value when the present value
    # (`pv`) is passed in as a negative number (i.e. cash outflow for the
    # borrower, cash inflow for the lender). Therefore **do not** invert the
    # sign here; we want positive cash-flows for the lender.

    tasa_mensual_sin_iva = interest_rate / 12
    interest_payments = [
        npf.ipmt(tasa_mensual_sin_iva, period, term_months, -loan_amount)
        for period in range(1, term_months + 1)
    ]
    
    # Calculate NPV using the same monthly rate as the discount rate
    npv = npf.npv(tasa_mensual_sin_iva, [0] + interest_payments)
    return npv