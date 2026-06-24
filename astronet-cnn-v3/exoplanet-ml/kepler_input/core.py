import os
import sys
import subprocess
import requests

# ----------------------------
# GENERAL CONFIGURATION
# ----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_DIR = os.environ.get("MODEL_DIR", os.path.join(BASE_DIR, "MODEL_DIR"))
KEPLER_DATA_DIR = os.environ.get("KEPLER_DATA_DIR", os.path.join(BASE_DIR, "KEPLER_DATA_DIR"))
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", os.path.join(BASE_DIR, "kepler_pictures"))
API_URL = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync"

# ----------------------------
# FUNCTION TO OBTAIN NASA ARCHIVE DATA
# ----------------------------
def get_kepler_params(kepler_id: str):
    """Obtains period, t0 and duration from the official NASA Exoplanet Archive API."""
    query = (
        f"SELECT koi.kepid, koi.koi_period, koi.koi_time0bk, koi.koi_duration "
        f"FROM q1_q17_dr25_koi koi "
        f"WHERE koi.kepid = {kepler_id}"
    )
    params = {"query": query, "format": "json"}

    print(f"🔍 Querying parameters for Kepler ID {kepler_id}...")
    response = requests.get(API_URL, params=params)
    response.raise_for_status()

    data = response.json()
    if not data:
        raise ValueError(f"No data found for Kepler ID {kepler_id}")

    entry = data[0]
    period = entry.get("koi_period")
    t0 = entry.get("koi_time0bk")
    duration = entry.get("koi_duration")

    if None in (period, t0, duration):
        raise ValueError(f"Incomplete data for Kepler ID {kepler_id}")

    print(f"✅ Parameters obtained:")
    print(f"   Period  = {period} days")
    print(f"   T0      = {t0} BKJD")
    print(f"   Duration= {duration} hours")

    return period, t0, duration / 24


# ----------------------------
# DOWNLOAD FITS FILES
# ----------------------------
def download_fits_files(kepler_id: str):
    """Downloads the FITS files for the specified ID."""
    kepler_id_padded = kepler_id.zfill(9)
    prefix = kepler_id_padded[:4]
    save_dir = os.path.join(KEPLER_DATA_DIR, prefix, kepler_id_padded)
    os.makedirs(save_dir, exist_ok=True)

    url = f"http://archive.stsci.edu/pub/kepler/lightcurves/{prefix}/{kepler_id_padded}/"
    print(f"⬇️  Downloading FITS from {url} ...")

    cmd = [
        "wget",
        "-nH", "--cut-dirs=6", "-r", "-l0", "-c", "-N", "-np",
        "-erobots=off", "-R", "index*", "-A", "*_llc.fits",
        "-P", save_dir, url
    ]
    subprocess.run(cmd, check=True)
    print(f"✅ FITS files saved in {save_dir}")
    return save_dir


# ----------------------------
# RUN THE ASTRONET MODEL
# ----------------------------
def run_astronet(kepler_id: str, period: float, t0: float, duration: float):
    """Runs the AstroNet model for the Kepler ID."""
    output_file = os.path.join(OUTPUT_DIR, f"{kepler_id}.png")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    cmd = [
        "python", "-m", "astronet.predict",
        "--model=AstroCNNModel",
        "--config_name=local_global",
        f"--model_dir={MODEL_DIR}",
        f"--kepler_data_dir={KEPLER_DATA_DIR}",
        f"--kepler_id={kepler_id}",
        f"--period={period}",
        f"--t0={t0}",
        f"--duration={duration}",
        f"--output_image_file={output_file}"
    ]

    print("🚀 Running AstroNet model...")
    subprocess.run(cmd, check=True)
    print(f"✅ Prediction completed. Image saved to {output_file}")
    return output_file


# ----------------------------
# COMPLETE PIPELINE
# ----------------------------
def predict(kepler_id: str):
    """Complete pipeline for Kepler ID."""
    period, t0, duration = get_kepler_params(kepler_id)
    download_fits_files(kepler_id)
    run_astronet(kepler_id, period, t0, duration)
    print("✅ Process finished successfully.")
