"""
Exoplanet Hunter REST API Server
Automated Vetting Platform

Bridges the React frontend with the AstroNet ML pipeline.
"""

import os
import sys
import io

# Force UTF-8 encoding for standard streams to prevent Unicode errors on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import json
import base64
import subprocess
import re
import numpy as np
import tornado.ioloop
import tornado.web
import tornado.gen
import importlib

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.environ.get("MODEL_DIR", os.path.join(BASE_DIR, "MODEL_DIR"))
TESS_DATA_DIR = os.environ.get("TESS_DATA_DIR", os.path.join(BASE_DIR, "KEPLER_DATA_DIR"))
OUTPUT_DIR = os.environ.get("OUTPUT_DIR", os.path.join(BASE_DIR, "kepler_pictures"))
# Auto-detect Python executable: use venv on Windows, system python on Linux/cloud
_win_python = os.path.join(BASE_DIR, "..", "venv_compat", "Scripts", "python.exe")
PYTHON_EXE = _win_python if os.path.exists(_win_python) else sys.executable
# PORT: Render/Railway inject $PORT at runtime; fall back to 8000 locally
PORT = int(os.environ.get("PORT", 8000))

# ── Optional classification + explainability modules ─────────────────────────
# Imported at server startup so model initialisation happens once only.
# If the modules are not yet available (e.g. first-run before creation),
# classification simply returns 'Unclassified' without crashing.
sys.path.insert(0, BASE_DIR)
try:
    import classifier as _classifier
    import explainability as _explainability
    CLASSIFICATION_AVAILABLE = True
except ImportError as _e:
    _classifier = None          # type: ignore[assignment]
    _explainability = None      # type: ignore[assignment]
    CLASSIFICATION_AVAILABLE = False
    print(f"Warning: Classification modules not yet available: {_e}", file=sys.stderr)

try:
    import report_generator as _report_generator
    REPORT_AVAILABLE = True
except ImportError as _e:
    _report_generator = None    # type: ignore[assignment]
    REPORT_AVAILABLE = False
    print(f"Warning: report_generator not available: {_e}", file=sys.stderr)



class CORSHandler(tornado.web.RequestHandler):
    """Base handler — CORS headers injected via set_default_headers (survives all error responses)."""

    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.set_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.set_header("Access-Control-Max-Age", "86400")

    def options(self, *args, **kwargs):
        self.set_status(204)
        self.finish()




def read_image_b64(path: str) -> str | None:
    """Read an image file and return it as a base64 data URI, or None if missing."""
    if path and os.path.exists(path):
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        return f"data:image/png;base64,{data}"
    return None


def run_pipeline(
    tic_id: str,
    period_override: float = None,
    t0_override: float = None,
    duration_override: float = None
) -> dict:
    """
    Run the appropriate pipeline script (kepler_input.py for Kepler targets,
    tess_input.py for TESS targets) as a subprocess and parse its stdout.
    """
    env = {**os.environ, "PYTHONUTF8": "1"}
    # Kepler KIC IDs are 7 or 8 digits; TESS TIC IDs are 9 or more digits.
    if len(tic_id) <= 8:
        script = "kepler_input.py"
        cmd = [PYTHON_EXE, "-u", script, tic_id]
    else:
        script = "tess_input.py"
        cmd = [PYTHON_EXE, "-u", script, tic_id]
        if period_override is not None:
            cmd.extend([str(period_override), str(t0_override), str(duration_override)])

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        cwd=BASE_DIR,
    )

    stdout = result.stdout + result.stderr

    if result.returncode != 0 and "Prediction:" not in stdout:
        # Try to extract a clean error message
        last_line = [l.strip() for l in stdout.splitlines() if l.strip()]
        msg = last_line[-1] if last_line else "Unknown error from pipeline."
        return {"error": msg}

    # ── Parse core parameters from stdout ─────────────────────────────────────
    period   = _parse_float(stdout, r"Period\s*[:\=]\s*([\d.]+)")
    t0       = _parse_float(stdout, r"T0\s*[:\=]\s*([\d.]+)")
    duration = _parse_float(stdout, r"Duration\s*[:\=]\s*([\d.]+)")
    depth    = _parse_float(stdout, r"BLS Depth\s*[:\=]\s*([\d.]+)")

    # AstroNet CNN score — runs before or in parallel with the multi-class classifier
    conf_raw = _parse_float(stdout, r"Prediction:\s*([\d.eE+\-]+)")
    confidence_pct = round(float(conf_raw) * 100, 2) if conf_raw is not None else 0.0
    astronet_score = float(conf_raw) if conf_raw is not None else 0.0

    # AstroNet-based classification label (Kepler reliable; TESS informational only)
    if confidence_pct >= 50:
        cnn_classification = "PLANET CANDIDATE"
        cnn_color = "green"
    elif confidence_pct >= 10:
        cnn_classification = "LOW CONFIDENCE"
        cnn_color = "yellow"
    else:
        cnn_classification = "FALSE POSITIVE"
        cnn_color = "red"

    # Signal-to-noise ratio: parse BLS SNR from stdout
    snr = _parse_float(stdout, r"BLS SNR\s*[:\=]\s*([\d.]+)")
    if snr is None:
        snr = round(astronet_score * 50, 1) if conf_raw is not None else 0.0
    else:
        snr = round(snr, 1)

    # ── Detection Significance (replaces raw CNN probability for TESS) ─────────
    # For TESS: sigmoid mapping of BLS SNR produces a detection significance
    # score derived from BLS signal-to-noise ratio. This is NOT a statistically
    # calibrated planet probability; it reflects signal strength only.
    # For Kepler: AstroNet CNN score is used directly as the significance proxy.
    is_tess = len(tic_id) > 8
    if is_tess:
        sig_raw = (1.0 - float(np.exp(-((snr / 6.0) ** 2)))) * 100.0
        detection_significance = round(min(99.9, sig_raw), 2)
    else:
        detection_significance = confidence_pct

    if detection_significance >= 90:
        significance_label = "Highly Significant Signal"
        significance_color = "green"
    elif detection_significance >= 70:
        significance_label = "Strong Signal"
        significance_color = "green"
    elif detection_significance >= 30:
        significance_label = "Moderate Signal"
        significance_color = "yellow"
    else:
        significance_label = "Weak Signal"
        significance_color = "red"

    # ── Parse advanced feature extraction values (FE prefix) ──────────────────
    fe_features = {}
    for line in stdout.splitlines():
        m = re.match(r"\s*FE\s+([\w_]+):\s*([\d.\-eE]+)", line.strip())
        if m:
            key = m.group(1)
            try:
                fe_features[key] = float(m.group(2))
            except ValueError:
                pass

    # ── Multi-class signal classification ─────────────────────────────────────
    # AstroNet score is passed as a feature so it contributes to the final
    # vetting decision alongside BLS-derived astrophysical features.
    signal_type = "Unclassified"
    signal_probabilities = {}
    feature_importance = {}
    explainability_mode = "Unavailable"

    if fe_features and CLASSIFICATION_AVAILABLE:
        try:
            clf_result = _classifier.classify(fe_features, astronet_score=astronet_score)
            signal_type = clf_result["predicted_class"]
            signal_probabilities = clf_result["class_probabilities"]
            feature_importance = clf_result["feature_importance"]

            # Explainability: AstroNet score is included in the feature vector,
            # so it contributes to the explanation alongside BLS features.
            exp_result = _explainability.explain(
                fe_features, _classifier._get_model(), astronet_score=astronet_score
            )
            feature_importance = exp_result["contributions"]
            explainability_mode = exp_result["mode"]
        except Exception as clf_err:
            print(f"⚠️  Classification error (non-fatal): {clf_err}", file=sys.stderr)


    # ── Image paths ────────────────────────────────────────────────────────────
    if not is_tess:
        tic_padded = tic_id.zfill(9)
        main_img_path  = os.path.join(OUTPUT_DIR, f"{tic_id}.png")
        bls_img_path   = None
        phase_img_path = os.path.join(OUTPUT_DIR, f"{tic_id}_phase_folded.png")
    else:
        tic_padded = f"{int(tic_id):09d}"
        main_img_path  = os.path.join(OUTPUT_DIR, f"{tic_padded}.png")
        bls_img_path   = os.path.join(OUTPUT_DIR, f"{tic_id}_bls_power.png")
        phase_img_path = os.path.join(OUTPUT_DIR, f"{tic_id}_phase_folded.png")

    return {
        # Core identifiers
        "tic_id":                   tic_id,
        "tic_id_padded":            tic_padded,
        "mission":                  "TESS" if is_tess else "Kepler",
        # BLS transit parameters
        "period":                   period,
        "t0":                       t0,
        "duration_hours":           duration,
        "transit_depth":            depth,
        # Signal quality
        "snr":                      snr,
        # AstroNet CNN result (Stage 2 — contributes to classification)
        "confidence":               confidence_pct,
        "classification":           cnn_classification,
        "classification_color":     cnn_color,
        # Detection significance (renamed from raw probability)
        "detection_significance":   detection_significance,
        "significance_label":       significance_label,
        "significance_color":       significance_color,
        # Multi-class signal classification (Stage 3+4, AstroNet-informed)
        "signal_type":              signal_type,
        "signal_probabilities":     signal_probabilities,
        # Advanced features
        "features":                 fe_features,
        "transit_shape_score":      fe_features.get("transit_shape_score"),
        "secondary_eclipse_strength": fe_features.get("secondary_eclipse_strength"),
        "odd_even_diff":            fe_features.get("odd_even_diff"),
        "n_transits":               fe_features.get("n_transits"),
        "depth_uncertainty":        fe_features.get("depth_uncertainty"),
        # Explainability
        "feature_importance":       feature_importance,
        "explainability_mode":      explainability_mode,
        # Visualisation images (base64)
        "main_image":               read_image_b64(main_img_path),
        "bls_image":                read_image_b64(bls_img_path),
        "phase_folded_image":       read_image_b64(phase_img_path),
        "raw_output":               stdout,
    }


def _parse_float(text: str, pattern: str):
    """Return the first float captured by pattern, or None."""
    m = re.search(pattern, text)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass
    return None


# ── Request Handlers ───────────────────────────────────────────────────────────

class HealthHandler(CORSHandler):
    """GET /api/v1/health — simple liveness check."""


    def get(self):
        self.write({"status": "ok", "model": "AstroNet CNN v3", "port": PORT})


class PredictHandler(CORSHandler):
    """POST /api/v1/predict — run the full AstroNet pipeline for a TIC ID."""


    @tornado.gen.coroutine
    def post(self):
        try:
            body = json.loads(self.request.body)
            tic_id = str(body.get("tic_id", "")).strip()
            if not tic_id or not tic_id.isdigit():
                self.set_status(400)
                self.write({"error": "Please provide a valid numeric TIC ID."})
                return

            # Parse optional advanced overrides
            period_override = body.get("period_override")
            t0_override = body.get("t0_override")
            duration_override = body.get("duration_override")

            if period_override is not None:
                try:
                    period_override = float(period_override)
                    t0_override = float(t0_override)
                    duration_override = float(duration_override)
                except (ValueError, TypeError):
                    self.set_status(400)
                    self.write({"error": "Override parameters must be numbers."})
                    return

            # Run pipeline (blocking — acceptable for a single-user demo server)
            result = run_pipeline(
                tic_id,
                period_override=period_override,
                t0_override=t0_override,
                duration_override=duration_override
            )

            if "error" in result:
                self.set_status(422)

            self.write(result)

        except json.JSONDecodeError:
            self.set_status(400)
            self.write({"error": "Invalid JSON body."})
        except Exception as exc:
            self.set_status(500)
            self.write({"error": str(exc)})


class NewsHandler(CORSHandler):
    """GET /api/v1/news — fetch latest space and exoplanet news dynamically from RSS."""


    def get(self):
        try:
            import urllib.request
            from xml.etree import ElementTree
            
            url = "https://phys.org/rss-feed/space-news/"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5) as response:
                xml_data = response.read()
            
            root = ElementTree.fromstring(xml_data)
            news_items = []
            
            # Parse up to 5 items
            for item in root.findall('.//item')[:5]:
                title = item.find('title').text if item.find('title') is not None else "Unknown Title"
                link = item.find('link').text if item.find('link') is not None else "https://phys.org"
                
                # Get creator or fallback
                creator = item.find('{http://purl.org/dc/elements/1.1/}creator')
                author = creator.text if creator is not None and creator.text else "Science Journalist"
                
                # Format time
                pubDate = item.find('pubDate').text if item.find('pubDate') is not None else ""
                time_str = pubDate.split(',')[1].strip() if ',' in pubDate else pubDate
                time_str = ' '.join(time_str.split()[:3])
                
                news_items.append({
                    "title": title,
                    "author": author,
                    "source": "Phys.org Space",
                    "url": link,
                    "time": time_str
                })
            
            self.write({"news": news_items})
        except Exception as exc:
            # Fallback to static news if offline/error
            self.write({
                "news": [
                    {
                        "title": "NASA Confirms 6,000th Exoplanet Discovery Milestone",
                        "author": "Shawn Domagal-Goldman",
                        "source": "Science Daily",
                        "url": "https://www.sciencedaily.com/releases/2025/09/250920214427.htm",
                        "time": "2 weeks ago"
                    },
                    {
                        "title": "AI Predicts Exoplanets Using Transformer Architecture",
                        "author": "Prof. Yann Alibert",
                        "source": "Phys.org",
                        "url": "https://phys.org/news/2025-09-ai-discovery-exoplanets-distant.html",
                        "time": "3 weeks ago"
                    },
                    {
                        "title": "JWST Narrows Atmosphere Possibilities for TRAPPIST-1e",
                        "author": "Dr. Néstor Espinoza",
                        "source": "Phys.org",
                        "url": "https://phys.org/news/2025-09-trappist-1e-narrow-possibilities-atmosphere.html",
                        "time": "4 weeks ago"
                    }
                ]
            })


class ReportHandler(CORSHandler):
    """
    POST /api/v1/report

    Accepts the same JSON body as /api/v1/predict  { "tic_id": "..." }.
    Runs the full pipeline, then generates and streams a PDF report.
    Falls back to plain-text if reportlab is unavailable.
    """


    @tornado.gen.coroutine
    def post(self):
        try:
            body = json.loads(self.request.body)
            # If the request contains a full pipeline result, use it directly
            # to make PDF generation instantaneous.
            if "period" in body and "tic_id" in body:
                result = body
                tic_id = str(result.get("tic_id", "")).strip()
            else:
                tic_id = str(body.get("tic_id", "")).strip()
                if not tic_id or not tic_id.isdigit():
                    self.set_status(400)
                    self.write({"error": "Please provide a valid numeric TIC ID."})
                    return
                result = run_pipeline(tic_id)
            if "error" in result:
                self.set_status(422)
                self.write(result)
                return

            if REPORT_AVAILABLE:
                try:
                    pdf_bytes = _report_generator.generate_pdf_report(result)
                    self.set_header("Content-Type", "application/pdf")
                    self.set_header(
                        "Content-Disposition",
                        f'attachment; filename="exoplanet_report_{tic_id}.pdf"'
                    )
                    self.write(pdf_bytes)
                    return
                except Exception as pdf_err:
                    print(f"PDF generation failed, falling back to text: {pdf_err}", file=sys.stderr)

            # Fallback: plain-text report
            if _report_generator is not None:
                txt = _report_generator.generate_plaintext_report(result)
            else:
                txt = f"Report unavailable. Pipeline result for TIC {tic_id}: {json.dumps(result, indent=2)}"
            self.set_header("Content-Type", "text/plain; charset=utf-8")
            self.set_header(
                "Content-Disposition",
                f'attachment; filename="exoplanet_report_{tic_id}.txt"'
            )
            self.write(txt.encode("utf-8"))

        except json.JSONDecodeError:
            self.set_status(400)
            self.write({"error": "Invalid JSON body."})
        except Exception as exc:
            self.set_status(500)
            self.write({"error": str(exc)})


# ── App factory ────────────────────────────────────────────────────────────────

def make_app():
    return tornado.web.Application([
        (r"/api/v1/health",  HealthHandler),
        (r"/api/v1/predict", PredictHandler),
        (r"/api/v1/report",  ReportHandler),
        (r"/api/v1/news",    NewsHandler),
    ])


if __name__ == "__main__":
    app = make_app()
    app.listen(PORT)
    print(f"🚀 Exoplanet Hunter API server running on http://localhost:{PORT}")
    print(f"   POST http://localhost:{PORT}/api/v1/predict  {{ \"tic_id\": \"261108232\" }}")
    print(f"   GET  http://localhost:{PORT}/api/v1/health")
    print("   Press Ctrl+C to stop.\n")
    tornado.ioloop.IOLoop.current().start()
