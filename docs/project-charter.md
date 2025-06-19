Of course. Let's create the definitive, comprehensive Project Charter. This version will be meticulously detailed, leaving no ambiguity. It will explain not just the "what," but the deep "why" behind every rule, every calculation, and every strategic decision, incorporating the specificity of the financial logic we've uncovered.

This is the document you can share with anyone—from a new engineer to a C-level executive—to give them a complete and rigorous understanding of the Trade-Up Engine.

Project Charter: The Kavak Trade-Up Engine (Definitive Edition)
1. Business Rationale & Strategic Vision: Why We Are Building This

1.1. The Untapped Asset: Our Loan Portfolio
Kavak's most valuable, yet under-leveraged, asset is our portfolio of active auto loans. These clients represent a captive audience of verified, loyal customers who are on a predictable ownership timeline. Currently, our interaction is passive; we wait for them to act. The Trade-Up Engine initiative is a strategic imperative to reverse this. We will build a proactive, intelligent system to engage these customers at the precise moment of maximum opportunity, transforming single transactions into a recurring, high-margin revenue stream.

1.2. Core Strategic Objectives
This is not merely a feature; it's a core business driver designed to:

Compound Customer Lifetime Value (LTV): Systematically drive repeat transactions, fundamentally altering the unit economics of our customer acquisition cost.

Fortify Customer Retention: Create a "golden handcuff" effect by offering a seamless, data-driven upgrade path that is superior to any competitor's offering.

Optimize Inventory Strategy: Use Trade-Up offers as a surgical tool to acquire high-demand, high-margin vehicles for our inventory, directly addressing supply-side needs.

Revolutionize Sales & Marketing: Shift from generic campaigns to hyper-personalized, mathematically optimized offers that significantly increase conversion rates and operational efficiency.

2. The Product Vision: What We Are Building

We are building a centralized financial offer-generation service. It is the "brain" that will power all proactive retention efforts at Kavak. Its primary function is to answer a single, complex question for any given customer:

"Considering this customer's unique financial profile, their current loan, and every car in our inventory, what are all the mathematically possible and strategically sound upgrade offers we can present to them right now?"

The final product will manifest in three distinct stages:

The Internal Engine & Diagnostic Tool: A robust backend service with a simple UI for our internal teams to validate logic, analyze raw output, and understand the engine's mechanics.

The Sales & Marketing Enabler: An integrated tool that pushes curated "Top Offers" into our CRM, empowering sales agents and fueling automated marketing campaigns.

The Customer-Facing Experience: The ultimate goal—a feature within the Kavak app that allows customers to self-discover their personalized upgrade options, creating a powerful, engaging user experience.

3. The Logic Rationale: The "Engine's Philosophy"

The engine's intelligence comes from its adherence to a clear set of financial and commercial principles.

3.1. Profit-First, Concession-Based Hierarchy
The engine is designed to be inherently profitable. It will never "give away" margin unnecessarily. Its core search process follows a strict top-down methodology: it always starts by attempting to construct an offer with all fees and commissions at their maximum. Only if this "Max Profit" scenario fails to meet the customer's affordability constraints will the engine begin a "dial-down" cascade, systematically sacrificing margin in a pre-defined, strategic order. This ensures we capture the maximum possible value from every single transaction.

3.2. Customer-Centric Classification via Payment Delta
We understand that the most meaningful metric to a customer is "How much does my monthly payment change?". Therefore, our entire product classification system is based on this single, powerful metric. Every generated offer is categorized into one of three tiers, which allows us to apply different business rules and understand the nature of the offer from the customer's perspective.

3.3. Rigorous Financial Modeling
Every calculation is designed to mirror real-world financial complexity.

Net Present Value (NPV): We do not use simple gross profit as our primary success metric. Instead, we calculate the NPV of the new loan's interest stream. This gives us the true, long-term financial value of the transaction to Kavak, allowing for sophisticated ranking and decision-making.

Component-Based Payment Calculation: We recognize that a monthly payment is not monolithic. Our calculator correctly models the amortization of different components over different timeframes (e.g., the car loan over 60 months vs. the first year's insurance over 12 months), ensuring the calculated payment is precise and reflects the customer's actual payment schedule for the first year.

4. The Definitive Rule Set: The "Engine's DNA"

These are the precise rules that govern every calculation. All placeholders have been replaced with the specific logic required.

4.1. The Unbreakable Gates (Hard Filters)
An offer is only considered for calculation if it passes all three of these initial checks:

Price Appreciation Rule: new_car_price must be strictly greater than current_car_price. We are only offering upgrades.

Minimum Down Payment (Z%) Rule: The customer's effective equity must satisfy the requirement for their risk profile and the chosen loan term. The formula is: Effective Vehicle Equity >= (new_car_price * Z%).

Payment Affordability Rule: The engine must be able to find a combination of terms and fees that results in a final monthly payment.

4.2. The Search & Concession Hierarchy
This is the core operational logic of the engine.

Global Rule: The engine operates in two distinct phases. It will only enter Phase 2 if Phase 1 yields zero valid offers.

Term Search Order (Fixed): Within each phase, the engine will ALWAYS iterate through loan terms in this specific, commercially-preferred order: 60 -> 72 -> 48 -> 36 -> 24 -> 12 months.

PHASE 1: Max Profit Search (No Subsidy)

The engine iterates through the Term Search Order.

For each term, it attempts to construct an offer with all fees at their maximum value.

If any valid offers are found, the search concludes, and the results from this phase are returned.

PHASE 2: Concession Search (With Subsidy)

The engine iterates through the Term Search Order again.

For each term, it applies a "dial-down" cascade, attempting to find a valid offer at each level before moving to the next.

The Order of Sacrifice:

Reduce Service Fee: (from max down to zero).

Apply CAC Subsidy: Apply a cash bonus to the customer (up to a defined MAX_CAC_BONUS), which increases their effective equity.

Reduce Comisión por Apertura: The final lever. Reducing this fee also increases the customer's effective equity, directly reducing the required loan amount and thus the monthly payment.

4.3. The Levers & Financial Mechanics Explained

vehicle_equity: The starting point. current_car_market_price - current_loan_balance.

Comisión por Apertura (CXA): This is calculated as a percentage of the new_loan_amount (4%). Crucially, this amount is subtracted from the customer's vehicle_equity. This means a higher CXA results in a higher loan amount. Reducing it is a powerful subsidy.

CAC (Customer Bonus): This is a direct cash subsidy. It is added to the customer's vehicle_equity.

Effective Vehicle Equity: The final value used as the down payment in the loan calculation. The formula is: (vehicle_equity + CAC_bonus) - CXA_amount.

new_loan_amount: The amount to be financed. new_car_price - Effective_Vehicle_Equity.

Financed Add-ons (Kavak Total, Insurance): These are fixed amounts (Kavak Total: 25,000 MXN, Insurance: 10,999 MXN) and are financed alongside the main loan.

The Monthly Payment Calculation: The final monthly payment presented to the customer is for the first 12 months. It is the sum of:

The amortized payment for the new_loan_amount over the full loan term (e.g., 60 months).

The amortized payment for the financed Service Fee (5% of car price) over the full loan term.

The amortized payment for the financed Insurance (10,999 MXN) over a fixed 12-month period.

The amortized payment for the financed Kavak Total (25,000 MXN) over the full loan term.

Any other fixed fees (GPS fee: 350 MXN).

All interest and fee components include a 16% IVA tax.

5. Required Data & Integration Points

To function, this engine requires real-time, programmatic access to the following data sources:

Customer Loan Portfolio (The Input):

Source: Redshift (or primary production database).

Data Needed per customer_id: current_loan_balance, current_monthly_payment, current_car_id, risk_profile_name (e.g., 'C1_SB'), and risk_profile_index (e.g., 23).

Vehicle Valuations (The Asset Value):

Source: Kavak's internal pricing engine or table.

Data Needed per car_id: market_price.

Live Sales Inventory (The Product Catalog):

Source: Redshift (or primary inventory database).

Data Needed per inventory_car_id: sales_price, year, model, mileage.

This charter provides a complete, unambiguous definition of the Trade-Up Engine's purpose, design, and logic, serving as the single source of truth for its development and deployment.