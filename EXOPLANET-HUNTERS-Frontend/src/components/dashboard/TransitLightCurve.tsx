/**
 * TransitLightCurve Component - Shows AstroNet prediction image AND phase-folded plot
 * Exoplanet Vetting Platform
 */

import React, { useState } from "react";
import { Telescope, BarChart3 } from "lucide-react";
import type { PredictionResult } from "../common/DashboardContentWrapper";

interface TransitLightCurveProps {
  isAnalyzing: boolean;
  result: PredictionResult | null;
}

const PlaceholderCurve: React.FC = () => (
  <svg className="w-full h-full" viewBox="0 0 800 250">
    <path
      d="M 0 125 L 200 125 L 250 145 L 300 145 L 350 125 L 800 125"
      stroke="#8b5cf6" strokeWidth="2" fill="none" className="drop-shadow-lg"
    />
    <path d="M 0 125 L 800 125" stroke="#475569" strokeWidth="1" strokeDasharray="5,5" fill="none" />
    <rect x="240" y="130" width="70" height="30" fill="#8b5cf6" opacity="0.2" rx="4" />
    <text x="275" y="170" fontSize="10" fill="#a78bfa" textAnchor="middle">Transit Event</text>
  </svg>
);

type TabId = "astronet" | "phase" | "bls";

export const TransitLightCurve: React.FC<TransitLightCurveProps> = ({ isAnalyzing, result }) => {
  const [activeTab, setActiveTab] = useState<TabId>("phase");

  // Switch to phase-folded tab automatically when a result arrives
  React.useEffect(() => {
    if (result?.phase_folded_image) setActiveTab("phase");
    else if (result?.main_image) setActiveTab("astronet");
  }, [result]);

  const tabs: { id: TabId; label: string; icon: React.ReactNode; available: boolean }[] = [
    {
      id: "phase",
      label: "Phase-Folded",
      icon: <Telescope className="w-3.5 h-3.5" />,
      available: !!result?.phase_folded_image,
    },
    {
      id: "astronet",
      label: "AstroNet CNN",
      icon: <BarChart3 className="w-3.5 h-3.5" />,
      available: !!result?.main_image,
    },
    {
      id: "bls",
      label: "BLS Power",
      icon: <BarChart3 className="w-3.5 h-3.5" />,
      available: !!result?.bls_image,
    },
  ];

  const activeImg =
    activeTab === "phase" ? result?.phase_folded_image
    : activeTab === "astronet" ? result?.main_image
    : result?.bls_image;

  const missionColor = result?.mission === "Kepler" ? "text-amber-400" : "text-blue-400";
  const missionBg    = result?.mission === "Kepler" ? "bg-amber-500/15 border-amber-500/35" : "bg-blue-500/15 border-blue-500/35";

  return (
    <div className="bg-slate-800/50 backdrop-blur-lg rounded-xl p-6 border border-nasa-500/20">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">Transit Light Curve</h3>
        <div className="flex items-center gap-2">
          {result?.mission && (
            <span className={`text-xs font-bold px-2 py-0.5 rounded-full border ${missionBg} ${missionColor}`}>
              {result.mission}
            </span>
          )}
          {result && (
            <span className="text-xs text-gray-400">TIC {result.tic_id}</span>
          )}
        </div>
      </div>

      {/* Tab selector — only shown when results exist */}
      {result && (
        <div className="flex gap-1 mb-3">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => tab.available && setActiveTab(tab.id)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                activeTab === tab.id
                  ? "bg-nasa-600/70 text-white border border-nasa-500/50"
                  : tab.available
                  ? "bg-slate-700/50 text-gray-400 hover:text-white hover:bg-slate-700"
                  : "bg-slate-800/30 text-gray-600 cursor-not-allowed"
              }`}
              disabled={!tab.available}
              title={!tab.available ? "Not available for this mission / analysis" : undefined}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </div>
      )}

      <div className="relative bg-slate-900/50 rounded-lg border border-nasa-500/10 overflow-hidden">
        {activeImg ? (
          <img
            src={activeImg}
            alt={`${activeTab} plot for TIC ${result?.tic_id}`}
            className="w-full h-auto rounded-lg"
          />
        ) : (
          <div className="h-64">
            <PlaceholderCurve />
          </div>
        )}

        {isAnalyzing && (
          <div className="absolute inset-0 bg-slate-900/80 flex items-center justify-center">
            <div className="text-center">
              <div className="w-12 h-12 border-4 border-nasa-500 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
              <p className="text-sm text-nasa-300">Analysing transit pattern...</p>
              <p className="text-xs text-gray-500 mt-1">Detrending + BLS + AstroNet CNN</p>
            </div>
          </div>
        )}
      </div>

      <div className="mt-4 flex items-center justify-between text-xs text-gray-400">
        <span>
          {activeTab === "phase" ? "Phase (days)" : "Time / Period (days)"}
        </span>
        <span>Normalised Flux</span>
      </div>
    </div>
  );
};
