from hypothesis import given, strategies as st, assume
import pytest
from core.engine import _validate_range, _generate_range

@given(
    start=st.floats(min_value=0, max_value=5),
    end=st.floats(min_value=0, max_value=5),
    step=st.floats(min_value=0.01, max_value=1.0)
)
def test_validate_range(start, end, step):
    if step <= 0 or end < start:
        with pytest.raises(ValueError):
            _validate_range((start, end), step, "test")
    else:
        _validate_range((start, end), step, "test")

@given(
    start=st.floats(min_value=0, max_value=5),
    end=st.floats(min_value=0, max_value=5),
    step=st.floats(min_value=0.01, max_value=1.0)
)
def test_generate_range(start, end, step):
    assume(step > 0)
    assume(end >= start)
    rng = list(_generate_range(start, end, step))
    assert rng[0] == pytest.approx(start)
    assert rng[-1] >= end - step
