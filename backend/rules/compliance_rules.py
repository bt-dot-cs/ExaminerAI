"""
Compliance rule engine — Fair Lending, QM, HMDA rules.
Each rule returns: {rule, passed, severity, finding, recommendation}
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class RuleResult:
    rule: str
    passed: bool
    severity: str  # "violation", "warning", "info"
    finding: str
    recommendation: Optional[str] = None


def check_qm_dti(loan: dict, macro: dict) -> RuleResult:
    """Qualified Mortgage DTI threshold (43% standard, 45% with compensating factors)."""
    dti = loan["dti"]
    credit = loan["credit_score"]
    threshold = 0.45 if credit >= 720 else 0.43

    if dti > threshold:
        return RuleResult(
            rule="QM_DTI",
            passed=False,
            severity="violation",
            finding=f"DTI {dti:.0%} exceeds QM threshold of {threshold:.0%} for credit score {credit}",
            recommendation="Decline or document non-QM exception with compensating factors",
        )
    elif dti > 0.41:
        return RuleResult(
            rule="QM_DTI",
            passed=True,
            severity="warning",
            finding=f"DTI {dti:.0%} is elevated — within threshold but warrants documentation",
            recommendation="Document compensating factors in loan file",
        )
    return RuleResult(rule="QM_DTI", passed=True, severity="info", finding=f"DTI {dti:.0%} within QM guidelines")


def check_ltv(loan: dict, macro: dict) -> RuleResult:
    """Loan-to-value ratio check."""
    ltv = loan["loan_amount"] / loan["property_value"]
    if ltv > 0.97:
        return RuleResult(
            rule="LTV",
            passed=False,
            severity="violation",
            finding=f"LTV {ltv:.1%} exceeds maximum 97%",
            recommendation="Require additional down payment or PMI documentation",
        )
    elif ltv > 0.80:
        return RuleResult(
            rule="LTV",
            passed=True,
            severity="warning",
            finding=f"LTV {ltv:.1%} requires PMI",
            recommendation="Confirm PMI is quoted and disclosed",
        )
    return RuleResult(rule="LTV", passed=True, severity="info", finding=f"LTV {ltv:.1%} acceptable")


def check_fair_lending_disparate_treatment(loan: dict, macro: dict) -> RuleResult:
    """
    Flag for potential disparate treatment review.
    Triggers HMDA/ECOA review when protected class + borderline metrics.
    """
    protected_races = {"Black or African American", "Hispanic or Latino", "Asian", "American Indian or Alaska Native"}
    is_protected = loan["race"] in protected_races
    borderline = 0.38 <= loan["dti"] <= 0.46 or 680 <= loan["credit_score"] <= 720

    if is_protected and borderline:
        return RuleResult(
            rule="FAIR_LENDING_DISPARATE_TREATMENT",
            passed=True,
            severity="warning",
            finding=f"Applicant in protected class with borderline metrics — requires comparative file review",
            recommendation="Pull comparable applications from same officer/period for ECOA analysis",
        )
    return RuleResult(
        rule="FAIR_LENDING_DISPARATE_TREATMENT",
        passed=True,
        severity="info",
        finding="No disparate treatment flag triggered",
    )


def check_hmda_reporting(loan: dict, macro: dict) -> RuleResult:
    """Verify HMDA reportable fields are present."""
    required = ["race", "income", "loan_amount", "property_state", "loan_type", "purpose"]
    missing = [f for f in required if not loan.get(f)]
    if missing:
        return RuleResult(
            rule="HMDA_COMPLETENESS",
            passed=False,
            severity="violation",
            finding=f"Missing HMDA required fields: {', '.join(missing)}",
            recommendation="Complete all HMDA LAR fields before submission",
        )
    return RuleResult(rule="HMDA_COMPLETENESS", passed=True, severity="info", finding="All HMDA fields present")


def check_rate_spread(loan: dict, macro: dict) -> RuleResult:
    """HOEPA rate spread check using live FRED mortgage rate."""
    mortgage_rate = macro.get("mortgage_30yr")
    if not mortgage_rate:
        return RuleResult(rule="RATE_SPREAD", passed=True, severity="info", finding="Rate spread check skipped — no live rate available")

    # Jumbo loans often carry a spread; flag if loan amount suggests non-conforming
    conforming_limit = 766550  # 2024 FHFA limit
    if loan["loan_amount"] > conforming_limit:
        return RuleResult(
            rule="RATE_SPREAD",
            passed=True,
            severity="warning",
            finding=f"Non-conforming loan amount ${loan['loan_amount']:,} — verify rate spread against APOR (current 30yr: {mortgage_rate}%)",
            recommendation="Calculate APR and compare to APOR threshold for HOEPA coverage",
        )
    return RuleResult(
        rule="RATE_SPREAD",
        passed=True,
        severity="info",
        finding=f"Loan within conforming limits. Current 30yr rate: {mortgage_rate}%",
    )


ALL_RULES = [
    check_qm_dti,
    check_ltv,
    check_fair_lending_disparate_treatment,
    check_hmda_reporting,
    check_rate_spread,
]


def run_all_rules(loan: dict, macro: dict) -> list[RuleResult]:
    return [rule(loan, macro) for rule in ALL_RULES]
