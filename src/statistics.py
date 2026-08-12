"""Uncertainty estimates for benchmark score summaries."""

from __future__ import annotations

import numpy as np


def bootstrap_mean_ci(
    values: list[float] | np.ndarray,
    confidence: float = 0.95,
    resamples: int = 2000,
    seed: int = 42,
) -> dict[str, float | int]:
    """Estimate a percentile bootstrap CI for a sample mean."""
    sample = np.asarray(values, dtype=float)
    sample = sample[np.isfinite(sample)]
    if sample.size == 0:
        raise ValueError("At least one finite score is required")
    if not 0 < confidence < 1:
        raise ValueError("confidence must be between 0 and 1")
    if resamples < 100:
        raise ValueError("resamples must be at least 100")

    rng = np.random.default_rng(seed)
    indices = rng.integers(0, sample.size, size=(resamples, sample.size))
    means = sample[indices].mean(axis=1)
    alpha = (1 - confidence) / 2
    lower, upper = np.quantile(means, [alpha, 1 - alpha])
    return {
        "n": int(sample.size),
        "mean": round(float(sample.mean()), 4),
        "ci_lower": round(float(lower), 4),
        "ci_upper": round(float(upper), 4),
        "confidence": confidence,
    }
