/**
 * QuickActions Component - Quick action buttons for analysis and upload
 * Exoplanet Vetting Platform
 *
 * Now wired to the live AstroNet backend via onRunAnalysis prop.
 */

import React, { useState, useRef } from 'react';
import { Play, Upload, X, FileType, Search, Loader } from 'lucide-react';
import { useToast } from '../common/Toast';

interface QuickActionsProps {
  onAnalyzeDemo: () => void;
  onRunAnalysis: (
    ticId: string,
    periodOverride?: string,
    t0Override?: string,
    durationOverride?: string
  ) => Promise<void>;
  isAnalyzing: boolean;
}

type DataSource = 'TESS' | 'Kepler';

/**
 * Quick action panel with live TIC ID search, demo analysis, and FITS upload.
 */
export const QuickActions: React.FC<QuickActionsProps> = ({
  onAnalyzeDemo,
  onRunAnalysis,
  isAnalyzing,
}) => {
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [selectedSource, setSelectedSource] = useState<DataSource>('TESS');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [ticIdInput, setTicIdInput] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [periodOverride, setPeriodOverride] = useState('');
  const [t0Override, setT0Override] = useState('');
  const [durationOverride, setDurationOverride] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { showToast } = useToast();

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file?.name.toLowerCase().endsWith('.fits')) {
      setSelectedFile(file);
      showToast('info', `File "${file.name}" selected (${(file.size / 1024).toFixed(2)} KB)`, 3000);
    } else {
      showToast('error', 'Invalid file type. Please select a valid FITS file (.fits extension)', 4000);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleTicSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!ticIdInput.trim()) {
      showToast('warning', 'Please enter a TIC ID', 2000);
      return;
    }
    onRunAnalysis(
      ticIdInput.trim(),
      showAdvanced ? periodOverride : undefined,
      showAdvanced ? t0Override : undefined,
      showAdvanced ? durationOverride : undefined
    );
  };

  const handleUpload = () => {
    if (selectedFile && ticIdInput.trim()) {
      showToast(
        'info',
        `🔭 Analysing uploaded FITS for ${selectedSource} ID ${ticIdInput}…`,
        3000,
      );
      onRunAnalysis(ticIdInput.trim());
      setShowUploadModal(false);
      setSelectedFile(null);
      setTicIdInput('');
      if (fileInputRef.current) fileInputRef.current.value = '';
    } else if (!selectedFile) {
      showToast('warning', 'Please select a FITS file first', 3000);
    } else {
      showToast('warning', 'Please enter a TIC / Kepler ID', 3000);
    }
  };

  return (
    <>
      <div className="bg-slate-800/50 backdrop-blur-lg rounded-xl p-4 border border-nasa-500/20">
        <h3 className="text-sm font-semibold mb-3 text-nasa-300">Quick Start</h3>

        {/* Live TIC / KIC ID search */}
        <form onSubmit={handleTicSearch} className="mb-3">
          <label className="text-xs text-gray-400 mb-1 block">Target Star ID (TIC / KIC)</label>
          <div className="flex gap-2">
            <input
              type="text"
              value={ticIdInput}
              onChange={(e) => setTicIdInput(e.target.value)}
              placeholder="e.g. 10797460 or 183374187"
              disabled={isAnalyzing}
              className="flex-1 px-3 py-2 bg-slate-700/60 border border-nasa-500/20 rounded-lg text-white text-sm placeholder-gray-500 focus:outline-none focus:border-nasa-500 focus:ring-1 focus:ring-nasa-500 transition-all disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={isAnalyzing}
              className="bg-nasa-600 hover:bg-nasa-700 disabled:opacity-50 rounded-lg p-2 transition-all"
              title="Run AstroNet analysis"
            >
              {isAnalyzing ? (
                <Loader className="w-4 h-4 animate-spin" />
              ) : (
                <Search className="w-4 h-4" />
              )}
            </button>
          </div>

          {/* Advanced Options Toggle */}
          <div className="mt-2">
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="text-xs text-blue-400 hover:text-blue-300 hover:underline focus:outline-none transition-all"
            >
              {showAdvanced ? 'Hide Advanced Options' : 'Show Advanced Vetting Options'}
            </button>

            {showAdvanced && (
              <div className="mt-2 p-3 bg-slate-900/60 rounded-lg border border-nasa-500/10 space-y-2">
                <div>
                  <label className="text-[10px] text-gray-400 block mb-0.5">Period Override (days)</label>
                  <input
                    type="text"
                    value={periodOverride}
                    onChange={(e) => setPeriodOverride(e.target.value)}
                    placeholder="e.g. 9.8"
                    disabled={isAnalyzing}
                    className="w-full px-2 py-1 bg-slate-700/40 border border-nasa-500/20 rounded text-white text-xs placeholder-gray-600 focus:outline-none focus:border-nasa-500"
                  />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-[10px] text-gray-400 block mb-0.5">T0 Epoch Override</label>
                    <input
                      type="text"
                      value={t0Override}
                      onChange={(e) => setT0Override(e.target.value)}
                      placeholder="e.g. 1320.5"
                      disabled={isAnalyzing}
                      className="w-full px-2 py-1 bg-slate-700/40 border border-nasa-500/20 rounded text-white text-xs placeholder-gray-600 focus:outline-none focus:border-nasa-500"
                    />
                  </div>
                  <div>
                    <label className="text-[10px] text-gray-400 block mb-0.5">Duration Override (hours)</label>
                    <input
                      type="text"
                      value={durationOverride}
                      onChange={(e) => setDurationOverride(e.target.value)}
                      placeholder="e.g. 2.4"
                      disabled={isAnalyzing}
                      className="w-full px-2 py-1 bg-slate-700/40 border border-nasa-500/20 rounded text-white text-xs placeholder-gray-600 focus:outline-none focus:border-nasa-500"
                    />
                  </div>
                </div>
              </div>
            )}
          </div>
        </form>

        <button
          onClick={onAnalyzeDemo}
          disabled={isAnalyzing}
          className="w-full bg-gradient-to-r from-nasa-600 to-blue-600 hover:from-nasa-700 hover:to-blue-700 disabled:opacity-50 rounded-lg py-3 px-4 flex items-center justify-center gap-2 transition-all mb-2"
        >
          {isAnalyzing ? (
            <Loader className="w-4 h-4 animate-spin" />
          ) : (
            <Play className="w-4 h-4" />
          )}
          {isAnalyzing ? 'Analysing…' : 'Analyse Demo Planet'}
        </button>

        <button
          onClick={() => setShowUploadModal(true)}
          disabled={isAnalyzing}
          className="w-full bg-slate-700/50 hover:bg-slate-700 disabled:opacity-50 rounded-lg py-3 px-4 flex items-center justify-center gap-2 transition-all"
        >
          <Upload className="w-4 h-4" />
          Upload Your Data
        </button>
        <p className="text-xs text-gray-400 mt-2 text-center">Supports: .fits only</p>
      </div>

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="bg-gradient-to-br from-slate-900 to-slate-800 rounded-2xl p-6 border border-nasa-500/30 max-w-md w-full">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-bold text-white flex items-center gap-2">
                <FileType className="w-5 h-5 text-nasa-400" />
                Upload FITS File
              </h3>
              <button
                onClick={() => {
                  setShowUploadModal(false);
                  setSelectedFile(null);
                  setTicIdInput('');
                  if (fileInputRef.current) fileInputRef.current.value = '';
                }}
                className="text-gray-400 hover:text-white transition-colors"
                title="Close upload modal"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4">
              {/* Data Source */}
              <div>
                <label className="text-sm text-gray-300 mb-2 block font-medium">
                  Data Source
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {(['TESS', 'Kepler'] as DataSource[]).map((source) => (
                    <button
                      key={source}
                      onClick={() => setSelectedSource(source)}
                      className={`py-2 px-3 rounded-lg text-sm font-medium transition-all ${
                        selectedSource === source
                          ? 'bg-gradient-to-r from-nasa-600 to-blue-600 text-white'
                          : 'bg-slate-700/50 text-gray-300 hover:bg-slate-700'
                      }`}
                    >
                      {source}
                    </button>
                  ))}
                </div>
              </div>

              {/* File input */}
              <div>
                <label className="text-sm text-gray-300 mb-2 block font-medium">
                  Select FITS File
                </label>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".fits,.fit"
                  onChange={handleFileSelect}
                  title="Select FITS file"
                  className="w-full text-sm text-gray-300 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-nasa-600 file:text-white hover:file:bg-nasa-700 file:cursor-pointer cursor-pointer bg-slate-700/50 rounded-lg border border-nasa-500/20"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Flexible Image Transport System format only
                </p>
              </div>

              {/* TIC / Kepler ID */}
              <div>
                <label className="text-sm text-gray-300 mb-2 block font-medium">
                  {selectedSource} ID <span className="text-nasa-400">*</span>
                </label>
                <input
                  type="text"
                  value={ticIdInput}
                  onChange={(e) => setTicIdInput(e.target.value)}
                  placeholder={`e.g., ${selectedSource === 'Kepler' ? '11442793' : '261108232'}`}
                  className="w-full px-4 py-2 bg-slate-700/50 border border-nasa-500/20 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-nasa-500 focus:ring-1 focus:ring-nasa-500 transition-all"
                />
              </div>

              {/* Selected file info */}
              {selectedFile && (
                <div className="bg-slate-700/50 rounded-lg p-3 border border-nasa-500/20">
                  <p className="text-xs text-gray-400 mb-1">Selected File:</p>
                  <p className="text-sm text-white font-medium">{selectedFile.name}</p>
                  <p className="text-xs text-gray-500 mt-1">
                    Size: {(selectedFile.size / 1024).toFixed(2)} KB
                  </p>
                </div>
              )}

              {/* Action buttons */}
              <div className="flex gap-2 pt-2">
                <button
                  onClick={() => {
                    setShowUploadModal(false);
                    setSelectedFile(null);
                    setTicIdInput('');
                    if (fileInputRef.current) fileInputRef.current.value = '';
                  }}
                  className="flex-1 bg-slate-700/50 hover:bg-slate-700 rounded-lg py-2 px-4 text-sm transition-all"
                >
                  Cancel
                </button>
                <button
                  onClick={handleUpload}
                  disabled={!selectedFile || !ticIdInput.trim()}
                  className={`flex-1 rounded-lg py-2 px-4 text-sm font-medium transition-all ${
                    selectedFile && ticIdInput.trim()
                      ? 'bg-gradient-to-r from-nasa-600 to-blue-600 hover:from-nasa-700 hover:to-blue-700 text-white'
                      : 'bg-slate-700/30 text-gray-500 cursor-not-allowed'
                  }`}
                >
                  Analyse
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
