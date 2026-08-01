

# --- An unfilled remediation must not read as "none needed" -------------------


class _Finding:
    def __init__(self, severity, remediation=None):
        self.severity = severity
        self.raw_record = {"remediation_requirement": remediation}


def test_a_blocking_finding_without_a_plan_says_so():
    """It used to read "No remediation required." two lines under an Impact line
    saying a remediation plan was required. On a rejection those are opposite
    claims, and a reader skimming would take the finding as already handled."""
    from board.cli import _fix_line

    for severity in ("SEV-1", "SEV-2"):
        line = _fix_line(_Finding(severity))
        assert "NOT SPECIFIED" in line
        assert "No remediation required" not in line


def test_a_non_blocking_finding_without_a_plan_needs_none():
    from board.cli import _fix_line

    assert _fix_line(_Finding("SEV-3")) == "No remediation required."
    assert _fix_line(_Finding("SEV-4")) == "No remediation required."


def test_a_stated_remediation_is_shown_verbatim_at_every_severity():
    from board.cli import _fix_line

    for severity in ("SEV-1", "SEV-2", "SEV-3", "SEV-4"):
        assert _fix_line(_Finding(severity, "Obtain a second corroborating case.")) == (
            "Obtain a second corroborating case."
        )


def test_whitespace_is_not_a_remediation_plan():
    from board.cli import _fix_line

    assert "NOT SPECIFIED" in _fix_line(_Finding("SEV-2", "   "))
