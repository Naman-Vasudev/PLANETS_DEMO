/**
 * ModelPerformance Component - Displays AI model performance metrics
 * Exoplanet Vetting Platform
 *
 * Metrics sourced from the published AstroNet paper:
 * Shallue & Vanderburg (2018), AJ, 155, 94
 * "Identifying Exoplanets with Deep Learning: A Five-Planet Resonant Chain around Kepler-80"
 * DOI: 10.3847/1538-3881/aa9e09
 *
 * On the held-out test set of 3,400 TCEs (Threshold Crossing Events):
 *   Accuracy  = 96.0%
 *   Precision = 94.1%
 *   Recall    = 96.9%
 * Trained on 14,731 Kepler light curves labelled by the Cumulative KOI catalogue.
 */

import React from 'react';
import { TrendingUp, ExternalLink } from 'lucide-react';

const METRICS = [
  { label: 'Accuracy',  value: 96.0, colour: 'bg-green-500',   text: 'text-green-400',  bar: '96%'  },
  { label: 'Precision', value: 94.1, colour: 'bg-blue-500',    text: 'text-blue-400',   bar: '94%'  },
  { label: 'Recall',    value: 96.9, colour: 'bg-nasa-500',    text: 'text-nasa-400',   bar: '97%'  },
];

/**
 * Shows accuracy, precision and recall metrics from the published AstroNet paper.
 */
export const ModelPerformance: React.FC = () => (
  <div className="bg-slate-800/50 backdrop-blur-lg rounded-xl p-4 border border-nasa-500/20">
    <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
      <TrendingUp className="w-4 h-4 text-green-400" />
      Model Performance
    </h3>
    <div className="space-y-3">
      {METRICS.map(({ label, value, colour, text, bar }) => (
        <div key={label}>
          <div className="flex justify-between text-xs mb-1">
            <span className="text-gray-400">{label}</span>
            <span className={`font-semibold ${text}`}>{value}%</span>
          </div>
          <div className="h-2 bg-slate-700/50 rounded-full overflow-hidden">
            <div className={`h-full ${colour} rounded-full transition-all duration-500`} style={{ width: bar }} />
          </div>
        </div>
      ))}
    </div>
    <div className="mt-3 pt-3 border-t border-nasa-500/20 text-xs text-gray-400 space-y-1">
      <div>Trained on 14,731 Kepler TCEs</div>
      <a
        href="https://doi.org/10.3847/1538-3881/aa9e09"
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center gap-1 text-nasa-400 hover:text-nasa-300 transition-colors"
      >
        Shallue &amp; Vanderburg (2018) <ExternalLink className="w-3 h-3" />
      </a>
    </div>
  </div>
);
