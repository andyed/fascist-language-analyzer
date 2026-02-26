import React from 'react';
import { ENTITY_CLASS_COLORS, ENTITY_CLASS_LABELS } from '../utils/graphHelpers';

// Toggle buttons for filtering entity nodes by class.
// visibleClasses is a Set of active class IDs; onToggle(classId) toggles one.
const EntityClassFilter = ({ classCounts, visibleClasses, onToggle }) => {
  const classes = Object.keys(classCounts);

  return (
    <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap', alignItems: 'center' }}>
      <span style={{ fontSize: '0.85rem', color: '#666', marginRight: '0.3rem' }}>Filter:</span>
      {classes.map(cls => {
        const isActive = visibleClasses.has(cls);
        const color = ENTITY_CLASS_COLORS[cls] || '#999';
        const label = ENTITY_CLASS_LABELS[cls] || cls;
        const count = classCounts[cls] || 0;
        return (
          <button
            key={cls}
            onClick={() => onToggle(cls)}
            style={{
              padding: '3px 10px',
              borderRadius: '14px',
              border: `2px solid ${color}`,
              background: isActive ? color : 'transparent',
              color: isActive ? '#fff' : color,
              cursor: 'pointer',
              fontSize: '0.82rem',
              fontWeight: 500,
              opacity: isActive ? 1 : 0.5,
              transition: 'all 0.2s',
              lineHeight: 1.4,
            }}
          >
            {label} ({count})
          </button>
        );
      })}
    </div>
  );
};

export default EntityClassFilter;
