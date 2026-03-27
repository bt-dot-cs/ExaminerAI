# Qualified Mortgage — Debt-to-Income Rule

## Source
Dodd-Frank Act Section 1412; CFPB Regulation Z (12 CFR 1026.43)

## Overview
The Qualified Mortgage (QM) rule establishes a safe harbor for lenders by defining underwriting standards that presume a borrower's ability to repay. The DTI threshold is the primary numeric gate.

## Key Thresholds
- Standard QM DTI limit: 43%
- GSE Patch (Fannie/Freddie eligible): 45% with compensating factors
- Compensating factor threshold: credit score ≥ 720 allows up to 45% DTI
- Warning zone: DTI 41–43% requires documented compensating factors even if within limit

## Trigger Conditions
- DTI > 43% AND credit score < 720 → QM violation
- DTI > 45% regardless of credit score → QM violation
- DTI 41–45% with credit score ≥ 720 → warning, document compensating factors

## Agent Decision Logic
```
if loan.dti > 0.45:
    → VIOLATION: exceeds absolute QM ceiling
elif loan.dti > 0.43 and loan.credit_score < 720:
    → VIOLATION: exceeds standard QM threshold without compensating factor eligibility
elif loan.dti > 0.41:
    → WARNING: elevated DTI, document compensating factors
else:
    → PASS
```

## Escalate Conditions
- DTI > 0.43 with borderline credit (680–720): escalate for human review
- Non-QM exception requests: always escalate
- DTI > 0.45: decline without escalation (hard violation)

## Documentation Required
- Debt schedule itemizing all monthly obligations
- Income verification (W-2, tax returns, pay stubs)
- If compensating factors claimed: reserves documentation, residual income calculation
