import React from 'react';

// Panel showing evidence quotes for a selected entity-theme edge.
// Reuses the parent's buildLocalSourceUrlForPage for source links.
const EvidencePanel = ({ edge, scoreMode, chunkPages, buildLocalSourceUrlForPage }) => {
  if (!edge) return null;

  return (
    <div style={{ background: '#fafafa', border: '1px solid #eee', borderRadius: '8px', padding: '1rem', marginBottom: '1rem' }}>
      <h3 style={{ marginTop: 0 }}>{edge.entity_label} ↔ {edge.theme}</h3>
      <p style={{ marginTop: 0, color: '#666' }}>
        Score ({edge.score_mode || scoreMode}): {edge.weight} · Raw weight: {edge.raw_weight ?? edge.weight} · Lift: {edge.lift ?? 'n/a'} · PMI: {edge.pmi ?? 'n/a'} · Matches: {edge.count}
      </p>
      {(edge.evidence || []).map((ev, i) => {
        const quote = typeof ev === 'string' ? ev : ev.quote;
        const chunkId = typeof ev === 'string' ? null : ev.chunk_id;
        const localEvidenceSource = buildLocalSourceUrlForPage(
          chunkId !== null && chunkId !== undefined ? chunkPages?.[String(chunkId)] : null,
          quote
        );
        return (
          <blockquote key={i} style={{ margin: '0.5rem 0', paddingLeft: '0.8rem', borderLeft: '3px solid #ddd' }}>
            <div>{quote}</div>
            <div style={{ color: '#666', fontSize: '0.85rem', marginTop: '0.3rem' }}>
              {chunkId !== null && chunkId !== undefined ? <>Chunk {chunkId}</> : <>Chunk n/a</>}
              {' · '}<a href={localEvidenceSource} target="_blank" rel="noreferrer">Source doc</a>
            </div>
          </blockquote>
        );
      })}
    </div>
  );
};

export default EvidencePanel;
