import os
import sys
import io

# Force UTF-8 encoding for standard streams to prevent Unicode errors on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import subprocess
import numpy as np
from lightkurve import search_lightcurve, search_lightcurvefile
from astropy.io import fits
from astropy.timeseries import BoxLeastSquares
import matplotlib.pyplot as plt

# Base directory = location of the current script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_DIR = os.environ.get("MODEL_DIR", os.path.join(BASE_DIR, "MODEL_DIR"))
TESS_DATA_DIR = os.environ.get("TESS_DATA_DIR", os.path.join(BASE_DIR, "KEPLER_DATA_DIR"))
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", os.path.join(BASE_DIR, "kepler_pictures"))

# Import new pipeline modules (graceful fallback if unavailable)
try:
    from detrending import detrend_lightcurve
    DETRENDING_AVAILABLE = True
except ImportError:
    DETRENDING_AVAILABLE = False

try:
    from feature_extractor import extract_features
    FEATURE_EXTRACTION_AVAILABLE = True
except ImportError:
    FEATURE_EXTRACTION_AVAILABLE = False

# ----------------------------
# LIGHT CURVE DOWNLOAD AND PARAMETER CALCULATION
# ----------------------------
def analyze_tess_lightcurve(tic_id: str, period_override: float = None, t0_override: float = None, duration_override: float = None):
    """Download TESS light curve, apply detrending, run BLS, and extract features."""
    print(f"🔍 Searching for light curve for TIC {tic_id}...")
    results = search_lightcurve(f"TIC {tic_id}", mission="TESS")

    if len(results) == 0:
        raise ValueError("No observations found for this TIC.")

    lc = results[0].download().remove_nans().normalize()
    time = np.asarray(lc.time.value, dtype=np.float64)
    flux = np.asarray(lc.flux.value if hasattr(lc.flux, "value") else lc.flux, dtype=np.float64)

    if len(time) < 100:
        raise ValueError("Too few valid data points for BLS analysis.")

    # Stage 1: Apply detrending before BLS to improve transit sensitivity
    if DETRENDING_AVAILABLE:
        time, flux = detrend_lightcurve(time, flux)
    else:
        print("⚠️  Detrending module unavailable — using raw normalised light curve.")

    print("⚙️  Running Box Least Squares analysis...")
    periods = np.linspace(0.5, 30, 20000)
    bls = BoxLeastSquares(time, flux)
    bls_result = bls.power(periods, 0.1)

    if period_override is not None:
        period = period_override
        t0 = t0_override
        duration = duration_override
        print(f"   [OVERRIDE] Using user-defined parameters: P={period}, T0={t0}, Dur={duration}")
    else:
        best = np.argmax(bls_result.power)
        period = float(bls_result.period[best].value) if hasattr(bls_result.period[best], "value") else float(bls_result.period[best])
        t0 = float(bls_result.transit_time[best].value) if hasattr(bls_result.transit_time[best], "value") else float(bls_result.transit_time[best])
        duration = float(bls_result.duration[best].value) if hasattr(bls_result.duration[best], "value") else float(bls_result.duration[best])

    # Calculate Signal-to-Noise Ratio (SNR) of the transit
    phase = (time - t0 + 0.5 * period) % period - 0.5 * period
    in_transit = np.abs(phase) < (duration / 2.0)
    flux_in = flux[in_transit]
    flux_out = flux[~in_transit]
    if len(flux_in) > 0 and len(flux_out) > 0:
        mean_in = np.mean(flux_in)
        mean_out = np.mean(flux_out)
        depth = mean_out - mean_in
        std_out = np.std(flux_out)
        if std_out > 0:
            snr = (depth / std_out) * np.sqrt(len(flux_in))
        else:
            snr = 0.0
    else:
        depth = 0.0
        snr = 0.0

    print(f"✅ Estimated parameters for TIC {tic_id}:")
    print(f"   Period  : {period:.5f} days")
    print(f"   T0      : {t0:.5f}")
    print(f"   Duration: {duration*24:.2f} hours")
    print(f"   BLS SNR : {snr:.2f}")
    print(f"   BLS Depth: {depth:.6f}")

    # Stage 2: Advanced feature extraction after BLS detection
    if FEATURE_EXTRACTION_AVAILABLE:
        try:
            extract_features(time, flux, period, t0, duration)
        except Exception as fe_err:
            print(f"⚠️  Feature extraction warning: {fe_err}")

    # Save BLS power spectrum plot
    plt.figure(figsize=(7, 3))
    plt.plot(bls_result.period, bls_result.power, lw=0.7, color='#60a5fa')
    plt.xlabel("Period (days)", color='white')
    plt.ylabel("BLS Power", color='white')
    plt.title(f"BLS Power Spectrum — TIC {tic_id}", color='white')
    plt.gca().set_facecolor('#0f172a')
    plt.gcf().patch.set_facecolor('#0f172a')
    plt.tick_params(colors='#94a3b8')
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, f"{tic_id}_bls_power.png"), dpi=120)
    plt.close()

    # Save phase-folded light curve plot (primary scientific output)
    phase = (time - t0 + 0.5 * period) % period - 0.5 * period
    sort_idx = np.argsort(phase)
    phase_sorted = phase[sort_idx]
    flux_sorted  = flux[sort_idx]

    plt.figure(figsize=(8, 4))
    plt.scatter(phase_sorted, flux_sorted, s=1.5, c='#94a3b8', alpha=0.5, rasterized=True)
    # Overlay a 50-point binned profile for clarity
    bin_edges = np.linspace(phase_sorted.min(), phase_sorted.max(), 51)
    bin_centres = 0.5 * (bin_edges[:-1] + bin_edges[1:])
    bin_flux = []
    for lo, hi in zip(bin_edges[:-1], bin_edges[1:]):
        mask = (phase_sorted >= lo) & (phase_sorted < hi)
        bin_flux.append(np.mean(flux_sorted[mask]) if mask.any() else np.nan)
    plt.plot(bin_centres, bin_flux, color='#38bdf8', lw=1.8, label='Binned profile')
    plt.axvspan(-duration / 2.0, duration / 2.0, alpha=0.12, color='#f59e0b', label='Transit window')
    plt.xlabel(f"Phase (days, P = {period:.4f} d)", color='white')
    plt.ylabel("Normalised Flux", color='white')
    plt.title(f"Phase-Folded Light Curve — TIC {tic_id}", color='white')
    plt.legend(facecolor='#1e293b', edgecolor='#334155', labelcolor='white', fontsize=8)
    plt.gca().set_facecolor('#0f172a')
    plt.gcf().patch.set_facecolor('#0f172a')
    plt.tick_params(colors='#94a3b8')
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, f"{tic_id}_phase_folded.png"), dpi=120)
    plt.close()
    print(f"   Phase-folded plot saved.")

    return float(period), float(t0), float(duration)/24, float(snr)

# ----------------------------
# CREATE FITS FILE
# ----------------------------
def create_tess_fits(tic_id: str):
    """Downloads TESS light curve and generates FITS file compatible with AstroNet."""
    # Normalise the ID to 9 digits (pad with leading zeroes)
    tic_id_padded = f"{int(tic_id):09d}"

    prefix = tic_id_padded[:4]
    save_dir = os.path.join(TESS_DATA_DIR, prefix, tic_id_padded)
    os.makedirs(save_dir, exist_ok=True)

    print(f"📦 Generating FITS file for TIC {tic_id_padded}...")
    search_result = search_lightcurve(f"TIC {tic_id}", mission='TESS')
    if len(search_result) == 0:
        raise ValueError(f"No data found for TIC {tic_id}")

    lc = search_result[0].download()
    data = lc.hdu[1].data
    time = data["TIME"]
    
    # Check for various flux column names
    flux_col = None
    for col in ["PDCSAP_FLUX", "CORR_FLUX", "PCA_FLUX", "SAP_FLUX", "FLUX", "RAW_FLUX"]:
        if col in data.names:
            flux_col = col
            break
            
    if flux_col is None:
        raise KeyError(f"No compatible flux column found. Columns: {data.names}")
        
    flux = data[flux_col]

    mask = np.isfinite(time) & np.isfinite(flux)
    time, flux = time[mask], flux[mask]

    cols = fits.ColDefs([
        fits.Column(name='TIME', format='E', array=time),
        fits.Column(name='PDCSAP_FLUX', format='E', array=flux)
    ])
    hdu = fits.BinTableHDU.from_columns(cols, name="LIGHTCURVE")

    output_file = os.path.join(save_dir, f"kplr{tic_id_padded}-2009259160929_llc.fits")
    hdu.writeto(output_file, overwrite=True)

    print(f"✅ FITS file ready: {output_file}")
    return output_file, tic_id_padded

# ----------------------------
# DUMMY PARAMETERS (fallback)
# ----------------------------
def generate_fake_params(tic_id: str):
    """Generates dummy parameters for TIC (if BLS has no clear signal)."""
    np.random.seed(int(tic_id) % 1000)
    period = np.random.uniform(1.5, 15.0)
    t0 = np.random.uniform(1300, 1500)
    duration = np.random.uniform(1.0, 10.0) / 24
    print(f"⚠️  Using dummy parameters:")
    print(f"   Period  = {period:.4f} days")
    print(f"   T0      = {t0:.4f} BKJD")
    print(f"   Duration= {duration*24:.4f} hours")
    return period, t0, duration

# ----------------------------
# RUN ASTRONET MODEL
# ----------------------------
def run_astronet(tic_id_padded: str, period: float, t0: float, duration: float):
    output_file = os.path.join(OUTPUT_DIR, f"{tic_id_padded}.png")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    cmd = [
        sys.executable, "-m", "astronet.predict",
        "--model=AstroCNNModel",
        "--config_name=local_global",
        f"--model_dir={MODEL_DIR}",
        f"--kepler_data_dir={TESS_DATA_DIR}",
        f"--kepler_id={tic_id_padded}",
        f"--period={period}",
        f"--t0={t0}",
        f"--duration={duration}",
        f"--output_image_file={output_file}"
    ]
    print(f"🚀 Running AstroNet model...")
    subprocess.run(cmd, check=True)
    print(f"✅ Prediction completed. Image saved to {output_file}")

# ----------------------------
# MAIN
# ----------------------------
def main():
    if len(sys.argv) not in (2, 5):
        print("Usage: python tess_predict.py <TIC_ID> [period] [t0] [duration]")
        sys.exit(1)

    tic_id = sys.argv[1].strip()
    period_override = None
    t0_override = None
    duration_override = None

    if len(sys.argv) == 5:
        try:
            period_override = float(sys.argv[2])
            t0_override = float(sys.argv[3])
            # duration override is passed in hours; convert to days
            duration_override = float(sys.argv[4]) / 24.0
        except ValueError as err:
            print(f"⚠️  Invalid override arguments: {err}")
            sys.exit(1)

    try:
        try:
            period, t0, duration, snr = analyze_tess_lightcurve(
                tic_id,
                period_override=period_override,
                t0_override=t0_override,
                duration_override=duration_override
            )
        except Exception as e:
            print(f"⚠️  Could not estimate parameters: {e}")
            period, t0, duration = generate_fake_params(tic_id)
            snr = 0.0

        fits_path, tic_id_padded = create_tess_fits(tic_id)
        run_astronet(tic_id_padded, period, t0, duration)

    except Exception as e:
        print(f"❌ General error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
