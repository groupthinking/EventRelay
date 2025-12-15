
import React from 'react';
import { LayerDefinition } from '../types';

interface LayerCardProps {
  layer: LayerDefinition;
}

const LayerCard: React.FC<LayerCardProps> = ({ layer }) => {
  // Simple hash function for stable key generation for points (not cryptographically secure)
  const hashCode = (s: string): number => {
    let hash = 0;
    for (let i = 0; i < s.length; i++) {
      const character = s.charCodeAt(i);
      hash = ((hash << 5) - hash) + character;
      hash |= 0; // Convert to 32bit integer
    }
    return hash;
  };
  
  return (
    <div className="bg-white p-6 rounded-xl shadow-xl border border-slate-300 w-full max-w-3xl mx-auto hover:shadow-2xl transition-shadow duration-300">
      <h3 className="text-xl font-semibold text-sky-600 mb-1 text-center">{layer.title}</h3>
      {layer.subtitle && (
        <p className="text-sm text-slate-500 mb-4 text-center italic">{layer.subtitle}</p>
      )}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-2 px-2">
        {layer.points.map((point, index) => (
          <div key={`${hashCode(point)}-${index}`} className="text-sm text-slate-700 flex items-start">
            <span className="text-sky-500 mr-2 mt-1">&#9679;</span> {/* Small circle bullet */}
            <span>{point.startsWith('- ') ? point.substring(2) : point}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default LayerCard;
