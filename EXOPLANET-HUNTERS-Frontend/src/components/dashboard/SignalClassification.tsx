/**
 * SignalClassification Component - Multi-Class Astrophysical Signal Classifier
 * Exoplanet Vetting Platform
 *
 * Displays the output of the rule-assisted heuristic classifier initialized
 * using astrophysical priors. Shows predicted class badge, probability bars
 * for all 5 classes, feature score mini-cards, and explainability panel.
 */

import React from 'react';
import {
  FlaskConical,
  Binary,
  AlertTriangle,
  TrendingDown,
  XCircle,
  CheckCircle2,
  Info,
  Layers,
} from 'lucide-react';
import type { PredictionResult } from '../common/DashboardContentWrapper';

interface SignalClassificationProps {
  result: PredictionResult | null;
}

const CLASS_META: Record<string, {
  icon: React.FC<{ className?: string }>;
  colour: string;
  bg: string;
  border: string;
  description: string;
}> = {
  'Exoplanet Transit': {
    icon: CheckCircle2,
    colour: 'text-emerald-400',
    bg: 'bg-emerald-500/15',
    border: 'border-emerald-500/35',
    description: 'U-shaped transit, symmetric ingress/egress, no secondary eclipse detected.',
  },
  'Eclipsing Binary': {
    icon: Binary,
    colour: 'text-amber-400',
    bg: 'bg-amber-500/15',
    border: 'border-amber-500/35',
    description: 'Large odd-even depth difference and secondary eclipse present — two stellar components.',
  },
  'Blend / Contaminated Source': {
    icon: Layers,
    colour: 'text-yellow-400',
    bg: 'bg-yellow-500/15',
    border: 'border-yellow-500/35',
    description: 'Shallow diluted transit — possibly from a background source within the photometric aperture.',
  },
  'Variable Star': {
    icon: TrendingDown,
    colour: 'text-orange-400',
    bg: 'bg-orange-500/15',
    border: 'border-orange-500/35',
    description: 'Low-SNR periodic variability consistent with stellar pulsation or rotation.',
  },
  'False Positive / Noise': {
    icon: XCircle,
    colour: 'text-red-400',
    bg: 'bg-red-500/15',
    border: 'border-red-500/35',
    description: 'No statistically significant transit signal detected above the noise floor.',
  },
};

const ORDERED_CLASSES = [
  'Exoplanet Transit',
  'Eclipsing Binary',
  'Blend / Contaminated Source',
  'Variable Star',
  'False Positive / Noise',
];

const CLASS_BAR_COLOURS: Record<string, string> = {
  'Exoplanet Transit': 'from-emerald-500 to-teal-400',
  'Eclipsing Binary': 'from-amber-500 to-orange-400',
  'Blend / Contaminated Source': 'from-yellow-500 to-amber-400',
  'Variable Star': 'from-orange-500 to-red-400',
  'False Positive / Noise': 'from-red-600 to-rose-500',
};

const FeatureScoreCard: React.FC<{
  label: string;
  value: number | null;
  fmt: (v: number) => string;
  colour: string;
  tooltip: string;
}> = ({ label, value, fmt, colour, tooltip }) => (
  <div
    className="bg-slate-900/50 rounded-lg p-3 border border-white/5 flex flex-col gap-1"
    title={tooltip}
  >
    <div className="text-xs text-gray-400">{label}</div>
    <div className={`text-base font-bold ${colour}`}>
      {value != null ? fmt(value) : '-'}
    </div>
  </div>
);

export const SignalClassification: React.FC<SignalClassificationProps> = ({ result }) => {
  if (!result) {
    return (
      <div className="bg-gradient-to-br from-slate-900/40 to-purple-900/20 backdrop-blur-lg rounded-xl p-6 border border-purple-500/20 space-y-4">
        <div className="flex items-center gap-2">
          <FlaskConical className="w-5 h-5 text-purple-400" />
          <h3 className="text-lg font-semibold text-white">Signal Classification</h3>
        </div>
        <p className="text-sm text-gray-500 text-center py-6">
          Run an analysis to see astrophysical signal classification.
        </p>
      </div>
    );
  }

  const signalType = result.signal_type ?? 'Unclassified';
  const probs = result.signal_probabilities ?? {};
  const importance = result.feature_importance ?? {};
  const meta = CLASS_META[signalType];
  const ClassIcon = meta?.icon ?? AlertTriangle;

  const topFeatures = Object.entries(importance)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 6);

  const maxImportance = topFeatures.length > 0 ? topFeatures[0][1] : 1;

  return (
    <div className="bg-gradient-to-br from-slate-900/40 to-purple-900/20 backdrop-blur-lg rounded-xl p-6 border border-purple-500/20 space-y-5">

      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold flex items-center gap-2 text-white">
          <FlaskConical className="w-5 h-5 text-purple-400" />
          Signal Classification
        </h3>
        {result.explainability_mode && result.explainability_mode !== 'Unavailable' && (
          <span className="text-xs text-gray-500 font-mono px-2 py-0.5 bg-slate-800 rounded-full">
            XAI: {result.explainability_mode}
          </span>
        )}
      </div>

      {/* Predicted Class Badge */}
      {signalType !== 'Unclassified' ? (
        <div className={`flex items-start gap-3 p-4 rounded-xl border ${meta?.bg ?? 'bg-slate-800/40'} ${meta?.border ?? 'border-white/10'}`}>
          <ClassIcon className={`w-6 h-6 shrink-0 mt-0.5 ${meta?.colour ?? 'text-gray-400'}`} />
          <div>
            <p className={`font-bold text-base ${meta?.colour ?? 'text-gray-200'}`}>{signalType}</p>
            <p className="text-xs text-gray-400 mt-0.5 leading-relaxed">{meta?.description}</p>
          </div>
        </div>
      ) : (
        <div className="flex items-center gap-2 p-3 bg-slate-800/40 rounded-xl border border-white/10">
          <Info className="w-4 h-4 text-gray-500" />
          <span className="text-sm text-gray-400">
            Classification unavailable - feature extraction may be in progress.
          </span>
        </div>
      )}

      {/* Class Probability Bars */}
      {Object.keys(probs).length > 0 && (
        <div className="bg-slate-800/50 rounded-xl p-4 border border-white/5 space-y-2.5">
          <p className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">
            Class Probabilities
          </p>
          {ORDERED_CLASSES.map((cls) => {
            const pct = probs[cls] ?? 0;
            const barClass = CLASS_BAR_COLOURS[cls] ?? 'from-gray-500 to-gray-400';
            const isWinner = cls === signalType;
            return (
              <div key={cls}>
                <div className="flex justify-between text-xs mb-1">
                  <span className={isWinner ? 'text-white font-semibold' : 'text-gray-400'}>
                    {cls}
                  </span>
                  <span className={isWinner ? 'text-white font-bold' : 'text-gray-500'}>
                    {typeof pct === 'number' ? pct.toFixed(1) : '0.0'}%
                  </span>
                </div>
                <div className="h-1.5 bg-slate-700/60 rounded-full overflow-hidden">
                  <div
                    className={`h-full bg-gradient-to-r ${barClass} rounded-full transition-all duration-700`}
                    style={{ width: `${Math.max(typeof pct === 'number' ? pct : 0, 0.3)}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Feature Score Mini-Cards */}
      <div className="grid grid-cols-2 gap-3">
        <FeatureScoreCard
          label="Transit Shape"
          value={result.transit_shape_score}
          fmt={(v) => v.toFixed(2)}
          colour={
            result.transit_shape_score != null && result.transit_shape_score > 0.6
              ? 'text-emerald-400'
              : 'text-amber-400'
          }
          tooltip="Shape score 0-1. Near 1.0 = U-shaped (planet-like). Near 0 = V-shaped (eclipsing binary)."
        />
        <FeatureScoreCard
          label="Secondary Eclipse"
          value={result.secondary_eclipse_strength}
          fmt={(v) => `${(v * 100).toFixed(3)}%`}
          colour={
            result.secondary_eclipse_strength != null && result.secondary_eclipse_strength > 0.005
              ? 'text-amber-400'
              : 'text-emerald-400'
          }
          tooltip="Depth of secondary dip near phase 0.5. High value strongly suggests an eclipsing binary."
        />
        <FeatureScoreCard
          label="Odd-Even Delta Depth"
          value={result.odd_even_diff}
          fmt={(v) => `${(v * 100).toFixed(3)}%`}
          colour={
            result.odd_even_diff != null && result.odd_even_diff > 0.01
              ? 'text-amber-400'
              : 'text-emerald-400'
          }
          tooltip="Depth difference between odd and even transits. Large value indicates an eclipsing binary."
        />
        <FeatureScoreCard
          label="N Transits"
          value={result.n_transits}
          fmt={(v) => String(Math.round(v))}
          colour="text-blue-400"
          tooltip="Number of distinct transit events observed in the light curve."
        />
      </div>

      {/* Explainability Panel */}
      {topFeatures.length > 0 && (
        <div className="bg-slate-800/50 rounded-xl p-4 border border-purple-500/15 space-y-2.5">
          <p className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-3">
            Feature Contributions
            <span className="ml-2 text-purple-400 normal-case font-normal">
              ({result.explainability_mode ?? 'RF Importance'})
            </span>
          </p>
          {topFeatures.map(([name, pct]) => {
            const barWidth = maxImportance > 0 ? (pct / maxImportance) * 100 : 0;
            const displayName = name
              .replace(/_/g, ' ')
              .replace(/\b\w/g, (c) => c.toUpperCase());
            return (
              <div key={name}>
                <div className="flex justify-between text-xs mb-1">
                  <span className="text-gray-300">{displayName}</span>
                  <span className="text-purple-300 font-semibold">{pct.toFixed(1)}%</span>
                </div>
                <div className="h-1.5 bg-slate-700/60 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-purple-500 to-indigo-400 rounded-full transition-all duration-500"
                    style={{ width: `${Math.max(barWidth, 1)}%` }}
                  />
                </div>
              </div>
            );
          })}
          <p className="text-xs text-gray-500 mt-2 leading-relaxed">
            Contributions normalised to 100%. The AstroNet score is included as a feature
            input so it contributes alongside BLS-derived astrophysical metrics.
          </p>
        </div>
      )}
    </div>
  );
};
