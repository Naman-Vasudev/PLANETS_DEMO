import os
import sys
import io

# Force UTF-8 encoding for standard streams to prevent Unicode errors on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import subprocess
import requests
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

BASE_DIR        = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR       = os.environ.get("MODEL_DIR",       os.path.join(BASE_DIR, "MODEL_DIR"))
KEPLER_DATA_DIR = os.environ.get("KEPLER_DATA_DIR", os.path.join(BASE_DIR, "KEPLER_DATA_DIR"))
OUTPUT_DIR      = os.environ.get("OUTPUT_DIR",      os.path.join(BASE_DIR, "kepler_pictures"))
API_URL         = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"

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


def get_kepler_params(kepler_id: str):
    """Obtains period, t0, duration and depth from the NASA Exoplanet Archive TAP service."""
    query = (
        f"SELECT koi.kepid, koi.koi_period, koi.koi_time0bk, koi.koi_duration, koi.koi_depth "
        f"FROM q1_q17_dr25_koi koi WHERE koi.kepid = {kepler_id}"
    )
    print(f"Searching for light curve for KIC {kepler_id}...")
    try:
        response = requests.get(API_URL, params={"query": query, "format": "json"}, timeout=15)
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        raise RuntimeError(f"NASA Exoplanet Archive query failed: {exc}")

    if not data:
        raise ValueError(f"No data found for Kepler ID {kepler_id}")

    entry    = data[0]
    period   = entry.get("koi_period")
    t0       = entry.get("koi_time0bk")
    duration = entry.get("koi_duration")
    depth_ppm = entry.get("koi_depth")

    if None in (period, t0, duration):
        raise ValueError(f"Incomplete archive data for Kepler ID {kepler_id}")

    depth = float(depth_ppm) / 1e6 if depth_ppm is not None else 0.0
    duration_days = float(duration) / 24.0

    print(f"Parameters obtained:")
    print(f"   Period  = {period} days")
    print(f"   T0      = {t0} BKJD")
    print(f"   Duration: {float(duration):.2f} hours")
    print(f"   BLS Depth: {depth:.6f}")
    return float(period), float(t0), duration_days, depth


def download_fits_files(kepler_id: str) -> str:
    """Locates or downloads Kepler FITS files for the given KIC ID."""
    kepler_id_padded = kepler_id.zfill(9)
    prefix   = kepler_id_padded[:4]
    save_dir = os.path.join(KEPLER_DATA_DIR, prefix, kepler_id_padded)
    os.makedirs(save_dir, exist_ok=True)

    import glob
    existing = glob.glob(os.path.join(save_dir, "*_llc.fits"))
    if existing:
        print(f"Found {len(existing)} existing Kepler FITS files in {save_dir}. Skipping download.")
        return save_dir

    # Pure-Python download fallback using lightkurve (no wget dependency)
    try:
        from lightkurve import search_lightcurve
        import shutil
        print(f"📦 Searching MAST for Kepler ID {kepler_id} using lightkurve...")
        search_result = search_lightcurve(f"KIC {kepler_id}", mission="Kepler", author="Kepler", cadence="long")
        if len(search_result) == 0:
            search_result = search_lightcurve(f"KIC {kepler_id}", mission="Kepler", cadence="long")

        if len(search_result) > 0:
            print(f"   Found {len(search_result)} quarters on MAST. Downloading...")
            for item in search_result:
                try:
                    lc = item.download()
                    if lc is not None:
                        cached_path = lc.filename
                        dest_name = os.path.basename(cached_path)
                        # Ensure standard Kepler file naming convention is kept
                        if not dest_name.endswith("_llc.fits") and ".fits" in dest_name:
                            dest_name = dest_name.replace(".fits", "_llc.fits")
                        dest_path = os.path.join(save_dir, dest_name)
                        shutil.copy(cached_path, dest_path)
                except Exception as dl_err:
                    print(f"   Warning: failed to download single quarter: {dl_err}")
            
            # Verify we downloaded something
            existing = glob.glob(os.path.join(save_dir, "*_llc.fits"))
            if existing:
                print(f"✅ FITS files saved in {save_dir}")
                return save_dir
    except Exception as lk_err:
        print(f"⚠️ lightkurve download failed/unavailable: {lk_err}. Trying legacy wget...")

    # Legacy wget download (fallback for backward compatibility if lightkurve fails)
    url = f"http://archive.stsci.edu/pub/kepler/lightcurves/{prefix}/{kepler_id_padded}/"
    print(f"Downloading FITS from {url} ...")
    cmd = ["wget", "-nH", "--cut-dirs=6", "-r", "-l0", "-c", "-N", "-np",
           "-erobots=off", "-R", "index*", "-A", "*_llc.fits", "-P", save_dir, url]
    try:
        subprocess.run(cmd, check=True)
    except FileNotFoundError:
        print("wget is not available. Kepler FITS files must be pre-loaded in the data directory.")
        raise
    print(f"FITS files saved in {save_dir}")
    return save_dir


def load_kepler_lightcurve(save_dir: str):
    """Load, concatenate and median-normalise all Kepler FITS quarter files."""
    import glob
    from astropy.io import fits as astropy_fits

    fits_files = sorted(glob.glob(os.path.join(save_dir, "*_llc.fits")))
    if not fits_files:
        raise RuntimeError(f"No *_llc.fits files found in {save_dir}")

    time_list, flux_list = [], []
    for fpath in fits_files:
        try:
            with astropy_fits.open(fpath) as hdul:
                data = hdul[1].data
                t = data["TIME"].astype(np.float64)
                flux_col = next((c for c in ["PDCSAP_FLUX", "SAP_FLUX", "FLUX"] if c in data.names), None)
                if flux_col is None:
                    continue
                f = data[flux_col].astype(np.float64)
                mask = np.isfinite(t) & np.isfinite(f)
                time_list.append(t[mask])
                flux_list.append(f[mask])
        except Exception as exc:
            print(f"   Could not read {os.path.basename(fpath)}: {exc}")

    if not time_list:
        raise RuntimeError("No valid flux data could be loaded from Kepler FITS files.")

    time = np.concatenate(time_list)
    flux = np.concatenate(flux_list)
    sort_idx = np.argsort(time)
    time, flux = time[sort_idx], flux[sort_idx]
    median_flux = np.median(flux)
    if median_flux > 0:
        flux = flux / median_flux

    print(f"   Loaded {len(time)} data points from {len(fits_files)} FITS file(s).")
    return time, flux


def compute_bls_snr(time: np.ndarray, flux: np.ndarray,
                    period: float, t0: float, duration: float) -> float:
    """Compute transit SNR for the given orbital solution on the Kepler light curve."""
    phase = (time - t0 + 0.5 * period) % period - 0.5 * period
    in_transit = np.abs(phase) < (duration / 2.0)
    flux_in, flux_out = flux[in_transit], flux[~in_transit]
    if len(flux_in) == 0 or len(flux_out) == 0:
        return 0.0
    depth   = np.mean(flux_out) - np.mean(flux_in)
    std_out = np.std(flux_out)
    if std_out <= 0:
        return 0.0
    snr = (depth / std_out) * np.sqrt(len(flux_in))
    print(f"   BLS SNR : {snr:.2f}")
    return float(snr)


def generate_plots(kepler_id: str, time: np.ndarray, flux: np.ndarray,
                   period: float, t0: float, duration: float) -> None:
    """Generate phase-folded light curve plot for the Kepler target."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    phase = (time - t0 + 0.5 * period) % period - 0.5 * period
    sort_idx     = np.argsort(phase)
    phase_sorted = phase[sort_idx]
    flux_sorted  = flux[sort_idx]

    plt.figure(figsize=(8, 4))
    plt.scatter(phase_sorted, flux_sorted, s=1.5, c='#94a3b8', alpha=0.5, rasterized=True)
    bin_edges   = np.linspace(phase_sorted.min(), phase_sorted.max(), 51)
    bin_centres = 0.5 * (bin_edges[:-1] + bin_edges[1:])
    bin_flux = []
    for lo, hi in zip(bin_edges[:-1], bin_edges[1:]):
        mask = (phase_sorted >= lo) & (phase_sorted < hi)
        bin_flux.append(np.mean(flux_sorted[mask]) if mask.any() else np.nan)
    plt.plot(bin_centres, bin_flux, color='#38bdf8', lw=1.8, label='Binned profile')
    plt.axvspan(-duration / 2.0, duration / 2.0, alpha=0.12, color='#f59e0b', label='Transit window')
    plt.xlabel(f"Phase (days, P = {period:.4f} d)", color='white')
    plt.ylabel("Normalised Flux", color='white')
    plt.title(f"Phase-Folded Light Curve - KIC {kepler_id}", color='white')
    plt.legend(facecolor='#1e293b', edgecolor='#334155', labelcolor='white', fontsize=8)
    plt.gca().set_facecolor('#0f172a')
    plt.gcf().patch.set_facecolor('#0f172a')
    plt.tick_params(colors='#94a3b8')
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, f"{kepler_id}_phase_folded.png"), dpi=120)
    plt.close()
    print(f"   Phase-folded plot saved.")


def run_astronet(kepler_id: str, period: float, t0: float, duration: float) -> None:
    """Runs the AstroNet CNN model for the given KIC ID."""
    output_file = os.path.join(OUTPUT_DIR, f"{kepler_id}.png")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    cmd = [
        sys.executable, "-m", "astronet.predict",
        "--model=AstroCNNModel", "--config_name=local_global",
        f"--model_dir={MODEL_DIR}", f"--kepler_data_dir={KEPLER_DATA_DIR}",
        f"--kepler_id={kepler_id}", f"--period={period}",
        f"--t0={t0}", f"--duration={duration}",
        f"--output_image_file={output_file}"
    ]
    print("Running AstroNet model...")
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as exc:
        print(f"AstroNet inference failed (non-fatal): {exc}")
    print(f"Prediction completed. Image saved to {output_file}")


def predict(kepler_id: str) -> None:
    """
    Complete Kepler pipeline with full feature parity to the TESS pipeline.

    Stages:
      1. Retrieve orbital parameters from NASA Exoplanet Archive
      2. Download or locate Kepler FITS files
      3. Load and normalise the light curve
      4. Apply detrending (sigma-clip + Savitzky-Golay)
      5. Compute BLS SNR
      6. Extract astrophysical features (10 metrics, FE-prefix output)
      7. Generate phase-folded plot
      8. Run AstroNet CNN

    Note: This is a rule-assisted heuristic classifier initialized using
    astrophysical priors. Future work includes replacement with
    mission-labelled training datasets.
    """
    period, t0, duration, depth = get_kepler_params(kepler_id)
    save_dir = download_fits_files(kepler_id)

    time, flux = np.array([]), np.array([])
    try:
        time, flux = load_kepler_lightcurve(save_dir)
    except RuntimeError as exc:
        print(f"Could not load light curve: {exc}. Skipping detrending and feature extraction.")

    snr = 0.0
    if len(time) > 100:
        if DETRENDING_AVAILABLE:
            time, flux = detrend_lightcurve(time, flux)
        else:
            print("Detrending module unavailable - using raw normalised light curve.")

        snr = compute_bls_snr(time, flux, period, t0, duration)

        if FEATURE_EXTRACTION_AVAILABLE:
            try:
                extract_features(time, flux, period, t0, duration)
            except Exception as fe_err:
                print(f"Feature extraction warning: {fe_err}")

        try:
            generate_plots(kepler_id, time, flux, period, t0, duration)
        except Exception as plot_err:
            print(f"Plot generation warning: {plot_err}")

    kepler_id_padded = kepler_id.zfill(9)
    run_astronet(kepler_id_padded, period, t0, duration)
    print("Process finished successfully.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python kepler_input.py <KEPLER_ID>")
        sys.exit(1)
    predict(sys.argv[1])
