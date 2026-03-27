# HMDA — Home Mortgage Disclosure Act Reporting

## Source
Home Mortgage Disclosure Act (12 U.S.C. 2801); Regulation C (12 CFR 1003)

## Overview
HMDA requires covered institutions to collect, record, and report data about mortgage applications and originations. The data is used by regulators to identify potential fair lending violations and assess whether institutions are serving community credit needs.

## Key Thresholds
- Reporting threshold: institutions with assets > $56M (2024) in MSAs must report
- LAR submission deadline: March 1 of the following calendar year
- Resubmission threshold: error rate > 0.05% of records triggers mandatory resubmission

## Required LAR Fields
- Application date
- Loan type (Conventional, FHA, VA, USDA)
- Loan purpose (Purchase, Refinance, Home Improvement, Other)
- Owner occupancy
- Loan amount
- Action taken (originated, approved not accepted, denied, withdrawn, incomplete)
- Property location (state, county, census tract)
- Applicant race, ethnicity, sex
- Applicant income
- Rate spread (if applicable)
- HOEPA status
- Lien status

## Trigger Conditions
- Any required LAR field missing → HMDA_COMPLETENESS violation
- Race/ethnicity field blank without "information not provided" notation → violation
- Loan amount inconsistent with property value (LTV > 100%) → data quality flag

## Agent Decision Logic
```
required_fields = [race, income, loan_amount, property_state, loan_type, purpose]
missing = [f for f in required_fields if not loan.get(f)]
if missing:
    → VIOLATION: cannot process without complete HMDA fields
```

## Escalate Conditions
- Missing demographic fields: escalate for data collection before processing
- Census tract not determinable: escalate for geocoding

## Documentation Required
- Complete LAR record for every covered application
- Geocoding documentation for property location
- Demographic information collection notice provided to applicant
