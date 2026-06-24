/**
 * NewsPanel Component - Latest exoplanet news
 * Exoplanet Vetting Platform
 */

import React, { useState, useEffect } from 'react';
import { Users, ExternalLink, Loader2 } from 'lucide-react';
import { COMMUNITY_NEWS } from '../../constants';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

interface NewsItem {
  title: string;
  author: string;
  source: string;
  url: string;
  time: string;
}

/**
 * Displays latest news about exoplanet discoveries dynamically fetched from the backend
 */
export const NewsPanel: React.FC = () => {
  const [news, setNews] = useState<NewsItem[]>(COMMUNITY_NEWS);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    const fetchNews = async () => {
      try {
        const response = await fetch(`${API_BASE}/news`);
        if (response.ok) {
          const data = await response.json();
          if (active && data.news && data.news.length > 0) {
            setNews(data.news);
          }
        }
      } catch (err) {
        console.error('Failed to fetch exoplanet news:', err);
      } finally {
        if (active) setLoading(false);
      }
    };

    fetchNews();
    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="bg-slate-800/50 backdrop-blur-lg rounded-xl p-4 border border-nasa-500/20">
      <h3 className="text-sm font-semibold mb-3 flex items-center justify-between">
        <span className="flex items-center gap-2">
          <Users className="w-4 h-4 text-nasa-400" />
          Latest Exoplanet News
        </span>
        {loading && <Loader2 className="w-3.5 h-3.5 text-nasa-400 animate-spin" />}
      </h3>
      <div className="space-y-3">
        {news.map((item, i) => (
          <a 
            key={i} 
            href={item.url} 
            target="_blank" 
            rel="noopener noreferrer" 
            className="flex items-start gap-3 p-2 bg-slate-700/30 rounded-lg hover:bg-slate-700/50 transition-colors cursor-pointer group"
          >
            <div className="flex-1 min-w-0">
              <div className="text-xs font-medium text-white group-hover:text-nasa-400 transition-colors flex items-center gap-1 flex-wrap leading-tight">
                {item.title}
                <ExternalLink className="w-3 h-3 inline shrink-0" />
              </div>
              <div className="text-[10px] text-gray-400 truncate mt-1">{item.author}</div>
              <div className="text-[10px] text-gray-500">{item.source} • {item.time}</div>
            </div>
          </a>
        ))}
      </div>
    </div>
  );
};
