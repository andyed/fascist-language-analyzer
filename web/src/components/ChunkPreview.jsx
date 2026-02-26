import React from 'react';
import { Link } from 'react-router-dom';
import { TRAIT_COLORS } from '../utils/graphHelpers';

// Popover panel for a clicked chunk node on the rhetoric graph.
// Shows summary, connected traits, and source link.
const ChunkPreview = ({ chunk, page, connectedTraits, sourceUrl, onClose }) => {
  if (!chunk) return null;

  return (
    <div
      style={{
        position: 'absolute',
        top: '60px',
        right: '16px',
        width: '380px',
        maxHeight: 'calc(100vh - 140px)',
        overflowY: 'auto',
        background: '#fff',
        borderRadius: '10px',
        boxShadow: '0 4px 20px rgba(0,0,0,0.18)',
        padding: '1.2rem',
        zIndex: 200,
        fontSize: '0.9rem',
        lineHeight: 1.5,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.6rem' }}>
        <div>
          <strong style={{ fontSize: '1rem' }}>{chunk.id}</strong>
          {page && (
            <span style={{ color: '#888', marginLeft: '0.5rem', fontSize: '0.85rem' }}>
              est. page {page}
            </span>
          )}
        </div>
        <button
          onClick={onClose}
          style={{
            background: 'none', border: 'none', cursor: 'pointer',
            fontSize: '1.2rem', color: '#999', padding: '0 4px', lineHeight: 1,
          }}
          aria-label="Close"
        >
          &times;
        </button>
      </div>

      {chunk.desc && (
        <p style={{ margin: '0 0 0.8rem 0', color: '#444' }}>
          {chunk.desc}
        </p>
      )}

      {connectedTraits.length > 0 && (
        <div style={{ marginBottom: '0.8rem' }}>
          <div style={{ fontSize: '0.8rem', color: '#888', marginBottom: '0.3rem' }}>Connected traits:</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.3rem' }}>
            {connectedTraits.map(trait => (
              <Link
                key={trait.name}
                to={`/theme/${encodeURIComponent(trait.name)}`}
                onClick={onClose}
                style={{
                  display: 'inline-block',
                  padding: '2px 8px',
                  borderRadius: '12px',
                  background: TRAIT_COLORS[trait.name] || '#eee',
                  color: '#333',
                  fontSize: '0.8rem',
                  textDecoration: 'none',
                  border: '1px solid rgba(0,0,0,0.08)',
                }}
              >
                {trait.name}
                {trait.confidence != null && (
                  <span style={{ opacity: 0.6, marginLeft: '3px' }}>
                    {trait.confidence.toFixed(2)}
                  </span>
                )}
              </Link>
            ))}
          </div>
        </div>
      )}

      {sourceUrl && (
        <a
          href={sourceUrl}
          target="_blank"
          rel="noreferrer"
          style={{
            display: 'inline-block',
            padding: '6px 12px',
            background: '#f0f0f0',
            borderRadius: '6px',
            color: '#333',
            textDecoration: 'none',
            fontSize: '0.85rem',
          }}
        >
          View in source document &rarr;
        </a>
      )}
    </div>
  );
};

export default ChunkPreview;
