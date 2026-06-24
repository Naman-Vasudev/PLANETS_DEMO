"""
detrending.py — Light Curve Noise Reduction Utilities

Provides three detrending methods that can be applied before BLS transit search:
  1. Sigma-clipping outlier rejection
  2. Running median detrending
  3. Savitzky-Golay polynomial smoothing

All methods are applied in sequence via detrend_lightcurve().
Returns cleaned time and flux arrays.
"""

import os
import sys
import io
import numpy as np

# Force UTF-8 encoding for standard streams to prevent Unicode errors on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

try:
    from scipy.signal import savgol_filter
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    print('⚠️  scipy not available; Savitzky-Golay detrending disabled.')


def sigma_clip(time: np.ndarray, flux: np.ndarray,
               sigma: float = 3.0,
               max_iterations: int = 5) -> tuple[np.ndarray, np.ndarray]:
    """
    Iteratively remove flux outliers beyond sigma standard deviations.

    Args:
        time: Time array.
        flux: Normalised flux array.
        sigma: Clipping threshold in units of standard deviation.
        max_iterations: Maximum number of sigma-clipping passes.

    Returns:
        Cleaned (time, flux) arrays.
    """
    mask = np.ones(len(flux), dtype=bool)
    for _ in range(max_iterations):
        median = np.median(flux[mask])
        std = np.std(flux[mask])
        new_mask = np.abs(flux - median) < sigma * std
        if np.sum(new_mask) == np.sum(mask):
            break
        mask = new_mask
    n_removed = len(flux) - np.sum(mask)
    if n_removed > 0:
        print(f'   Sigma-clipping removed {n_removed} outlier points ({sigma}σ threshold).')
    return time[mask], flux[mask]


def running_median_detrend(time: np.ndarray, flux: np.ndarray,
                           window_size: int = 101) -> np.ndarray:
    """
    Remove long-timescale stellar variability using a running median filter.

    Divides the flux by a sliding median to produce a flat out-of-transit baseline.

    Args:
        time: Time array.
        flux: Normalised flux array.
        window_size: Number of cadences in the sliding window (must be odd).

    Returns:
        Detrended flux array.
    """
    if window_size % 2 == 0:
        window_size += 1
    half = window_size // 2
    detrended = np.empty_like(flux)
    n = len(flux)
    for i in range(n):
        lo = max(0, i - half)
        hi = min(n, i + half + 1)
        detrended[i] = flux[i] / np.median(flux[lo:hi])
    return detrended


def savitzky_golay_detrend(flux: np.ndarray,
                           window_length: int = 51,
                           polyorder: int = 3) -> np.ndarray:
    """
    Apply Savitzky-Golay smoothing to remove broad stellar variability trends.

    Args:
        flux: Normalised flux array.
        window_length: Length of the filter window (must be odd).
        polyorder: Polynomial order for the SG filter.

    Returns:
        Detrended flux array (flux divided by SG trend).
    """
    if not SCIPY_AVAILABLE:
        return flux
    if window_length % 2 == 0:
        window_length += 1
    # Ensure window is not longer than the data
    window_length = min(window_length, len(flux) if len(flux) % 2 != 0 else len(flux) - 1)
    trend = savgol_filter(flux, window_length=window_length, polyorder=polyorder)
    # Avoid division by zero
    trend = np.where(np.abs(trend) < 1e-10, 1.0, trend)
    return flux / trend


def detrend_lightcurve(
        time: np.ndarray,
        flux: np.ndarray,
        apply_sigma_clip: bool = True,
        apply_running_median: bool = True,
        apply_savgol: bool = True,
        sigma: float = 3.0,
        median_window: int = 101,
        savgol_window: int = 51
) -> tuple[np.ndarray, np.ndarray]:
    """
    Apply the full detrending pipeline to a light curve.

    Steps applied in order:
      1. Sigma-clipping outlier rejection
      2. Running median detrending
      3. Savitzky-Golay polynomial filter

    Args:
        time: Time array.
        flux: Normalised flux array.
        apply_sigma_clip: Whether to apply sigma-clipping.
        apply_running_median: Whether to apply running median detrending.
        apply_savgol: Whether to apply Savitzky-Golay filter.
        sigma: Sigma-clipping threshold.
        median_window: Window size for running median.
        savgol_window: Window size for Savitzky-Golay filter.

    Returns:
        Cleaned (time, flux) tuple.
    """
    print('⚙️  Applying light curve detrending...')
    n_original = len(flux)

    if apply_sigma_clip:
        time, flux = sigma_clip(time, flux, sigma=sigma)

    if apply_running_median and len(flux) >= median_window:
        flux = running_median_detrend(time, flux, window_size=median_window)

    if apply_savgol and SCIPY_AVAILABLE:
        flux = savitzky_golay_detrend(flux, window_length=savgol_window)

    # Re-normalise after detrending
    median_flux = np.median(flux)
    if median_flux > 0:
        flux = flux / median_flux

    print(f'   Detrending complete. Retained {len(flux)}/{n_original} data points.')
    return time, flux
