# LTV Limits & HOEPA Rate Spread

## Source
HOEPA: 15 U.S.C. 1639; Regulation Z Section 1026.32
LTV: FHFA conforming loan limits; FHA guidelines; Fannie Mae Selling Guide

## Overview
Loan-to-value ratio governs collateral adequacy and PMI requirements. HOEPA (Home Ownership and Equity Protection Act) establishes rate spread thresholds above which loans are classified as high-cost and subject to additional restrictions.

## Key Thresholds — LTV
- Maximum LTV (conventional): 97%
- PMI required: LTV > 80%
- Jumbo/non-conforming: typically max 80–90% LTV
- 2024 FHFA conforming loan limit: $766,550 (baseline); $1,149,825 (high-cost areas)

## Key Thresholds — HOEPA Rate Spread
- High-cost mortgage trigger (first lien): APR exceeds APOR by 6.5 percentage points
- High-cost mortgage trigger (second lien): APR exceeds APOR by 8.5 percentage points
- Points and fees trigger: > 5% of total loan amount (or $1,148 for small loans)

## Trigger Conditions
- LTV > 97%: hard violation, loan cannot close
- LTV > 80%: PMI disclosure required
- Loan amount > $766,550: non-conforming, verify rate spread against APOR
- Estimated APR - current APOR > 6.5%: HOEPA high-cost classification

## Agent Decision Logic
```
ltv = loan.loan_amount / loan.property_value
if ltv > 0.97:
    → VIOLATION: exceeds maximum LTV
elif ltv > 0.80:
    → WARNING: PMI required, confirm disclosure

if loan.loan_amount > 766550:
    → WARNING: non-conforming, calculate rate spread vs APOR
    → Use live FRED MORTGAGE30US as APOR proxy for screening
```

## Escalate Conditions
- LTV > 97%: decline, no escalation needed
- Estimated HOEPA trigger: escalate for full APR calculation before proceeding
- Non-conforming loans with rate spread near threshold: escalate

## Documentation Required
- Appraisal or AVM supporting property value
- PMI quote and disclosure if LTV > 80%
- APR calculation worksheet for non-conforming loans
- HOEPA disclosure if high-cost classification applies (3 business days before closing)
