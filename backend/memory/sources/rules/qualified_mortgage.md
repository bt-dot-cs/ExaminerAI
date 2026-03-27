# Qualified Mortgage (QM) — Ability to Repay Rule

## Governing Statute
Dodd-Frank Act § 1412; CFPB Regulation Z (12 CFR § 1026.43)

## Ability to Repay (ATR) Requirement
Lenders must make a reasonable, good-faith determination that the borrower can repay the loan.
ATR analysis must consider: income, assets, employment, credit history, monthly payment, simultaneous loans, mortgage-related obligations, other debt obligations, DTI, residual income.

## Qualified Mortgage Safe Harbor
Loans meeting QM standards receive a legal presumption of ATR compliance.

### QM DTI Thresholds
- Standard QM: DTI ≤ 43%
- QM with compensating factors: DTI ≤ 45% if credit score ≥ 720
- High-balance QM (FHFA conforming limit applies): same thresholds

### Compensating Factors Recognized
- Credit score ≥ 720
- Documented liquid reserves ≥ 12 months PITI
- Residual income above FHA residual income guidelines
- LTV ≤ 80%

## Agent Decision Logic
```
IF dti > 0.45:
    RESULT: QM_VIOLATION — decline or require documented non-QM exception
IF 0.43 < dti <= 0.45 AND credit_score < 720:
    RESULT: QM_VIOLATION — DTI exceeds threshold without compensating factor
IF 0.43 < dti <= 0.45 AND credit_score >= 720:
    RESULT: QM_WARNING — within threshold via compensating factor, document
IF 0.41 < dti <= 0.43:
    RESULT: QM_WARNING — elevated, within threshold, document compensating factors
IF dti <= 0.41:
    RESULT: QM_PASS
```

## Non-QM Loans
Lenders may originate non-QM loans but must document ATR compliance without safe harbor.
Non-QM loans carry greater regulatory and litigation risk. Flag for senior underwriter review.

## Points and Fees Test (QM Eligibility)
Total points and fees ≤ 3% of total loan amount (for loans ≥ $100,000).
Agent does not currently check this — requires fee schedule data not in application file.

## Documentation Requirements
- Income verification: W-2s, tax returns (2 years), pay stubs (30 days)
- Asset verification: bank statements (2 months)
- Employment verification: VOE or equivalent
- All compensating factors must be documented in the loan file
