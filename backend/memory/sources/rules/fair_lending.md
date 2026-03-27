# Fair Lending — Disparate Treatment & ECOA

## Source
Equal Credit Opportunity Act (ECOA, 15 U.S.C. 1691); Fair Housing Act (42 U.S.C. 3605); Regulation B (12 CFR 202)

## Overview
Fair lending law prohibits discrimination in credit decisions based on race, color, religion, national origin, sex, marital status, age, or receipt of public assistance. Disparate treatment occurs when similarly situated applicants are treated differently based on a protected characteristic.

## Protected Classes
Race, Color, National Origin, Sex, Religion, Marital Status, Age, Receipt of Public Income

## Key Thresholds
- No numeric threshold — disparate treatment is comparative, not absolute
- Comparative file review required when: protected class applicant + borderline metrics + same loan officer
- HMDA peer analysis trigger: approval rate differential > 10 percentage points by race/ethnicity

## Trigger Conditions
- Applicant in protected class AND DTI 38–46% AND same officer as non-protected applicant with similar profile
- Applicant in protected class AND credit score 680–720 AND loan denied or escalated
- Two applications with near-identical financials but different race outcomes → mandatory comparative review

## Agent Decision Logic
```
protected_races = {Black or African American, Hispanic or Latino, Asian,
                   American Indian or Alaska Native, Native Hawaiian}

if loan.race in protected_races:
    if 0.38 <= loan.dti <= 0.46 or 680 <= loan.credit_score <= 720:
        → WARNING: pull comparable files from same officer/period
        → ESCALATE: do not auto-decide borderline protected class cases
```

## Escalate Conditions
- Any borderline case involving a protected class applicant: always escalate
- Cases where a comparable non-protected applicant received different treatment: always escalate
- Novel fact patterns with protected class involvement: sticky HITL, never graduate

## Documentation Required
- Comparative file analysis (same officer, same period, similar DTI/credit)
- Written explanation of any differential treatment
- HMDA LAR entry with all required demographic fields
- If declined: adverse action notice within 30 days (ECOA requirement)
