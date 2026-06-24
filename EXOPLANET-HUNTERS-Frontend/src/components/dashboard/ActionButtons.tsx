/**
 * ActionButtons Component - Export and share buttons
 * Exoplanet Vetting Platform
 */

import React, { useState } from 'react';
import { Download, Share2, X, FileSpreadsheet, FileText, FileDown } from 'lucide-react';
import { useToast } from '../common/Toast';
import type { PredictionResult } from '../common/DashboardContentWrapper';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

interface ActionButtonsProps {
  onShare: () => void;
  result: PredictionResult | null;
}

type ExportFormat = 'csv' | 'xlsx' | 'pdf';

/**
 * Buttons for exporting results and sharing discoveries
 */
export const ActionButtons: React.FC<ActionButtonsProps> = ({ onShare, result }) => {
  const [showExportModal, setShowExportModal] = useState(false);
  const [selectedFormat, setSelectedFormat] = useState<ExportFormat>('csv');
  const [isPdfLoading, setIsPdfLoading] = useState(false);
  const { showToast } = useToast();

  const handleExport = async () => {
    if (!result) {
      showToast('error', 'No analysis results available to export. Please run an analysis first.', 4000);
      setShowExportModal(false);
      return;
    }

    if (selectedFormat === 'pdf') {
      setShowExportModal(false);
      setIsPdfLoading(true);
      try {
        const response = await fetch(`${API_BASE}/report`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(result),
        });
        if (!response.ok) {
          const err = await response.json().catch(() => ({ error: 'Server error' }));
          showToast('error', `PDF generation failed: ${err.error}`, 5000);
          return;
        }
        const blob = await response.blob();
        const url  = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `exoplanet_report_${result.tic_id}.pdf`;
        link.click();
        URL.revokeObjectURL(url);
        showToast('success', '✅ PDF report downloaded successfully.', 4000);
      } catch (err: any) {
        showToast('error', `Failed to download PDF: ${err.message}`, 4000);
      } finally {
        setIsPdfLoading(false);
      }
      return;
    }

    try {
      const fileName = `exoplanet_analysis_${result.tic_id}`;
      const probs = result.signal_probabilities ?? {};
      const feats = result.features ?? {};

      const rows = [
        ["Parameter", "Value", "Unit", "Description"],
        ["Target ID",                 result.tic_id,                             "",      "Target identifier"],
        ["Mission",                   result.mission ?? "N/A",                   "",      "Observing mission"],
        ["Orbital Period",            result.period?.toFixed(6) ?? "N/A",       "days",  "BLS detected orbital period"],
        ["Transit Epoch (T0)",        result.t0?.toFixed(6) ?? "N/A",           "BKJD",  "First transit epoch"],
        ["Transit Duration",          result.duration_hours?.toFixed(4) ?? "N/A","hours", "Duration of transit"],
        ["BLS SNR",                   result.snr?.toFixed(2) ?? "N/A",           "",      "Signal-to-noise ratio"],
        ["Transit Depth",             result.transit_depth != null ? `${(result.transit_depth * 100).toFixed(4)}%` : "N/A", "", "Fractional depth"],
        ["Detection Significance",    result.detection_significance?.toFixed(2) + "%" ?? "N/A", "", "BLS SNR-derived score (NOT a planet probability)"],
        ["Significance Tier",         result.significance_label ?? "N/A",        "",      "Tier classification"],
        ["AstroNet CNN Score",        result.confidence?.toFixed(2) + "%" ?? "N/A","",   "CNN output (domain-shift caveat for TESS)"],
        ["CNN Classification",        result.classification,                      "",      "AstroNet vetting label"],
        ["Predicted Signal Type",     result.signal_type ?? "N/A",               "",      "Multi-class classifier output"],
        ["Transit Shape Score",       result.transit_shape_score?.toFixed(4) ?? "N/A", "", "1=U-shape (planet), 0=V-shape (EB)"],
        ["Secondary Eclipse Depth",   result.secondary_eclipse_strength != null ? `${(result.secondary_eclipse_strength * 100).toFixed(4)}%` : "N/A", "", "Depth at phase 0.5"],
        ["Odd-Even Depth Difference", result.odd_even_diff != null ? `${(result.odd_even_diff * 100).toFixed(4)}%` : "N/A", "", "EB discriminator"],
        ["N Transits",                result.n_transits?.toFixed(0) ?? "N/A",    "",      "Number of transit events"],
        ["Depth Uncertainty",         result.depth_uncertainty != null ? `${(result.depth_uncertainty * 100).toFixed(4)}%` : "N/A", "", "Bootstrap depth uncertainty"],
        ["Explainability Mode",       result.explainability_mode ?? "N/A",       "",      "XAI method used"],
        ...(Object.entries(probs).map(([cls, pct]) => [
          `P(${cls})`, typeof pct === 'number' ? pct.toFixed(1) + "%" : "N/A", "", "Class probability"
        ])),
        ...(Object.entries(feats).map(([feat, val]) => [
          feat.replace(/_/g, ' '), typeof val === 'number' ? val.toFixed(6) : String(val), "", "Extracted feature"
        ])),
      ];

      if (selectedFormat === 'csv') {
        // Prepend UTF-8 BOM to make sure Excel opens special characters correctly
        const csvContent = "\uFEFF" + rows.map(row => row.map(val => `"${val.replace(/"/g, '""')}"`).join(",")).join("\n");
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.setAttribute("href", url);
        link.setAttribute("download", `${fileName}.csv`);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        showToast('success', 'CSV export completed successfully.', 3000);
      } else {
        // XML Spreadsheet 2003 format
        let xml = '<?xml version="1.0"?><?mso-application progid="Excel.Sheet"?>';
        xml += '<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" ';
        xml += 'xmlns:o="urn:schemas-microsoft-com:office:office" ';
        xml += 'xmlns:x="urn:schemas-microsoft-com:office:excel" ';
        xml += 'xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet" ';
        xml += 'xmlns:html="http://www.w3.org/TR/REC-html40">';
        xml += '<Worksheet ss:Name="Exoplanet Analysis"><Table>';
        
        rows.forEach(row => {
          xml += '<Row>';
          row.forEach(cell => {
            // Escape XML entities
            const safeCell = cell.replace(/&/g, '&amp;')
                                 .replace(/</g, '&lt;')
                                 .replace(/>/g, '&gt;')
                                 .replace(/"/g, '&quot;')
                                 .replace(/'/g, '&apos;');
            xml += `<Cell><Data ss:Type="String">${safeCell}</Data></Cell>`;
          });
          xml += '</Row>';
        });
        
        xml += '</Table></Worksheet></Workbook>';
        
        const blob = new Blob([xml], { type: 'application/vnd.ms-excel' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.setAttribute("href", url);
        link.setAttribute("download", `${fileName}.xls`);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        showToast('success', 'Excel export completed successfully.', 3000);
      }
    } catch (err: any) {
      console.error('Export error:', err);
      showToast('error', `Failed to export results: ${err.message}`, 4000);
    }
    
    setShowExportModal(false);
  };

  return (
    <>
      {/* PDF Generation Loading Overlay */}
      {isPdfLoading && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <div className="bg-gradient-to-br from-slate-900 to-slate-800 rounded-2xl p-8 border border-purple-500/30 max-w-sm w-full mx-4 text-center shadow-2xl">
            <div className="w-14 h-14 border-4 border-purple-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <h3 className="text-lg font-bold text-white mb-2">Generating PDF Report</h3>
            <p className="text-sm text-gray-400 mb-5">Building your scientific report with plots and analysis data...</p>
            {/* Animated progress bar */}
            <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
              <div className="h-full bg-gradient-to-r from-purple-500 to-indigo-400 rounded-full animate-pulse" style={{ width: '75%' }} />
            </div>
            <p className="text-xs text-gray-500 mt-3">This re-runs the full pipeline — may take 30–60s</p>
          </div>
        </div>
      )}

      <div className="space-y-2">
        <button
          onClick={() => setShowExportModal(true)}
          disabled={isPdfLoading}
          className="w-full bg-slate-700/50 hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg py-3 px-4 text-sm transition-all flex items-center justify-center gap-2"
        >
          <Download className="w-4 h-4" />
          Export Results
        </button>

        <button 
          onClick={onShare} 
          className="w-full bg-slate-700/50 hover:bg-slate-700 rounded-lg py-3 px-4 text-sm transition-all flex items-center justify-center gap-2"
        >
          <Share2 className="w-4 h-4" />
          Share Discovery
        </button>
      </div>

      {/* Export Format Modal */}
      {showExportModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="bg-gradient-to-br from-slate-900 to-slate-800 rounded-2xl p-6 border border-nasa-500/30 max-w-md w-full">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-bold text-white flex items-center gap-2">
                <Download className="w-5 h-5 text-nasa-400" />
                Export Results
              </h3>
              <button
                onClick={() => setShowExportModal(false)}
                className="text-gray-400 hover:text-white transition-colors"
                title="Close export modal"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4">
              <p className="text-sm text-gray-400">
                Choose your preferred export format for the analysis results:
              </p>

              {/* Format Selection */}
              <div className="space-y-3">
                {/* CSV Option */}
                <button
                  onClick={() => setSelectedFormat('csv')}
                  className={`w-full p-4 rounded-lg border-2 transition-all text-left ${
                    selectedFormat === 'csv'
                      ? 'border-nasa-500 bg-nasa-900/30'
                      : 'border-slate-700 bg-slate-700/30 hover:border-slate-600'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                      selectedFormat === 'csv' ? 'bg-nasa-600' : 'bg-slate-600'
                    }`}>
                      <FileText className="w-5 h-5 text-white" />
                    </div>
                    <div className="flex-1">
                      <h4 className="font-semibold text-white mb-0.5">CSV Format</h4>
                      <p className="text-xs text-gray-400">
                        Comma-separated values, compatible with Excel and data analysis tools
                      </p>
                    </div>
                    <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${
                      selectedFormat === 'csv' 
                        ? 'border-nasa-500 bg-nasa-500' 
                        : 'border-gray-500'
                    }`}>
                      {selectedFormat === 'csv' && (
                        <div className="w-2 h-2 bg-white rounded-full"></div>
                      )}
                    </div>
                  </div>
                </button>

                {/* XLSX Option */}
                <button
                  onClick={() => setSelectedFormat('xlsx')}
                  className={`w-full p-4 rounded-lg border-2 transition-all text-left ${
                    selectedFormat === 'xlsx'
                      ? 'border-nasa-500 bg-nasa-900/30'
                      : 'border-slate-700 bg-slate-700/30 hover:border-slate-600'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                      selectedFormat === 'xlsx' ? 'bg-green-600' : 'bg-slate-600'
                    }`}>
                      <FileSpreadsheet className="w-5 h-5 text-white" />
                    </div>
                    <div className="flex-1">
                      <h4 className="font-semibold text-white mb-0.5">XLSX Format</h4>
                      <p className="text-xs text-gray-400">
                        Excel spreadsheet format with formatting and multiple sheets support
                      </p>
                    </div>
                    <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${
                      selectedFormat === 'xlsx' 
                        ? 'border-nasa-500 bg-nasa-500' 
                        : 'border-gray-500'
                    }`}>
                      {selectedFormat === 'xlsx' && (
                        <div className="w-2 h-2 bg-white rounded-full"></div>
                      )}
                    </div>
                  </div>
                </button>

                {/* PDF Option */}
                <button
                  onClick={() => setSelectedFormat('pdf')}
                  className={`w-full p-4 rounded-lg border-2 transition-all text-left ${
                    selectedFormat === 'pdf'
                      ? 'border-purple-500 bg-purple-900/20'
                      : 'border-slate-700 bg-slate-700/30 hover:border-slate-600'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                      selectedFormat === 'pdf' ? 'bg-purple-600' : 'bg-slate-600'
                    }`}>
                      <FileDown className="w-5 h-5 text-white" />
                    </div>
                    <div className="flex-1">
                      <h4 className="font-semibold text-white mb-0.5">PDF Report</h4>
                      <p className="text-xs text-gray-400">
                        Full scientific report with all metrics, class probabilities, and XAI summary
                      </p>
                    </div>
                    <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${
                      selectedFormat === 'pdf'
                        ? 'border-purple-500 bg-purple-500'
                        : 'border-gray-500'
                    }`}>
                      {selectedFormat === 'pdf' && (
                        <div className="w-2 h-2 bg-white rounded-full"></div>
                      )}
                    </div>
                  </div>
                </button>

              </div>

              {/* Action Buttons */}
              <div className="flex gap-2 pt-2">
                <button
                  onClick={() => setShowExportModal(false)}
                  className="flex-1 bg-slate-700/50 hover:bg-slate-700 rounded-lg py-2 px-4 text-sm transition-all"
                >
                  Cancel
                </button>
                <button
                  onClick={handleExport}
                  className="flex-1 bg-gradient-to-r from-nasa-600 to-blue-600 hover:from-nasa-700 hover:to-blue-700 text-white rounded-lg py-2 px-4 text-sm font-medium transition-all flex items-center justify-center gap-2"
                >
                  <Download className="w-4 h-4" />
                  Export as {selectedFormat.toUpperCase()}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
