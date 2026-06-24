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
# FUNCTIONS
# ----------------------------
def get_kepler_params(kepler_id: str):
    """Obtains period, t0 and duration from the official API of the NASA Exoplanet Archive."""
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

    return period, t0, duration / 24  # Convert hours to days

def run_astronet_with_fits(fits_file: str, period: float, t0: float, duration: float):
    """
    Runs the AstroNet model directly with a local FITS file.
    """
    kepler_id = os.path.splitext(os.path.basename(fits_file))[0]
    output_file = os.path.join(OUTPUT_DIR, f"{kepler_id}.png")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    cmd = [
        sys.executable, "-m", "astronet.predict",
        "--model=AstroCNNModel",
        "--config_name=local_global",
        f"--model_dir={MODEL_DIR}",
        f"--kepler_data_dir={KEPLER_DATA_DIR}",
        f"--kepler_id={kepler_id}",
        f"--period={period}",
        f"--t0={t0}",
        f"--duration={duration}",
        f"--fits_file={fits_file}",
        f"--output_image_file={output_file}"
    ]

    print(f"🚀 Running AstroNet for {fits_file} ...")
    subprocess.run(cmd, check=True)
    print(f"✅ Prediction completed. Image saved to {output_file}")
    return output_file

def predict_fits_with_kepler_id(fits_file: str, kepler_id: str):
    """
    Complete pipeline: obtains parameters automatically and runs AstroNet
    with a local FITS file.
    """
    period, t0, duration = get_kepler_params(kepler_id)
    return run_astronet_with_fits(fits_file, period, t0, duration)

# Example of usage:
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python predict_fits_kepler.py <FITS_FILE> <KEPLER_ID>")
        sys.exit(1)

    fits_file = sys.argv[1]
    kepler_id = sys.argv[2]

    predict_fits_with_kepler_id(fits_file, kepler_id)
