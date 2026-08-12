import numpy as np
import pytest

from src.statistics import bootstrap_mean_ci


def test_bootstrap_mean_ci_is_reproducible_and_bounded():
    result_one = bootstrap_mean_ci([1, 2, 3, 4, 5], resamples=500)
    result_two = bootstrap_mean_ci([1, 2, 3, 4, 5], resamples=500)

    assert result_one == result_two
    assert result_one["ci_lower"] <= result_one["mean"] <= result_one["ci_upper"]
    assert 1 <= result_one["ci_lower"] <= 5
    assert 1 <= result_one["ci_upper"] <= 5


def test_bootstrap_rejects_empty_or_invalid_input():
    with pytest.raises(ValueError):
        bootstrap_mean_ci([])
    with pytest.raises(ValueError):
        bootstrap_mean_ci([np.nan])
