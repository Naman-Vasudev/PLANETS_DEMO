# 🌌 EXOPLANET-HUNTERS: AI-Enabled Vetting of Noisy Astronomical Light Curves

An end-to-end, mission-agnostic exoplanet detection, data processing, and signal-vetting platform built for the NASA International Space Apps Challenge. 

**EXOPLANET-HUNTERS** integrates classical astronomical analysis with deep learning models and an Explainable AI (XAI) layer to classify and vet exoplanet candidates from raw stellar light curves (supporting both NASA Kepler and TESS missions).

---

## 📋 Table of Contents
- [Project Overview](#-project-overview)
- [Repository Structure](#-repository-structure)
- [Core Pipeline Architecture](#-core-pipeline-architecture)
- [Astrophysical Features Extracted](#-astrophysical-features-extracted)
- [Technology Stack](#-technology-stack)
- [Installation & Running the Platform](#-installation--running-the-platform)
  - [Backend Server Setup](#1-backend-server-setup)
  - [Frontend Dashboard Setup](#2-frontend-dashboard-setup)
- [Scientific Validation](#-scientific-validation)
- [PDF Research Reports](#-pdf-research-reports)

---

## 🌟 Project Overview
Exoplanet transit detection via photometry relies on measuring tiny dips in stellar brightness (often <1% of total flux) as a planet crosses our line of sight. These dips are buried in stellar activity, detector noise, and background binary star blends. 

**EXOPLANET-HUNTERS** solves this by combining:
1. **Advanced 3-Stage Signal Detrending:** Preserves transit curves while cleaning raw data.
2. **Box Least Squares (BLS) Search:** Locates periodic transits across 20,000 trial periods.
3. **Hybrid AI Classifier:** Informs a rule-assisted Random Forest classifier with physical parameters and raw deep learning (AstroNet CNN) scores.
4. **SHAP Explainable AI Layer:** Translates raw neural network outputs into human-understandable physical explanations of *why* a candidate was vetted or rejected.

---

## 📁 Repository Structure
The repository is split into three main components:

*   **`astronet-cnn-v3/exoplanet-ml/` (Core Vetting Backend):**
    *   `server.py`: Tornado-based asynchronous REST API.
    *   `detrending.py`: Code for outlier rejection (Sigma-clipping), running median detrending, and Savitzky-Golay filtering.
    *   `feature_extractor.py`: Module calculating 10 diagnostic astrophysical properties.
    *   `classifier.py`: 5-class Random Forest classifier using synthetic decision boundary training data.
    *   `explainability.py`: XAI layer utilizing SHAP TreeExplainer and RandomForest fallback importances.
    *   `report_generator.py`: Generates scientific PDF reports from vetting outcomes.
*   **`EXOPLANET-HUNTERS-Frontend/` (Visual Dashboard):**
    *   React 19 + TypeScript + TailwindCSS application containing real-time analytics, light curve visualization, probability meters, and PDF exporter.
*   **`EXOPLANET-HUNTERS-Backend/` (Boilerplate Auth API):**
    *   Initial FastAPI and PostgreSQL authentication endpoint boilerplate.

---

## ⚙️ Core Pipeline Architecture

```
User Inputs KIC / TIC ID via React Dashboard
                     ↓
[Stage 1] Light Curve Retrieval (lightkurve API → NASA MAST Archive)
                     ↓
[Stage 2] Noise Reduction & Detrending (Sigma-clip → Running Median → Savitzky-Golay)
                     ↓
[Stage 3] BLS Transit Search (Period, Epoch, & Duration extraction)
                     ↓
[Stage 4] Advanced Feature Extraction (Computes 10 astrophysical parameters)
                     ↓
[Stage 5] AstroNet CNN Inference (Parallel vetting; calibrated for TESS domain shift)
                     ↓
[Stage 6] Rule-Assisted Heuristic Random Forest Classifier (5 target classes)
                     ↓
[Stage 7] Explainable AI (XAI) Analysis (SHAP contribution calculation)
                     ↓
React Dashboard visualizes curves, classification probabilities, and SHAP charts
```

---

## 📊 Astrophysical Features Extracted

The backend extracts 10 physical indicators from phase-folded light curves:

| Feature | Physical Meaning & Diagnostic Value |
|---|---|
| `transit_depth` | Fractional brightness reduction `(F_out - F_in) / F_out`. |
| `snr` | Transit signal-to-noise ratio: `(depth / σ_out) * √N_in`. |
| `orbital_period` | Best-fit BLS orbital period in days. |
| `transit_duration_hours` | Width of the transit event in hours. |
| `n_transits` | Count of observed transit crossings. |
| `odd_even_diff` | Depth difference between odd and even transits (identifies Eclipsing Binaries). |
| `secondary_eclipse_strength` | Presence of a secondary eclipse dip at phase 0.5 (identifies Eclipsing Binaries). |
| `transit_shape_score` | Ratio of flat-bottom to total width (U-shaped = Planet, V-shaped = Binary). |
| `transit_symmetry` | Ingress vs. egress slope symmetry (identifies blends and variable stars). |
| `depth_uncertainty` | Bootstrap resampling (200 iterations) standard deviation of transit depth. |

---

## 🛠️ Technology Stack

*   **Backend:** Python 3.10, Tornado Server, SciPy, NumPy, Astropy.
*   **Deep Learning & ML:** TensorFlow 1.x (AstroNet CNN compatibility), Scikit-Learn (Random Forest), SHAP.
*   **Frontend:** React 19, TypeScript, TailwindCSS, Chart.js / Recharts.
*   **Data Source:** NASA MAST Archive via Lightkurve client.
*   **Reporting:** ReportLab (dynamic PDF generation).

---

## 🚀 Installation & Running the Platform

### 1. Backend Server Setup
The vetting server runs on Python 3.10 and requires the `venv_compat` environment.

1. Navigate to the core folder:
   ```bash
   cd astronet-cnn-v3/exoplanet-ml
   ```
2. Activate the pre-configured virtual environment:
   * **Windows (PowerShell):**
     ```powershell
     ..\venv_compat\Scripts\Activate.ps1
     ```
   * **Linux/macOS:**
     ```bash
     source ../venv_compat/bin/activate
     ```
3. Run the API Server (runs on `http://localhost:8000`):
   ```bash
   python server.py
   ```

### 2. Frontend Dashboard Setup
The React dashboard communicates with the Tornado API to run predictions.

1. Navigate to the frontend folder:
   ```bash
   cd EXOPLANET-HUNTERS-Frontend
   ```
2. Install Node dependencies:
   ```bash
   npm install
   ```
3. Start the local server (opens on `http://localhost:3000`):
   ```bash
   npm start
   ```

---

## 🧪 Scientific Validation
The platform's analytical steps and classifications have been successfully tested on:
*   **TIC 183374187 (TESS Confirmed Exoplanet):** Pipeline detects significant periodic transit events.
*   **KIC 10797460 (Kepler Confirmed Exoplanet Host):** AstroNet CNN correctly assigns high planet candidate probability.

---

## 📄 PDF Research Reports
The system automatically generates consolidated research reports for verified candidate targets in scientific paper format. Sample outputs are available in the root directory:
*   [Consolidated_Research_Report.pdf](file:///n:/PLANETS/Consolidated_Research_Report.pdf)
*   [Research_Report_TIC_294329732.pdf](file:///n:/PLANETS/Research_Report_TIC_294329732.pdf)
