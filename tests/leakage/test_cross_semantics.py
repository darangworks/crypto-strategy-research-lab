import pytest

from validation.leakage.strict_cross_semantics import CASES, run_semantics_case


@pytest.mark.parametrize("rsi,expected,desc", CASES)
def test_cross_semantics(rsi, expected, desc):
    result = run_semantics_case(rsi)
    assert result == pytest.approx(expected), (
        f"{desc}: got {result}, expected {expected}"
    )
