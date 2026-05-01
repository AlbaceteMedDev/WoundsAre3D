"""
Monte Carlo uncertainty quantification for volume and surface area.

Given a posterior distribution over the depth field (typically from a
Gaussian process fusion of camera + probe data), this module samples
depth fields from the posterior and computes the resulting distribution
over integrated quantities (volume, surface area).

The posterior can be specified three ways:

1. Pointwise standard deviation (depth_std) - assumes spatial independence.
   Cheap and approximately right for VOLUME uncertainty (volume is a linear
   functional of depth, so independent noise averages out correctly).

   WARNING: Do NOT use pointwise-independent noise for SURFACE AREA
   uncertainty on fine grids. The surface area integrand involves depth
   gradients, which amplify high-frequency noise and produce inflated
   uncertainty estimates. For surface area uncertainty, use option 2 or 3.

2. Correlated noise via length scale (depth_std + correlation_length_cm).
   Generates spatially smooth noise samples by convolving white noise
   with a Gaussian kernel. Cheap (O(n log n) per sample via FFT) and
   represents realistic posterior structure for both volume and surface
   area. Use this when you have a pointwise std estimate but want
   physically realistic spatial correlation.

3. Full covariance matrix (depth_cov) - exact for Gaussian posteriors.
   Required when you have an actual GP posterior with non-stationary or
   anisotropic correlation structure. Costs O(n^3) memory and O(n^2 N)
   time, prohibitive for large grids.

Returns
-------
UncertaintyResult dataclass with mean, std, 95% CI, median, sample count.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from .surface_area import compute_surface_area
from .volume import compute_volume


@dataclass(frozen=True)
class UncertaintyResult:
    """Distribution statistics for a Monte Carlo-estimated quantity.

    All fields are in the same units as the underlying quantity (cm^3 for
    volume, cm^2 for surface area).

    Attributes
    ----------
    mean : float
        Sample mean of the quantity across MC samples.
    std : float
        Sample standard deviation (ddof=1).
    ci_95_low : float
        2.5th percentile of the sample distribution.
    ci_95_high : float
        97.5th percentile of the sample distribution.
    median : float
        50th percentile.
    n_samples : int
        Number of Monte Carlo samples used.
    """

    mean: float
    std: float
    ci_95_low: float
    ci_95_high: float
    median: float
    n_samples: int

    def relative_uncertainty(self) -> float:
        """std / mean, useful for reporting "X% volume uncertainty"."""
        if self.mean == 0:
            return float("inf")
        return self.std / self.mean


def _sample_depth_fields(
    depth_mean: np.ndarray,
    depth_std: Optional[np.ndarray],
    depth_cov: Optional[np.ndarray],
    correlation_length: Optional[float],
    dx: float,
    dy: float,
    n_samples: int,
    rng: np.random.Generator,
    enforce_nonneg: bool = True,
) -> np.ndarray:
    """Generate samples from the depth-field posterior.

    Parameters
    ----------
    depth_mean : np.ndarray
        Posterior mean depth field, 2D.
    depth_std : np.ndarray, optional
        Pointwise standard deviation. If correlation_length is also
        provided, samples are spatially correlated; otherwise independent.
    depth_cov : np.ndarray, optional
        Full covariance matrix. Mutually exclusive with depth_std.
    correlation_length : float, optional
        Spatial correlation length in cm for the Gaussian smoothing kernel.
        If None and depth_std is provided, samples are pointwise independent.
        Recommended values: 0.2 - 1.0 cm for typical wound posteriors.
    dx, dy : float
        Grid spacings (used for correlation_length scaling).
    n_samples : int
        Number of MC samples.
    rng : np.random.Generator
        Random generator.
    enforce_nonneg : bool
        Whether to clip samples at zero.

    Returns
    -------
    samples : np.ndarray, shape (n_samples, Ny, Nx)
    """
    if (depth_std is None) == (depth_cov is None):
        raise ValueError(
            "Provide exactly one of depth_std or depth_cov, not both or neither"
        )

    shape = depth_mean.shape

    if depth_cov is not None:
        flat_mean = depth_mean.ravel()
        n = flat_mean.size
        if depth_cov.shape != (n, n):
            raise ValueError(
                f"depth_cov must have shape ({n}, {n}), got {depth_cov.shape}"
            )
        samples_flat = rng.multivariate_normal(flat_mean, depth_cov, size=n_samples)
        samples = samples_flat.reshape((n_samples,) + shape)
    else:
        # Pointwise std with optional spatial correlation.
        if depth_std.shape != shape:
            raise ValueError(
                f"depth_std shape {depth_std.shape} doesn't match "
                f"depth_mean shape {shape}"
            )
        if np.any(depth_std < 0):
            raise ValueError("depth_std contains negative values")

        if correlation_length is None or correlation_length <= 0:
            # Independent pointwise noise.
            noise = (
                rng.standard_normal(size=(n_samples,) + shape)
                * depth_std[np.newaxis, ...]
            )
        else:
            # Correlated noise via Gaussian smoothing of white noise.
            # The smoothing reduces variance, so we rescale to preserve the
            # specified pointwise std after smoothing.
            from scipy.ndimage import gaussian_filter

            sigma_pix_x = correlation_length / dx
            sigma_pix_y = correlation_length / dy

            white = rng.standard_normal(size=(n_samples,) + shape)
            smoothed = np.empty_like(white)
            for i in range(n_samples):
                smoothed[i] = gaussian_filter(
                    white[i], sigma=(sigma_pix_y, sigma_pix_x), mode="constant"
                )
            # Empirical rescale: gaussian_filter reduces variance by a factor
            # of approximately 1 / (2 sqrt(pi) sigma) per dimension.
            # Compute and rescale to match target pointwise std.
            empirical_std = float(np.std(smoothed))
            if empirical_std > 0:
                smoothed = smoothed / empirical_std  # now unit-variance
            noise = smoothed * depth_std[np.newaxis, ...]

        samples = depth_mean[np.newaxis, ...] + noise

    if enforce_nonneg:
        samples = np.maximum(samples, 0.0)

    return samples


def compute_volume_with_uncertainty(
    depth_mean: np.ndarray,
    dx: float,
    dy: float,
    depth_std: Optional[np.ndarray] = None,
    depth_cov: Optional[np.ndarray] = None,
    correlation_length_cm: Optional[float] = None,
    mask: Optional[np.ndarray] = None,
    n_samples: int = 1000,
    rng: Optional[np.random.Generator] = None,
) -> UncertaintyResult:
    """Wound volume with Monte Carlo uncertainty propagation.

    Parameters
    ----------
    depth_mean : np.ndarray
        Posterior mean depth field, 2D, in cm.
    dx, dy : float
        Grid spacings in cm.
    depth_std : np.ndarray, optional
        Pointwise standard deviation of the depth posterior. Provide this
        OR depth_cov, not both.
    depth_cov : np.ndarray, optional
        Full covariance matrix (Ny*Nx, Ny*Nx) of the depth posterior.
    correlation_length_cm : float, optional
        Spatial correlation length for noise samples when depth_std is used.
        If None, samples are pointwise-independent. For volume, this rarely
        matters (linear functional). Recommended: 0.3-1.0 cm.
    mask : np.ndarray, optional
        Wound footprint mask.
    n_samples : int
        Number of MC samples. Default 1000 is usually sufficient for
        2-sigma confidence in the reported CI.
    rng : np.random.Generator, optional
        Random generator. If None, np.random.default_rng(seed=0) is used
        for reproducibility.
    """
    if rng is None:
        rng = np.random.default_rng(seed=0)

    samples = _sample_depth_fields(
        depth_mean,
        depth_std,
        depth_cov,
        correlation_length_cm,
        dx,
        dy,
        n_samples,
        rng,
        enforce_nonneg=True,
    )

    volumes = np.array(
        [compute_volume(samples[i], dx, dy, mask=mask) for i in range(n_samples)]
    )

    return UncertaintyResult(
        mean=float(np.mean(volumes)),
        std=float(np.std(volumes, ddof=1)),
        ci_95_low=float(np.percentile(volumes, 2.5)),
        ci_95_high=float(np.percentile(volumes, 97.5)),
        median=float(np.median(volumes)),
        n_samples=n_samples,
    )


def compute_surface_area_with_uncertainty(
    depth_mean: np.ndarray,
    dx: float,
    dy: float,
    depth_std: Optional[np.ndarray] = None,
    depth_cov: Optional[np.ndarray] = None,
    correlation_length_cm: Optional[float] = None,
    mask: Optional[np.ndarray] = None,
    n_samples: int = 1000,
    rng: Optional[np.random.Generator] = None,
) -> UncertaintyResult:
    """3D surface area with Monte Carlo uncertainty propagation.

    Same parameters as compute_volume_with_uncertainty.

    IMPORTANT: For surface area uncertainty, you should provide either:
    - depth_cov (full covariance from a GP posterior), or
    - depth_std + correlation_length_cm (typical: 0.3-1.0 cm)

    Pointwise-independent noise (depth_std without correlation_length)
    produces inflated uncertainty estimates because the gradient operator
    in the surface area integrand amplifies high-frequency noise. The
    function will run with independent noise, but the result will not
    represent realistic posterior uncertainty.

    Note: surface area is a nonlinear functional of depth (involves
    gradients), so the posterior over surface area is NOT Gaussian even
    when the depth posterior is. The mean and median may differ
    appreciably; report both.
    """
    if rng is None:
        rng = np.random.default_rng(seed=0)

    if depth_std is not None and correlation_length_cm is None:
        import warnings

        warnings.warn(
            "Computing surface area uncertainty with pointwise-independent "
            "noise will produce inflated uncertainty estimates. Provide "
            "correlation_length_cm (typical: 0.3-1.0) to get realistic "
            "spatially correlated noise.",
            stacklevel=2,
        )

    samples = _sample_depth_fields(
        depth_mean,
        depth_std,
        depth_cov,
        correlation_length_cm,
        dx,
        dy,
        n_samples,
        rng,
        enforce_nonneg=True,
    )

    areas = np.array(
        [
            compute_surface_area(samples[i], dx, dy, mask=mask)
            for i in range(n_samples)
        ]
    )

    return UncertaintyResult(
        mean=float(np.mean(areas)),
        std=float(np.std(areas, ddof=1)),
        ci_95_low=float(np.percentile(areas, 2.5)),
        ci_95_high=float(np.percentile(areas, 97.5)),
        median=float(np.median(areas)),
        n_samples=n_samples,
    )
