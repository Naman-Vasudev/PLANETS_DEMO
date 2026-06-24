/**
 * Footer Component - Application footer with team info
 * Exoplanet Vetting Platform
 */

import React from 'react';

/**
 * Main application footer with branding
 */
export const Footer: React.FC = () => (
  <footer className="relative z-10 mt-12 border-t border-nasa-500/30 bg-slate-900/50 backdrop-blur-lg">
    <div className="max-w-7xl mx-auto px-6 py-6">
      <div className="flex items-center justify-between">
        <div className="text-sm text-gray-400">
          © 2026 EXOPLANET HUNTERS. All rights reserved.
        </div>
        <div className="text-xs text-gray-500">
          Standalone Automated Vetting System
        </div>
      </div>
    </div>
  </footer>
);
