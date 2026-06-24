/**
 * TodayStats Component - Live session statistics panel
 * Exoplanet Vetting Platform
 *
 * Counts are persisted in sessionStorage so they reset when the tab closes
 * but persist across page refreshes within the same session.
 */

import React, { useEffect, useState } from 'react';

function getSessionInt(key: string, fallback: number): number {
  const v = sessionStorage.getItem(key);
  return v !== null ? parseInt(v, 10) : fallback;
}

/**
 * Displays live session analysis statistics.
 */
export const TodayStats: React.FC = () => {
  const [totalRun, setTotalRun] = useState(() => getSessionInt('stats_total', 0));
  const [candidates, setCandidates] = useState(() => getSessionInt('stats_candidates', 0));
  const [falsePos, setFalsePos] = useState(() => getSessionInt('stats_false', 0));

  useEffect(() => {
    // Listen for custom events dispatched by DashboardContentWrapper after each prediction
    const onResult = (e: Event) => {
      const detail = (e as CustomEvent).detail as { confidence: number };
      const isCandidate = detail.confidence >= 50;

      setTotalRun((prev) => {
        const next = prev + 1;
        sessionStorage.setItem('stats_total', String(next));
        return next;
      });

      if (isCandidate) {
        setCandidates((prev) => {
          const next = prev + 1;
          sessionStorage.setItem('stats_candidates', String(next));
          return next;
        });
      } else {
        setFalsePos((prev) => {
          const next = prev + 1;
          sessionStorage.setItem('stats_false', String(next));
          return next;
        });
      }
    };

    window.addEventListener('exoplanet-result', onResult);
    return () => window.removeEventListener('exoplanet-result', onResult);
  }, []);

  return (
    <div className="bg-slate-800/50 backdrop-blur-lg rounded-xl p-4 border border-nasa-500/20">
      <h3 className="text-sm font-semibold mb-3 text-nasa-300">Session Stats</h3>
      <div className="space-y-2 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-400">Analyses Run</span>
          <span className="font-semibold text-blue-400">{totalRun.toLocaleString()}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400">Candidates Found</span>
          <span className="font-semibold text-nasa-400">{candidates}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400">False Positives</span>
          <span className="font-semibold text-red-400">{falsePos}</span>
        </div>
      </div>
    </div>
  );
};
