import React from 'react';

export function ScoreBadge({ score }: { score?: number }) {
  const s = typeof score === 'number' ? score : undefined;
  const color = s === undefined ? '#666' : s >= 80 ? '#2ecc71' : s >= 60 ? '#f1c40f' : '#e74c3c';
  const label = s === undefined ? 'N/A' : `${s}`;
  return (
    <span style={{
      background: color,
      color: '#000',
      borderRadius: 8,
      padding: '2px 8px',
      fontWeight: 600,
      fontSize: 12
    }}>{label}</span>
  );
}


