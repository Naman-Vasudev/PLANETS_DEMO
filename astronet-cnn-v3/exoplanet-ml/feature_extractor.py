"""
feature_extractor.py — Advanced Astrophysical Feature Extraction

Extracts a comprehensive set of astrophysical features from a light curve
after BLS transit detection. These features are used downstream by the
rule-assisted heuristic classifier initialized using astrophysical priors.

All features are printed to stdout in the format:
   FE <key>: <value>
so that server.py can parse them via regex.
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


def _phase_fold(time: np.ndarray, period: float, t0: float) -> np.ndarray:
    """Fold time array onto the interval [-0.5, 0.5] * period."""
    phase = (time - t0 + 0.5 * period) % period - 0.5 * period
    return phase


def compute_transit_depth(
        flux: np.ndarray, phase: np.ndarray, duration: float
) -> tuple[float, float, float]:
    """
    Compute fractional transit depth = (F_out - F_in) / F_out.

    Returns:
        depth: Fractional depth.
        mean_in: Mean in-transit flux.
        mean_out: Mean out-of-transit flux.
    """
    in_transit = np.abs(phase) < (duration / 2.0)
    flux_in = flux[in_transit]
    flux_out = flux[~in_transit]
    if len(flux_in) == 0 or len(flux_out) == 0:
        return 0.0, 1.0, 1.0
    mean_in = float(np.mean(flux_in))
    mean_out = float(np.mean(flux_out))
    if mean_out <= 0:
        return 0.0, mean_in, mean_out
    depth = (mean_out - mean_in) / mean_out
    return max(0.0, depth), mean_in, mean_out


def compute_snr(
        flux: np.ndarray, phase: np.ndarray, duration: float
) -> float:
    """
    Compute transit Signal-to-Noise Ratio.

    SNR = depth / sigma_out * sqrt(N_in)
    """
    in_transit = np.abs(phase) < (duration / 2.0)
    flux_in = flux[in_transit]
    flux_out = flux[~in_transit]
    if len(flux_in) == 0 or len(flux_out) == 0:
        return 0.0
    mean_in = np.mean(flux_in)
    mean_out = np.mean(flux_out)
    depth = mean_out - mean_in
    std_out = np.std(flux_out)
    if std_out <= 0:
        return 0.0
    return float((depth / std_out) * np.sqrt(len(flux_in)))


def compute_odd_even_depth_difference(
        time: np.ndarray, flux: np.ndarray,
        period: float, t0: float, duration: float
) -> float:
    """
    Compute the difference in transit depth between odd and even transit events.

    A large odd-even depth difference is a strong indicator of an eclipsing binary,
    where alternate eclipses differ in depth because of the two stellar components.

    Returns:
        Absolute difference in depth between odd and even transits (0 if undetermined).
    """
    # Assign each in-transit point to a transit number
    phase = _phase_fold(time, period, t0)
    in_transit = np.abs(phase) < (duration / 2.0)
    times_in = time[in_transit]
    flux_in = flux[in_transit]

    if len(times_in) < 4:
        return 0.0

    # Determine transit number for each point
    transit_numbers = np.round((times_in - t0) / period).astype(int)
    odd_depths = []
    even_depths = []
    out_of_transit = flux[~in_transit]
    mean_out = float(np.mean(out_of_transit)) if len(out_of_transit) > 0 else 1.0

    for tnum in np.unique(transit_numbers):
        mask = transit_numbers == tnum
        mean_in_t = float(np.mean(flux_in[mask]))
        depth_t = (mean_out - mean_in_t) / mean_out if mean_out > 0 else 0.0
        if tnum % 2 == 0:
            even_depths.append(depth_t)
        else:
            odd_depths.append(depth_t)

    if len(odd_depths) == 0 or len(even_depths) == 0:
        return 0.0

    return float(abs(np.mean(odd_depths) - np.mean(even_depths)))


def compute_secondary_eclipse_strength(
        flux: np.ndarray, phase: np.ndarray,
        period: float, duration: float
) -> float:
    """
    Search for a secondary eclipse near phase 0.5 (half-period).

    The presence of a secondary eclipse strongly suggests an eclipsing binary
    rather than a planetary transit, as planets do not produce symmetric depth dips.

    Returns:
        Fractional depth of any secondary dip detected near phase 0.5.
    """
    # Secondary eclipse is near phase +/- 0.5 * period
    secondary_mask = (
        (np.abs(phase) > (0.5 * period - 2.0 * duration)) &
        (np.abs(phase) < (0.5 * period + 2.0 * duration))
    )
    primary_mask = np.abs(phase) < (duration / 2.0)
    out_mask = ~primary_mask & ~secondary_mask

    flux_secondary = flux[secondary_mask]
    flux_out = flux[out_mask]

    if len(flux_secondary) < 2 or len(flux_out) < 2:
        return 0.0

    mean_sec = float(np.mean(flux_secondary))
    mean_out = float(np.mean(flux_out))
    if mean_out <= 0:
        return 0.0
    depth_sec = (mean_out - mean_sec) / mean_out
    return max(0.0, float(depth_sec))


def compute_transit_shape_score(
        flux: np.ndarray, phase: np.ndarray, duration: float
) -> float:
    """
    Estimate the U-vs-V shape of the transit profile.

    Shape score = bottom_width / total_transit_width.
    A score near 1.0 indicates a flat-bottomed U-shape (planetary transit).
    A score near 0.0 indicates a V-shaped profile (eclipsing binary).

    The flat bottom is identified as the fraction of in-transit points within
    10% of the minimum flux level.

    Returns:
        Shape score in [0, 1].
    """
    in_transit = np.abs(phase) < (duration / 2.0)
    flux_in = flux[in_transit]

    if len(flux_in) < 4:
        return 0.5  # Indeterminate

    flux_min = np.min(flux_in)
    flux_range = np.max(flux_in) - flux_min
    if flux_range < 1e-8:
        return 1.0  # Perfectly flat

    # Flat bottom: within 10% of the total range from the minimum
    flat_threshold = flux_min + 0.1 * flux_range
    n_flat = np.sum(flux_in <= flat_threshold)
    shape_score = float(n_flat) / float(len(flux_in))
    return float(np.clip(shape_score, 0.0, 1.0))


def compute_transit_symmetry(
        flux: np.ndarray, phase: np.ndarray, duration: float
) -> float:
    """
    Measure the ingress-egress symmetry of the transit.

    Symmetric transits (score near 1.0) are expected for both planets and eclipsing
    binaries. Asymmetric transits (score near 0.0) may indicate contamination or blends.

    Returns:
        Symmetry score in [0, 1].
    """
    in_transit_mask = np.abs(phase) < (duration / 2.0)
    phase_in = phase[in_transit_mask]
    flux_in = flux[in_transit_mask]

    if len(phase_in) < 4:
        return 0.5

    ingress_mask = phase_in < 0
    egress_mask = phase_in > 0

    ingress_flux = flux_in[ingress_mask]
    egress_flux = flux_in[egress_mask]

    if len(ingress_flux) < 2 or len(egress_flux) < 2:
        return 0.5

    # Compare slopes: diff from minimum to edge
    flux_min = np.min(flux_in)
    ingress_slope = (np.mean(ingress_flux) - flux_min) / (duration / 2.0)
    egress_slope = (np.mean(egress_flux) - flux_min) / (duration / 2.0)

    max_slope = max(abs(ingress_slope), abs(egress_slope), 1e-8)
    diff = abs(ingress_slope - egress_slope) / max_slope
    symmetry = float(np.clip(1.0 - diff, 0.0, 1.0))
    return symmetry


def compute_n_transits(
        time: np.ndarray, period: float, t0: float, duration: float
) -> int:
    """
    Count the number of observed transit events in the light curve.

    Args:
        time: Full time array.
        period: Detected orbital period in days.
        t0: Transit epoch in days.
        duration: Transit duration in days.

    Returns:
        Integer count of distinct transit events observed.
    """
    phase = _phase_fold(time, period, t0)
    in_transit = np.abs(phase) < (duration / 2.0)
    times_in = time[in_transit]

    if len(times_in) == 0:
        return 0

    transit_numbers = set(np.round((times_in - t0) / period).astype(int).tolist())
    return len(transit_numbers)


def compute_depth_uncertainty(
        flux: np.ndarray, phase: np.ndarray,
        duration: float, n_bootstrap: int = 200
) -> float:
    """
    Estimate uncertainty in transit depth via bootstrap resampling.

    Args:
        flux: Normalised flux array.
        phase: Phase array.
        duration: Transit duration in days.
        n_bootstrap: Number of bootstrap iterations.

    Returns:
        Standard deviation of bootstrap depth estimates.
    """
    in_transit = np.abs(phase) < (duration / 2.0)
    flux_in = flux[in_transit]
    flux_out = flux[~in_transit]

    if len(flux_in) < 3 or len(flux_out) < 3:
        return 0.0

    depths = []
    rng = np.random.default_rng(42)
    for _ in range(n_bootstrap):
        sample_in = rng.choice(flux_in, size=len(flux_in), replace=True)
        sample_out = rng.choice(flux_out, size=min(len(flux_out), 500), replace=True)
        mean_out = np.mean(sample_out)
        mean_in = np.mean(sample_in)
        if mean_out > 0:
            depths.append((mean_out - mean_in) / mean_out)

    return float(np.std(depths)) if depths else 0.0


def extract_features(
        time: np.ndarray,
        flux: np.ndarray,
        period: float,
        t0: float,
        duration: float,
        n_bootstrap: int = 200
) -> dict:
    """
    Run the full feature extraction pipeline for a detected transit signal.

    Args:
        time: Cleaned time array (days).
        flux: Normalised, detrended flux array.
        period: BLS-detected orbital period (days).
        t0: Transit epoch (days).
        duration: Transit duration (days).
        n_bootstrap: Bootstrap iterations for uncertainty estimates.

    Returns:
        Dictionary of extracted feature names to float values.
    """
    print('⚙️  Extracting astrophysical features...')
    phase = _phase_fold(time, period, t0)

    depth, mean_in, mean_out = compute_transit_depth(flux, phase, duration)
    snr = compute_snr(flux, phase, duration)
    odd_even_diff = compute_odd_even_depth_difference(time, flux, period, t0, duration)
    secondary_strength = compute_secondary_eclipse_strength(flux, phase, period, duration)
    shape_score = compute_transit_shape_score(flux, phase, duration)
    symmetry = compute_transit_symmetry(flux, phase, duration)
    n_transits = compute_n_transits(time, period, t0, duration)
    depth_unc = compute_depth_uncertainty(flux, phase, duration, n_bootstrap)

    features = {
        'transit_depth':              round(depth, 8),
        'snr':                        round(snr, 4),
        'orbital_period':             round(period, 6),
        'transit_duration_hours':     round(duration * 24.0, 4),
        'n_transits':                 n_transits,
        'odd_even_diff':              round(odd_even_diff, 6),
        'secondary_eclipse_strength': round(secondary_strength, 6),
        'transit_shape_score':        round(shape_score, 4),
        'transit_symmetry':           round(symmetry, 4),
        'depth_uncertainty':          round(depth_unc, 8),
    }

    print('✅ Feature extraction complete:')
    for key, val in features.items():
        print(f'   FE {key}: {val}')

    return features


if __name__ == '__main__':
    # Standalone unit test with a synthetic light curve
    rng = np.random.default_rng(0)
    t = np.linspace(0, 27, 2000)
    f = np.ones_like(t)
    # Inject a simulated transit every 5 days, depth 1%
    period_test = 5.0
    t0_test = 1.0
    dur_test = 0.1
    phase_test = _phase_fold(t, period_test, t0_test)
    f[np.abs(phase_test) < (dur_test / 2.0)] -= 0.01
    f += rng.normal(0, 0.001, len(f))
    features = extract_features(t, f, period_test, t0_test, dur_test)
    print('\nStandalone test passed.')
