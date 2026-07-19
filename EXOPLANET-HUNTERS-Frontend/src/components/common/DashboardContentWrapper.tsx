/**
 * DashboardContentWrapper Component - Dashboard wrapper with live API integration
 * Exoplanet Vetting Platform
 */

import React, { useState } from 'react';
import { useToast } from './Toast';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

export interface PredictionResult {
  tic_id: string;
  mission: string;
  period: number | null;
  t0: number | null;
  duration_hours: number | null;
  confidence: number;
  classification: string;
  classification_color: 'green' | 'yellow' | 'red';
  snr: number;
  transit_depth: number | null;
  main_image: string | null;
  bls_image: string | null;
  phase_folded_image: string | null;
  raw_output: string;
  // Detection significance (sigmoid-calibrated; replaces raw CNN probability for TESS)
  detection_significance: number;
  significance_label: string;
  significance_color: 'green' | 'yellow' | 'red';
  // Multi-class signal classification (AstroNet score is a feature input)
  signal_type: string;
  signal_probabilities: Record<string, number>;
  // Advanced astrophysical features from feature_extractor.py
  features: Record<string, number>;
  transit_shape_score: number | null;
  secondary_eclipse_strength: number | null;
  odd_even_diff: number | null;
  n_transits: number | null;
  depth_uncertainty: number | null;
  // Explainability layer output
  feature_importance: Record<string, number>;
  explainability_mode: string;
}

interface DashboardContentWrapperProps {
  children: (
    analyzeDemo: () => void,
    runAnalysis: (
      ticId: string,
      periodOverride?: string,
      t0Override?: string,
      durationOverride?: string
    ) => Promise<void>,
    isAnalyzing: boolean,
    result: PredictionResult | null,
  ) => React.ReactNode;
}

export const DashboardContentWrapper: React.FC<DashboardContentWrapperProps> = ({ children }) => {
  const { showToast } = useToast();
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState<PredictionResult | null>(null);

  const runAnalysis = async (
    ticId: string,
    periodOverride?: string,
    t0Override?: string,
    durationOverride?: string
  ) => {
    if (!ticId.trim() || !/^\d+$/.test(ticId.trim())) {
      showToast('error', 'Please enter a valid numeric TIC ID (e.g. 261108232)', 4000);
      return;
    }

    setIsAnalyzing(true);
    setResult(null);
    showToast('info', `🔭 Fetching light curve for TIC ${ticId}…`, 3000);

    try {
      const payload: any = { tic_id: ticId.trim() };
      if (periodOverride && periodOverride.trim()) {
        payload.period_override = parseFloat(periodOverride);
      }
      if (t0Override && t0Override.trim()) {
        payload.t0_override = parseFloat(t0Override);
      }
      if (durationOverride && durationOverride.trim()) {
        payload.duration_override = parseFloat(durationOverride);
      }

      // Pipeline can take 3-5 min on cloud (TF load + MAST download).
      // Use a 10-minute timeout so the browser doesn't silently drop the request.
      const controller = new AbortController();
      const hardTimeout = setTimeout(() => controller.abort(), 10 * 60 * 1000);
      const reassureTimeout = setTimeout(() => {
        showToast('info', '⏳ Still working… downloading light curve & running AI models (can take 2-4 min on first run)', 8000);
      }, 30_000);

      const response = await fetch(`${API_BASE}/predict`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: controller.signal,
      });

      clearTimeout(hardTimeout);
      clearTimeout(reassureTimeout);

      const data: PredictionResult & { error?: string } = await response.json();


      if (!response.ok || data.error) {
        showToast('error', `Pipeline error: ${data.error || 'Unknown error'}`, 5000);
        setIsAnalyzing(false);
        return;
      }

      setResult(data);

      // Notify session stats panel
      window.dispatchEvent(
        new CustomEvent('exoplanet-result', { detail: { confidence: data.confidence } })
      );

      if (data.confidence >= 50) {
        showToast(
          'success',
          `✅ Planet Candidate detected! Confidence: ${data.confidence.toFixed(1)}%`,
          5000,
        );
      } else {
        showToast(
          'warning',
          `Analysis complete. Classified as ${data.classification} (${data.confidence.toFixed(1)}%)`,
          5000,
        );
      }
    } catch (err: any) {
      showToast(
        'error',
        'Could not reach the backend server. Is server.py running?',
        6000,
      );
      console.error('API error:', err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Demo analysis: uses a known confirmed exoplanet TIC ID
  const analyzeDemo = () => {
    showToast('info', '🚀 Running demo analysis on TIC 261108232 (confirmed exoplanet)…', 3000);
    runAnalysis('261108232');
  };

  return <>{children(analyzeDemo, runAnalysis, isAnalyzing, result)}</>;
};
