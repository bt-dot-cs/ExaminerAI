# Loan-to-Value (LTV) Limits

## Definition
LTV = Loan Amount / Appraised Property Value (or purchase price, whichever is lower)

## Maximum LTV by Loan Type

### Conventional (Fannie Mae / Freddie Mac)
- Primary residence, purchase: 97% (with PMI and credit score ≥ 620)
- Primary residence, refinance: 97% (rate/term); 80% (cash-out)
- Second home: 90%
- Investment property: 85% (purchase); 75% (cash-out refinance)

### FHA
- Credit score ≥ 580: 96.5% LTV
- Credit score 500–579: 90% LTV
- Credit score < 500: Not eligible

### VA
- No maximum LTV for eligible veterans (entitlement covers the guarantee)
- No PMI required regardless of LTV

### USDA
- Up to 100% (no down payment required in eligible rural areas)

## PMI Trigger
Conventional loans with LTV > 80% require Private Mortgage Insurance (PMI).
PMI must be disclosed in the Loan Estimate and Closing Disclosure.
PMI cancels automatically when LTV reaches 78% based on original amortization schedule (HPA 1998).

## CLTV (Combined LTV)
CLTV = (First Mortgage + All Subordinate Liens) / Appraised Value
CLTV limits apply when borrower has simultaneous second mortgage or HELOC.

## Agent Decision Logic
```
ltv = loan_amount / property_value
IF ltv > 0.97:
    RESULT: LTV_VIOLATION — exceeds maximum 97%; require additional down payment
IF 0.80 < ltv <= 0.97:
    RESULT: LTV_WARNING — PMI required; confirm quoted and disclosed
IF ltv <= 0.80:
    RESULT: LTV_PASS — no PMI required
```

## Documentation Requirements
- Certified appraisal from state-licensed appraiser (required for all conventional loans)
- PMI commitment letter if LTV > 80%
- For FHA: FHA-approved appraiser required
