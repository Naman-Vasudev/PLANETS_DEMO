/**
 * PipelineStatusCard Component - Shows real-time completion status for each pipeline stage
 * Exoplanet Vetting Platform
 */

import React from "react";
import { CheckCircle2, Circle, Loader2, XCircle, Satellite } from "lucide-react";
import type { PredictionResult } from "../common/DashboardContentWrapper";

interface PipelineStatusCardProps {
  result: PredictionResult | null;
  isAnalyzing: boolean;
}

type StageStatus = "pending" | "running" | "done" | "error" | "skipped";

interface Stage {
  id: string;
  label: string;
  description: string;
  getStatus: (r: PredictionResult | null, analyzing: boolean) => StageStatus;
}

const STAGES: Stage[] = [
  {
    id: "retrieval",
    label: "Light Curve Retrieval",
    description: "MAST archive download via lightkurve",
    getStatus: (r, a) => a ? "running" : r ? "done" : "pending",
  },
  {
    id: "detrending",
    label: "Detrending",
    description: "Sigma-clip + Running Median + Savitzky-Golay",
    getStatus: (r, a) => a ? "running" : r?.period ? "done" : r ? "skipped" : "pending",
  },
  {
    id: "bls",
    label: "BLS Transit Search",
    description: "Box Least Squares periodogram over 20,000 periods",
    getStatus: (r, a) => a ? "running" : r?.period ? "done" : r ? "error" : "pending",
  },
  {
    id: "features",
    label: "Feature Extraction",
    description: "10 astrophysical metrics from phase-folded light curve",
    getStatus: (r, a) => {
      if (a) return "running";
      if (!r) return "pending";
      const hasFeatures = r.features && Object.keys(r.features).length > 0;
      return hasFeatures ? "done" : "skipped";
    },
  },
  {
    id: "astronet",
    label: "AstroNet CNN",
    description: "Deep CNN vetting — score fed into classifier as feature",
    getStatus: (r, a) => a ? "running" : r?.confidence != null ? "done" : "pending",
  },
  {
    id: "classification",
    label: "Signal Classification",
    description: "5-class rule-assisted heuristic classifier",
    getStatus: (r, a) => {
      if (a) return "running";
      if (!r) return "pending";
      return r.signal_type && r.signal_type !== "Unclassified" ? "done" : "skipped";
    },
  },
  {
    id: "explainability",
    label: "Explainability (XAI)",
    description: "RF feature importance / SHAP contributions",
    getStatus: (r, a) => {
      if (a) return "running";
      if (!r) return "pending";
      const hasXai = r.feature_importance && Object.keys(r.feature_importance).length > 0;
      return hasXai ? "done" : "skipped";
    },
  },
];

const StatusIcon: React.FC<{ status: StageStatus }> = ({ status }) => {
  switch (status) {
    case "done":    return <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />;
    case "running": return <Loader2 className="w-4 h-4 text-blue-400 shrink-0 animate-spin" />;
    case "error":   return <XCircle className="w-4 h-4 text-red-400 shrink-0" />;
    case "skipped": return <Circle className="w-4 h-4 text-amber-500/60 shrink-0" />;
    default:        return <Circle className="w-4 h-4 text-gray-600 shrink-0" />;
  }
};

const statusLabel: Record<StageStatus, string> = {
  done: "Complete",
  running: "Running...",
  error: "Failed",
  skipped: "Skipped",
  pending: "Waiting",
};

const statusColour: Record<StageStatus, string> = {
  done: "text-emerald-400",
  running: "text-blue-400",
  error: "text-red-400",
  skipped: "text-amber-500/70",
  pending: "text-gray-600",
};

export const PipelineStatusCard: React.FC<PipelineStatusCardProps> = ({ result, isAnalyzing }) => {
  const completedCount = STAGES.filter(
    (s) => s.getStatus(result, isAnalyzing) === "done"
  ).length;

  const missionBadge = result?.mission ? (
    <span
      className={`text-xs font-bold px-2 py-0.5 rounded-full border ${
        result.mission === "Kepler"
          ? "bg-amber-500/15 border-amber-500/35 text-amber-400"
          : "bg-blue-500/15 border-blue-500/35 text-blue-400"
      }`}
    >
      {result.mission}
    </span>
  ) : null;

  return (
    <div className="bg-gradient-to-br from-slate-900/40 to-blue-900/20 backdrop-blur-lg rounded-xl p-5 border border-blue-500/20">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold flex items-center gap-2 text-white">
          <Satellite className="w-4 h-4 text-blue-400" />
          Pipeline Status
        </h3>
        <div className="flex items-center gap-2">
          {missionBadge}
          <span className="text-xs text-gray-500">
            {completedCount}/{STAGES.length}
          </span>
        </div>
      </div>

      {/* Progress bar */}
      <div className="h-1.5 bg-slate-700/60 rounded-full overflow-hidden mb-4">
        <div
          className="h-full bg-gradient-to-r from-blue-500 to-emerald-400 rounded-full transition-all duration-700"
          style={{ width: `${(completedCount / STAGES.length) * 100}%` }}
        />
      </div>

      {/* Stage list */}
      <div className="space-y-2">
        {STAGES.map((stage) => {
          const status = stage.getStatus(result, isAnalyzing);
          return (
            <div key={stage.id} className="flex items-start gap-2.5">
              <StatusIcon status={status} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-gray-200">{stage.label}</span>
                  <span className={`text-xs ${statusColour[status]}`}>
                    {statusLabel[status]}
                  </span>
                </div>
                <p className="text-xs text-gray-500 truncate">{stage.description}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
