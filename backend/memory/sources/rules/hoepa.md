# HOEPA — High-Cost Mortgage Rules

## Governing Statute
Home Ownership and Equity Protection Act (HOEPA), 15 U.S.C. § 1639; CFPB Regulation Z (12 CFR § 1026.32)

## What Is a High-Cost Mortgage
A closed-end consumer credit transaction secured by the consumer's principal dwelling that meets ANY of the following thresholds:

### Rate Spread Trigger (vs. Average Prime Offer Rate — APOR)
APOR is published weekly by the CFPB based on Freddie Mac PMMS survey data.
- First lien: APR exceeds APOR by more than **6.5 percentage points**
- Subordinate lien: APR exceeds APOR by more than **8.5 percentage points**
- Personal property secured: APR exceeds APOR by more than **6.5 percentage points**

### Points and Fees Trigger
Total points and fees exceed:
- **5%** of the total loan amount for loans ≥ $24,866 (2024 threshold, adjusted annually)
- The lesser of 8% or $1,243 for loans < $24,866 (2024)

### Prepayment Penalty Trigger
Prepayment penalty that can be charged more than 36 months after consummation, OR
Prepayment penalty that exceeds 2% of the prepaid amount.

## Conforming Loan Limit (FHFA 2024)
$766,550 for single-family properties in standard areas.
High-cost areas: up to $1,149,825.
Non-conforming (jumbo) loans exceed these limits.

## Agent Rate Spread Check Logic
```
IF loan_amount > 766550:  # Non-conforming
    Flag: "Non-conforming loan — verify rate spread against current APOR"
    Note current 30yr rate from FRED (live)
    Recommendation: "Calculate APR and compare to APOR + 6.5% threshold"
ELSE:
    Conforming loan — standard HOEPA exposure is low; no flag
```

Note: Agent cannot compute APR directly (requires origination fee data). Flag for manual rate spread verification on non-conforming loans.

## HOEPA Prohibitions on High-Cost Mortgages
If a loan is classified as high-cost:
- No balloon payments (term < 5 years)
- No negative amortization
- No prepayment penalties (with limited exceptions)
- No advance payments from loan proceeds
- No increased interest rate after default
- No financing of points, fees, or credit insurance premiums
- Additional disclosures required 3 business days before consummation (HOEPA notice)
- Homeownership counseling required

## Penalties for HOEPA Violations
- Rescission rights for borrower (up to 3 years post-consummation for material violations)
- Civil liability: actual damages + statutory damages up to $4,000 per violation
- Assignee liability if violation apparent on face of documents
