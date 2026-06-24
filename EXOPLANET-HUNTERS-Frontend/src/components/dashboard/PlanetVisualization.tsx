/**
 * PlanetVisualization Component - Animated CSS exoplanet viewer
 * Exoplanet Vetting Platform
 *
 * Pure CSS + SVG implementation — no external 3D files, no network requests,
 * no IDM interference. Each planet type is styled to match real exoplanet
 * classification categories.
 */

import React, { useState, useEffect } from 'react';
import { Globe } from 'lucide-react';

interface PlanetConfig {
  id: number;
  name: string;
  type: string;
  description: string;
  /** CSS gradient for the sphere surface */
  gradient: string;
  /** Atmosphere glow colour */
  glow: string;
  /** Ring colour (empty string = no ring) */
  ring: string;
  /** Number of cloud/band stripes */
  bands: { top: string; colour: string; width: string }[];
}

const PLANETS: PlanetConfig[] = [
  {
    id: 1,
    name: 'Hot Jupiter',
    type: 'Gas Giant',
    description: 'Tidally-locked gas giant orbiting extremely close to its host star.',
    gradient: 'radial-gradient(circle at 35% 35%, #fbbf24, #f97316 45%, #dc2626 75%, #7f1d1d)',
    glow: 'rgba(251,146,60,0.6)',
    ring: '',
    bands: [
      { top: '28%', colour: 'rgba(220,38,38,0.35)', width: '12%' },
      { top: '44%', colour: 'rgba(251,191,36,0.25)', width: '8%'  },
      { top: '58%', colour: 'rgba(220,38,38,0.30)', width: '14%' },
    ],
  },
  {
    id: 2,
    name: 'Ice Giant',
    type: 'Neptune-like',
    description: 'Volatile-rich planet with deep methane atmosphere giving it a vivid blue hue.',
    gradient: 'radial-gradient(circle at 35% 35%, #bae6fd, #38bdf8 40%, #0369a1 70%, #0c4a6e)',
    glow: 'rgba(56,189,248,0.55)',
    ring: 'rgba(186,230,253,0.35)',
    bands: [
      { top: '32%', colour: 'rgba(255,255,255,0.20)', width: '9%'  },
      { top: '50%', colour: 'rgba(3,105,161,0.30)',   width: '11%' },
    ],
  },
  {
    id: 3,
    name: 'Super-Earth',
    type: 'Terrestrial',
    description: 'Rocky planet 1.5–2× Earth\'s radius, potentially habitable with liquid water.',
    gradient: 'radial-gradient(circle at 35% 35%, #86efac, #16a34a 45%, #15803d 65%, #14532d 85%, #0f172a)',
    glow: 'rgba(34,197,94,0.50)',
    ring: '',
    bands: [
      { top: '22%', colour: 'rgba(255,255,255,0.15)', width: '7%'  },
      { top: '60%', colour: 'rgba(30,64,175,0.25)',   width: '18%' },
    ],
  },
  {
    id: 4,
    name: 'Lava World',
    type: 'Ultra-hot',
    description: 'Extreme-temperature rocky planet covered in molten magma oceans.',
    gradient: 'radial-gradient(circle at 35% 35%, #fef08a, #f97316 30%, #dc2626 55%, #450a0a)',
    glow: 'rgba(239,68,68,0.70)',
    ring: 'rgba(239,68,68,0.25)',
    bands: [
      { top: '30%', colour: 'rgba(255,200,50,0.35)', width: '6%'  },
      { top: '50%', colour: 'rgba(185,28,28,0.40)',  width: '10%' },
      { top: '64%', colour: 'rgba(255,100,0,0.30)',  width: '8%'  },
    ],
  },
  {
    id: 5,
    name: 'Gas Giant',
    type: 'Jupiter-like',
    description: 'Massive banded gas giant with prominent equatorial storm systems.',
    gradient: 'radial-gradient(circle at 35% 35%, #e9d5ff, #a855f7 40%, #7e22ce 65%, #3b0764)',
    glow: 'rgba(168,85,247,0.55)',
    ring: 'rgba(233,213,255,0.40)',
    bands: [
      { top: '25%', colour: 'rgba(255,255,255,0.18)', width: '8%'  },
      { top: '38%', colour: 'rgba(107,33,168,0.35)',  width: '11%' },
      { top: '54%', colour: 'rgba(255,255,255,0.12)', width: '7%'  },
      { top: '66%', colour: 'rgba(91,33,182,0.30)',   width: '10%' },
    ],
  },
];

const MODEL_ROTATION_INTERVAL = 20000;

export const PlanetVisualization: React.FC = () => {
  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    const id = setInterval(
      () => setCurrentIndex((p) => (p + 1) % PLANETS.length),
      MODEL_ROTATION_INTERVAL,
    );
    return () => clearInterval(id);
  }, []);

  const planet = PLANETS[currentIndex];

  return (
    <div className="bg-slate-800/50 backdrop-blur-lg rounded-xl p-4 border border-nasa-500/20">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-nasa-300 flex items-center gap-2">
          <Globe className="w-4 h-4" />
          3D Exoplanet
        </h3>
        {/* Dot indicators */}
        <div className="flex items-center gap-1">
          {PLANETS.map((_, i) => (
            <button
              key={i}
              onClick={() => setCurrentIndex(i)}
              className={`rounded-full transition-all duration-300 ${
                i === currentIndex ? 'w-4 h-1.5 bg-nasa-400' : 'w-1.5 h-1.5 bg-gray-600 hover:bg-gray-500'
              }`}
              title={PLANETS[i].name}
            />
          ))}
        </div>
      </div>

      {/* Planet scene */}
      <div
        className="relative w-full rounded-lg overflow-hidden flex items-center justify-center"
        style={{
          height: 240,
          background: 'radial-gradient(ellipse at 50% 110%, #1e3a8a22 0%, #0f172a 70%)',
        }}
      >
        {/* Star field */}
        <StarField />

        {/* Outer glow */}
        <div
          className="absolute rounded-full"
          style={{
            width: 168,
            height: 168,
            background: `radial-gradient(circle, ${planet.glow} 0%, transparent 70%)`,
            filter: 'blur(18px)',
            animation: 'pulse 4s ease-in-out infinite',
          }}
        />

        {/* Ring (if applicable) */}
        {planet.ring && (
          <div
            className="absolute"
            style={{
              width: 220,
              height: 44,
              border: `6px solid ${planet.ring}`,
              borderRadius: '50%',
              transform: 'rotateX(72deg)',
              boxShadow: `0 0 12px ${planet.ring}`,
            }}
          />
        )}

        {/* Planet sphere */}
        <div
          className="relative rounded-full overflow-hidden"
          style={{
            width: 140,
            height: 140,
            background: planet.gradient,
            boxShadow: `0 0 30px ${planet.glow}, inset -20px -12px 40px rgba(0,0,0,0.55)`,
            animation: 'spin-planet 18s linear infinite',
          }}
        >
          {/* Atmospheric bands */}
          {planet.bands.map((band, i) => (
            <div
              key={i}
              className="absolute w-full"
              style={{
                top: band.top,
                height: band.width,
                background: band.colour,
                animation: `drift-band-${i % 2 === 0 ? 'a' : 'b'} ${14 + i * 3}s linear infinite`,
              }}
            />
          ))}

          {/* Specular highlight */}
          <div
            className="absolute rounded-full"
            style={{
              top: '12%',
              left: '18%',
              width: '32%',
              height: '28%',
              background: 'radial-gradient(circle, rgba(255,255,255,0.35) 0%, transparent 70%)',
              filter: 'blur(4px)',
            }}
          />
        </div>

        {/* Shadow terminator */}
        <div
          className="absolute rounded-full pointer-events-none"
          style={{
            width: 140,
            height: 140,
            background: 'radial-gradient(circle at 80% 50%, transparent 40%, rgba(0,0,0,0.65) 100%)',
            borderRadius: '50%',
          }}
        />
      </div>

      {/* Planet info */}
      <div className="mt-3 text-center">
        <p className="text-xs font-semibold text-white">{planet.name}</p>
        <p className="text-xs text-nasa-400 mt-0.5">{planet.type}</p>
        <p className="text-xs text-gray-500 mt-1 leading-relaxed px-1">{planet.description}</p>
      </div>

      {/* Manual selector buttons */}
      <div className="mt-3 flex justify-center gap-1.5">
        {PLANETS.map((p, i) => (
          <button
            key={p.id}
            onClick={() => setCurrentIndex(i)}
            className={`w-8 h-8 rounded-lg text-xs font-bold transition-all ${
              i === currentIndex
                ? 'bg-gradient-to-br from-nasa-600 to-blue-600 text-white shadow-lg scale-105'
                : 'bg-slate-700/50 text-gray-400 hover:bg-slate-600'
            }`}
            title={p.name}
          >
            {i + 1}
          </button>
        ))}
      </div>

      {/* CSS keyframes injected inline */}
      <style>{`
        @keyframes spin-planet {
          from { background-position: 0% 50%; }
          to   { filter: hue-rotate(0deg); transform: rotate(360deg); }
        }
        @keyframes drift-band-a {
          from { transform: translateX(-8%);  }
          to   { transform: translateX(8%);   }
        }
        @keyframes drift-band-b {
          from { transform: translateX(8%);   }
          to   { transform: translateX(-8%);  }
        }
        @keyframes pulse {
          0%, 100% { opacity: 0.7; transform: scale(1);    }
          50%       { opacity: 1.0; transform: scale(1.08); }
        }
        @keyframes twinkle {
          0%, 100% { opacity: 0.6; }
          50%       { opacity: 1.0; }
        }
      `}</style>
    </div>
  );
};

/** Tiny SVG star-field backdrop */
const StarField: React.FC = () => {
  const stars = React.useMemo(() => (
    Array.from({ length: 55 }, (_, i) => ({
      cx: Math.random() * 100,
      cy: Math.random() * 100,
      r:  Math.random() * 0.8 + 0.2,
      delay: Math.random() * 4,
    }))
  // eslint-disable-next-line react-hooks/exhaustive-deps
  ), []);

  return (
    <svg
      className="absolute inset-0 w-full h-full"
      viewBox="0 0 100 100"
      preserveAspectRatio="xMidYMid slice"
    >
      {stars.map((s, i) => (
        <circle
          key={i}
          cx={s.cx}
          cy={s.cy}
          r={s.r}
          fill="white"
          style={{
            animation: `twinkle ${2 + s.delay}s ease-in-out infinite`,
            animationDelay: `${s.delay}s`,
          }}
        />
      ))}
    </svg>
  );
};
