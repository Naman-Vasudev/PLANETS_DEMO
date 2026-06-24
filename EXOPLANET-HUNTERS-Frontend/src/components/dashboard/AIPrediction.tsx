/**
 * AIPrediction Component - Displays AI model predictions for exoplanet detection
 * Exoplanet Vetting Platform
 *
 * IMPORTANT SCIENTIFIC NOTE:
 * The AstroNet CNN (Shallue & Vanderburg 2018) was trained on Kepler mission data.
 * When applied to TESS light curves the CNN classification score is unreliable due
 * to domain shift (different cadence, noise profile, systematics, pixel scale).
 * The BLS period-detection stage is mission-agnostic and remains valid for TESS.
 *
 * We therefore present two separate stages:
 *   1. TRANSIT DETECTION  — BLS periodogram (mission-agnostic, reliable on TESS)
 *   2. CNN CLASSIFICATION — AstroNet score (trained on Kepler; treat with caution on TESS)
 */

import React from 'react';
import { Brain, AlertTriangle, CheckCircle2, XCircle, HelpCircle, Signal } from 'lucide-react';
import type { PredictionResult } from '../common/DashboardContentWrapper';

interface AIPredictionProps {
  confidence: number;
  result: PredictionResult | null;
}

/** BLS Transit Detection badge — mission-agnostic stage */
const BlsDetectionBadge: React.FC<{ period: number | null }> = ({ period }) => {
  if (period == null) {
    return (
      <div className="flex items-center gap-1.5 px-2 py-1 bg-gray-700/50 border border-gray-600/30 rounded-full text-xs text-gray-400">
        <HelpCircle className="w-3 h-3" />
        No period detected
      </div>
    );
  }
  return (
    <div className="flex items-center gap-1.5 px-2 py-1 bg-green-500/15 border border-green-500/30 rounded-full text-xs text-green-400 font-semibold">
      <CheckCircle2 className="w-3 h-3" />
      Transit signal detected
    </div>
  );
};

/** CNN classification badge with domain-shift caveat */
const CnnClassBadge: React.FC<{ classification: string; colour: 'green' | 'yellow' | 'red' }> = ({
  classification,
  colour,
}) => {
  const styles = {
    green:  'bg-green-500/15  border-green-500/30  text-green-400',
    yellow: 'bg-yellow-500/15 border-yellow-500/30 text-yellow-400',
    red:    'bg-red-500/15    border-red-500/30    text-red-400',
  };
  const Icon = colour === 'green' ? CheckCircle2 : colour === 'yellow' ? AlertTriangle : XCircle;
  return (
    <div className={`flex items-center gap-1.5 px-2 py-1 border rounded-full text-xs font-semibold ${styles[colour]}`}>
      <Icon className="w-3 h-3" />
      {classification}
    </div>
  );
};

/**
 * Displays AstroNet pipeline results split into two stages:
 * BLS transit detection (reliable) and CNN classification (Kepler-trained caveat).
 */
export const AIPrediction: React.FC<AIPredictionProps> = ({ confidence, result }) => {
  const isTess = result?.tic_id ? result.tic_id.length >= 9 : false;

  // For Kepler, use the CNN score. For TESS, use the BLS SNR to vet the transit.
  // When no result yet: show 0 (empty bar) instead of any default placeholder value.
  let displayConf = result ? result.confidence : 0;
  let classification = result ? result.classification : 'AWAITING ANALYSIS';
  let colour: 'green' | 'yellow' | 'red' | 'gray' = result ? (result.classification_color as any) : 'gray';

  // Use server-computed detection_significance when available (preferred);
  // fall back to local sigmoid on SNR for backwards compatibility.
  if (result && isTess) {
    if (result.detection_significance != null) {
      displayConf = result.detection_significance;
    } else {
      const rawProb = (1.0 - Math.exp(-Math.pow(result.snr / 6.0, 2))) * 100;
      displayConf = Math.min(99.9, rawProb);
    }
    if (result.snr >= 7.0) {
      classification = "TRANSIT DETECTED (BLS)";
      colour = "green";
    } else if (result.snr >= 4.0) {
      classification = "WEAK TRANSIT (BLS)";
      colour = "yellow";
    } else {
      classification = "FALSE POSITIVE (BLS)";
      colour = "red";
      displayConf = result.detection_significance ?? 0.0;
    }
  }

  const period         = result?.period        != null ? `${result.period.toFixed(3)} d` : '—';
  const duration       = result?.duration_hours != null ? `${result.duration_hours.toFixed(2)} h` : '—';
  const snr            = result?.snr            != null ? result.snr.toFixed(1)          : '—';
  const depth          = result?.transit_depth  != null ? `${(result.transit_depth * 100).toFixed(3)}%` : '—';

  const barColour = colour === 'green' ? 'from-green-500 to-emerald-400'
                  : colour === 'yellow' ? 'from-yellow-500 to-amber-400'
                  : colour === 'red' ? 'from-red-500 to-rose-400'
                  : 'from-slate-600 to-slate-500';
  const valColour = colour === 'green' ? 'text-green-400'
                  : colour === 'yellow' ? 'text-yellow-400'
                  : colour === 'red' ? 'text-red-400'
                  : 'text-gray-500';

  return (
    <div className="bg-gradient-to-br from-nasa-900/30 to-blue-900/30 backdrop-blur-lg rounded-xl p-6 border border-nasa-500/30 space-y-5">

      {/* ── Header ────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold flex items-center gap-2">
          <Brain className="w-5 h-5 text-nasa-400" />
          AI Prediction
        </h3>
        {result && (
          <span className="text-xs text-gray-500 font-mono">TIC {result.tic_id}</span>
        )}
      </div>

      {/* ── Stage 1: BLS Transit Detection ────────────────────────── */}
      <div className="bg-slate-800/60 rounded-xl p-4 border border-green-500/20">
        <div className="flex items-center justify-between mb-3">
          <div>
            <p className="text-xs font-bold text-gray-300 uppercase tracking-wider">
              Stage 1 — Transit Detection (BLS)
            </p>
            <p className="text-xs text-gray-500 mt-0.5">
              Box Least-Squares periodogram · mission-agnostic
            </p>
          </div>
          <BlsDetectionBadge period={result?.period ?? null} />
        </div>

        <div className="grid grid-cols-2 gap-3 mt-3">
          <div className="bg-slate-900/50 rounded-lg p-3 border border-nasa-500/10">
            <div className="text-xs text-gray-400 mb-1">Orbital Period</div>
            <div className="text-lg font-bold text-nasa-400">{period}</div>
            <div className="text-xs text-gray-500">BLS best fit</div>
          </div>
          <div className="bg-slate-900/50 rounded-lg p-3 border border-nasa-500/10">
            <div className="text-xs text-gray-400 mb-1">Duration</div>
            <div className="text-lg font-bold text-blue-400">{duration}</div>
            <div className="text-xs text-gray-500">Transit length</div>
          </div>
          <div className="bg-slate-900/50 rounded-lg p-3 border border-nasa-500/10">
            <div className="text-xs text-gray-400 mb-1">BLS SNR</div>
            <div className="text-lg font-bold text-nasa-400">{snr}</div>
            <div className="text-xs text-gray-500">Signal strength</div>
          </div>
          <div className="bg-slate-900/50 rounded-lg p-3 border border-nasa-500/10">
            <div className="text-xs text-gray-400 mb-1">Transit Depth</div>
            <div className="text-lg font-bold text-purple-400">{depth}</div>
            <div className="text-xs text-gray-500">Relative depth</div>
          </div>
        </div>
      </div>

      {/* ── Stage 2: CNN Classification ───────────────────────────── */}
      <div className="bg-slate-800/60 rounded-xl p-4 border border-nasa-500/20">
        <div className="flex items-center justify-between mb-3">
          <div>
            <p className="text-xs font-bold text-gray-300 uppercase tracking-wider">
              Stage 2 — CNN Classification (AstroNet)
            </p>
            <p className="text-xs text-gray-500 mt-0.5">
              Shallue &amp; Vanderburg 2018 · trained on Kepler TCEs
            </p>
          </div>
          {result && (
            <CnnClassBadge classification={classification} colour={colour as any} />
          )}
        </div>

        {/* Confidence bar */}
        <div className="mb-3">
          <div className="flex justify-between text-xs mb-2">
            <span className="text-xs text-gray-400 flex items-center gap-1">
              <Signal className="w-3 h-3" /> Detection Significance
            </span>
            <span className={`font-bold ${valColour}`}>{result ? `${displayConf.toFixed(1)}%` : '—'}</span>
          </div>
          <div className="h-3 bg-slate-700/50 rounded-full overflow-hidden">
            <div
              className={`h-full bg-gradient-to-r ${barColour} rounded-full transition-all duration-700`}
              style={{ width: `${Math.max(displayConf, 0.5)}%` }}
            />
          </div>
        </div>

        {/* Significance tier label */}
        {result && result.significance_label && (
          <div className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-semibold
            ${
              result.significance_color === 'green'  ? 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/25' :
              result.significance_color === 'yellow' ? 'bg-yellow-500/15 text-yellow-300 border border-yellow-500/25' :
                                                       'bg-red-500/15 text-red-300 border border-red-500/25'
            }`}
          >
            <Signal className="w-3.5 h-3.5" />
            {result.significance_label}
          </div>
        )}

        {/* Domain-shift warning — always shown for TESS targets */}
        {result && (
          <div className="mt-3 flex gap-2 p-3 bg-amber-500/10 border border-amber-500/25 rounded-lg">
            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
            <div className="text-xs text-amber-300 leading-relaxed">
              <strong>Domain shift caveat:</strong> AstroNet was trained on{' '}
              <em>Kepler</em> photometry. TESS has different cadence, pixel scale,
              and systematic noise — the CNN score may be unreliable for TESS targets.
              A low CNN score does <strong>not</strong> rule out a genuine transit if the
              BLS period is significant.{' '}
              <a
                href="https://doi.org/10.3847/1538-3881/aa9e09"
                target="_blank"
                rel="noopener noreferrer"
                className="underline hover:text-amber-200"
              >
                Paper ↗
              </a>
            </div>
          </div>
        )}
      </div>

      {/* ── BLS power spectrum image ──────────────────────────────── */}
      {result?.bls_image && (
        <div>
          <p className="text-xs text-gray-400 mb-2 font-semibold">BLS Power Spectrum</p>
          <img
            src={result.bls_image}
            alt={`BLS power spectrum for TIC ${result.tic_id}`}
            className="w-full rounded-lg border border-nasa-500/10"
          />
          <p className="text-xs text-gray-500 mt-1 text-center">
            Peaks correspond to candidate orbital periods. Dominant peak at {period}.
          </p>
        </div>
      )}
    </div>
  );
};
