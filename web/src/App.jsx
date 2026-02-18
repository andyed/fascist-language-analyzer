
import React, { useState, useEffect } from 'react';
import { HashRouter as Router, Routes, Route, Link, useParams } from 'react-router-dom';
import ForceGraph2D from 'react-force-graph-2d';

// --- Shared Data/Configs ---
const TRAIT_COLORS = {
  "Cult of Tradition": "#ffcccc",
  "Rejection of Modernism": "#ffe5cc",
  "Action for Action's Sake": "#ffffcc",
  "Disagreement is Treason": "#e5ffcc",
  "Fear of Difference": "#ccffcc",
  "Appeal to Social Frustration": "#ccffe5",
  "Obsession with a Plot": "#ccffff",
  "Enemy is Strong and Weak": "#cce5ff",
  "Pacifism is Trafficking with the Enemy": "#ccccff",
  "Contempt for the Weak": "#e5ccff",
  "Everybody is Educated to Become a Hero": "#ffccff",
  "Machismo and Weaponry": "#ffcce5",
  "Selective Populism": "#e0e0e0",
  "Ur-Fascism Speaks Newspeak": "#ff9999"
};

// --- Components ---

const Nav = () => (
  <nav style={{ padding: '1rem', background: '#333', color: 'white', display: 'flex', gap: '1rem', justifyContent: 'center' }}>
    <Link to="/" style={{ color: 'white' }}>Home (Graph)</Link>
    <Link to="/themes" style={{ color: 'white' }}>Analysis by Theme</Link>
    <Link to="/entities" style={{ color: 'white' }}>Entities</Link>
    <Link to="/entity-themes" style={{ color: 'white' }}>Entity × Themes</Link>
    <a href="../entities/index.html" style={{ color: 'white' }}>Static Entity Index</a>
  </nav>
);

const Sparkline = ({ counts, color }) => {
  // Simple SVG sparkline
  const height = 30;
  const width = 100;
  const max = Math.max(...counts, 1);

  // Create points for polyline
  const points = counts.map((val, i) => {
    const x = (i / (counts.length - 1)) * width;
    const y = height - (val / max) * height;
    return `${x},${y}`;
  }).join(' ');

  return (
    <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" style={{ display: 'block', marginTop: '5px' }}>
      <polyline
        fill="none"
        stroke="#666"
        strokeWidth="1"
        points={points}
      />
      <polygon
        fill={color}
        fillOpacity={0.5}
        points={`0,${height} ${points} ${width},${height}`}
      />
    </svg>
  );
};


// --- Helper for Color Gradient ---
// Simple linear interpolation between two colors
const interpolateColor = (color1, color2, factor = 0.5) => {
  const result = color1.slice();
  for (let i = 0; i < 3; i++) {
    result[i] = Math.round(result[i] + factor * (color2[i] - color1[i]));
  }
  return `rgb(${result[0]}, ${result[1]}, ${result[2]})`;
};

const hexToRgb = (hex) => {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result ? [
    parseInt(result[1], 16),
    parseInt(result[2], 16),
    parseInt(result[3], 16)
  ] : null;
}

const START_COLOR = hexToRgb("#e0f7fa"); // Light Cyan (Start)
const END_COLOR = hexToRgb("#ff5252");   // Red Accent (End)

const GraphView = () => {
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [maxChunkId, setMaxChunkId] = useState(1);

  useEffect(() => {
    fetch('./graph_data.json')
      .then(res => res.json())
      .then(data => {
        // Find max chunk ID for normalization
        let maxId = 0;
        data.nodes.forEach(n => {
          if (n.group === 'chunk') {
            const idParams = n.id.split(' ');
            if (idParams.length > 1) {
              const idVal = parseInt(idParams[1]);
              if (idVal > maxId) maxId = idVal;
            }
          }
        });
        setMaxChunkId(maxId);

        // Filter out unconnected nodes (e.g. traits with 0 occurrences)
        const connectedNodeIds = new Set();
        data.links.forEach(l => {
          connectedNodeIds.add(l.source);
          connectedNodeIds.add(l.target);
        });

        const activeNodes = data.nodes.filter(n => connectedNodeIds.has(n.id));
        const activeNodeIds = new Set(activeNodes.map(n => n.id));
        const activeLinks = data.links.filter(l => activeNodeIds.has(l.source) && activeNodeIds.has(l.target));

        setGraphData({ nodes: activeNodes, links: activeLinks });
      });
  }, []);

  return (
    <div style={{ height: 'calc(100vh - 60px)', position: 'relative' }}>
      <div style={{ position: 'absolute', top: '10px', left: '10px', background: 'rgba(255,255,255,0.8)', padding: '10px', borderRadius: '5px', pointerEvents: 'none', zIndex: 100 }}>
        <h2 style={{ margin: 0 }}>Project 2025 Rhetoric Graph</h2>
        <small>Powered by Gemini-3-Flash</small>
        <div style={{ marginTop: '10px', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '5px' }}>
          <span>Doc Start</span>
          <div style={{ width: '60px', height: '10px', background: 'linear-gradient(to right, #e0f7fa, #ff5252)' }}></div>
          <span>Doc End</span>
        </div>
      </div>
      <ForceGraph2D
        graphData={graphData}
        // Use structural links for physics, but make them invisible/faint
        linkColor={link => link.type === 'structural' ? 'rgba(0,0,0,0)' : '#eee'}
        linkWidth={link => link.type === 'structural' ? 0 : 1}

        // Physics Tuning for reduced overlap
        d3AlphaDecay={0.02} // Slower decay = more time to settle
        d3VelocityDecay={0.3} // Less friction
        cooldownTicks={100}
        onEngineStop={() => console.log('Engine stopped')}

        // Custom Forces
        d3Force={(d3Graph, force) => {
          // Increase repulsion significantly
          d3Graph.force('charge').strength(-120);
          d3Graph.force('link').distance(link => link.type === 'structural' ? 50 : 100);

          // Add collision to prevent overlap
          // We need to import d3 for this or rely on exposed props? 
          // force-graph exposes d3Force to modify existing forces, 
          // or we can add new ones if we had access to d3.
          // Since we don't have d3 imported here easily, rely on standard props
        }}

        backgroundColor="#ffffff"
        nodeCanvasObject={(node, ctx, globalScale) => {
          const label = node.id;
          const isTrait = node.group === 'trait';
          const fontSize = (isTrait ? 14 : 4) / globalScale; // Traits larger
          ctx.font = `${isTrait ? 'bold' : ''} ${fontSize}px Sans-Serif`;

          // Determine Node Color
          let nodeColor = node.color || '#ccc';
          if (!isTrait) {
            const idParams = node.id.split(' ');
            if (idParams.length > 1) {
              const idVal = parseInt(idParams[1]);
              const ratio = idVal / maxChunkId;
              nodeColor = interpolateColor(START_COLOR, END_COLOR, ratio);
            }
          }

          if (!isTrait) {
            // Chunk Nodes: Less intrusive, no text label by default
            // Just a small colored square/circle
            const size = 6;
            ctx.fillStyle = nodeColor;
            ctx.globalAlpha = 0.8;
            ctx.fillRect(node.x - size / 2, node.y - size / 2, size, size);
            ctx.globalAlpha = 1.0;

            // Only draw label on hover? 
            // nodeCanvasObject doesn't easily know hover state without state management.
            // For now, OMIT label as requested to reduce jam.
          } else {
            // Trait Nodes: Draw Box + Text
            const labelWithCount = `${label} (${node.val})`;
            const textWidth = ctx.measureText(labelWithCount).width;
            const bckgDimensions = [textWidth, fontSize].map(n => n + fontSize * 0.4);

            ctx.fillStyle = nodeColor;
            ctx.fillRect(node.x - bckgDimensions[0] / 2, node.y - bckgDimensions[1] / 2, ...bckgDimensions);

            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillStyle = '#222';
            ctx.fillText(labelWithCount, node.x, node.y);
          }

          // Re-use dim for pointer area (make sure chunks have a hit area)
          node.__bckgDimensions = isTrait ?
            [ctx.measureText(`${label} (${node.val})`).width + fontSize * 0.4, fontSize * 1.4] :
            [8, 8];
        }}
        nodePointerAreaPaint={(node, color, ctx) => {
          ctx.fillStyle = color;
          const bckgDimensions = node.__bckgDimensions;
          bckgDimensions && ctx.fillRect(node.x - bckgDimensions[0] / 2, node.y - bckgDimensions[1] / 2, ...bckgDimensions);
        }}
        onNodeClick={node => {
          if (node.group === 'trait') {
            window.location.hash = `#/theme/${encodeURIComponent(node.id)}`;
          } else if (node.desc) {
            alert(`${node.id}: ${node.desc}`);
          }
        }}
      />
    </div>
  );
};

const Tooltip = ({ text, children }) => {
  const [isVisible, setIsVisible] = useState(false);

  return (
    <div
      style={{ position: 'relative', display: 'inline-block', marginLeft: '0.5rem', cursor: 'help' }}
      onMouseEnter={() => setIsVisible(true)}
      onMouseLeave={() => setIsVisible(false)}
    >
      {children}
      {isVisible && (
        <div style={{
          position: 'absolute',
          bottom: '100%',
          left: '50%',
          transform: 'translateX(-50%)',
          background: '#333',
          color: '#fff',
          padding: '0.5rem',
          borderRadius: '4px',
          width: '250px',
          fontSize: '0.8rem',
          zIndex: 1000,
          marginBottom: '5px',
          boxShadow: '0 2px 4px rgba(0,0,0,0.2)'
        }}>
          {text}
          <div style={{
            position: 'absolute',
            top: '100%',
            left: '50%',
            marginLeft: '-5px',
            borderWidth: '5px',
            borderStyle: 'solid',
            borderColor: '#333 transparent transparent transparent'
          }} />
        </div>
      )}
    </div>
  );
};

const ThemeList = () => {
  const [stats, setStats] = useState({});
  const [sortedTraits, setSortedTraits] = useState([]);

  useEffect(() => {
    fetch('./data.json').then(res => res.json()).then(data => {
      // Bin data for sparklines (e.g., 50 bins)
      const numBins = 50;
      const totalChunks = data.length || 1;
      const chunkSize = Math.ceil(totalChunks / numBins);

      const newStats = {};
      const totals = {};

      Object.keys(TRAIT_COLORS).forEach(trait => {
        const bins = new Array(numBins).fill(0);
        let total = 0;
        data.forEach(chunk => {
          const binIdx = Math.min(Math.floor((chunk.chunk_id || 0) / chunkSize), numBins - 1);
          const hasTrait = chunk.concepts.some(c => c.trait === trait);
          if (hasTrait) {
            bins[binIdx]++;
            total++;
          }
        });
        newStats[trait] = bins;
        totals[trait] = total;
      });
      setStats(newStats);

      // Sort traits by count descending
      const sorted = Object.entries(TRAIT_COLORS)
        .map(([trait, color]) => ({ trait, color, count: totals[trait] || 0 }))
        .sort((a, b) => b.count - a.count);

      setSortedTraits(sorted);
    });
  }, []);

  const definitions = {
    "Cult of Tradition": "Truth is already known; we must only interpret the obscure messages of the past.",
    "Rejection of Modernism": "The Enlightenment, the Age of Reason is seen as the beginning of modern depravity.",
    "Action for Action's Sake": "Thinking is a form of emasculation. Culture is suspect.",
    "Disagreement is Treason": "The critical spirit makes distinctions, and to distinguish is a sign of modernism.",
    "Fear of Difference": "The first appeal of a fascist movement is an appeal against the intruders.",
    "Appeal to Social Frustration": "Appeal to a frustrated middle class, suffering from crisis or humiliation.",
    "Obsession with a Plot": "The followers must feel besieged. The easiest way to solve the plot is xenophobia.",
    "Enemy is Strong and Weak": "The enemies are at the same time too strong and too weak.",
    "Pacifism is Trafficking with the Enemy": "Life is permanent warfare.",
    "Contempt for the Weak": "Elitism is a typical aspect of any reactionary ideology.",
    "Everybody is Educated to Become a Hero": "In Ur-Fascism, heroism is the norm.",
    "Machismo and Weaponry": "Disdain for women and intolerance of nonstandard sexual habits.",
    "Selective Populism": "The People is conceived as a quality, a monolithic entity expressing the Common Will.",
    "Ur-Fascism Speaks Newspeak": "Impoverished vocabulary and elementary syntax to limit critical reasoning."
  };

  return (
    <div style={{ padding: '3rem', maxWidth: '1200px', margin: '0 auto' }}>
      <header style={{ marginBottom: '3rem', textAlign: 'center' }}>
        <h1 style={{ marginBottom: '1rem' }}>Analysis by Theme</h1>
        <p style={{ maxWidth: '800px', margin: '0 auto', color: '#666', lineHeight: 1.6 }}>
          This analysis maps the text against <strong>Umberto Eco's 14 properties of Ur-Fascism</strong>.
          Eco argues that fascism is a "syndrome"—a cluster of rhetorical features that can appear in different combinations.
          It is enough for just one of them to be present for fascism to coagulate around it.
        </p>
      </header>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '3rem' }}>
        {sortedTraits.map(({ trait, color, count }) => (
          <div key={trait} style={{ minHeight: '100%' }}>
            <Link
              to={`/theme/${encodeURIComponent(trait)}`}
              style={{ textDecoration: 'none', color: 'inherit', display: 'block', height: '100%' }}
            >
              <div
                style={{
                  position: 'relative',
                  background: '#f9f9f9',
                  border: '1px solid #eee',
                  borderTop: `4px solid ${color}`,
                  borderRadius: '8px',
                  padding: '1.5rem',
                  boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
                  display: 'flex',
                  flexDirection: 'column',
                  height: '100%',
                  overflow: 'hidden',
                  transition: 'transform 0.2s, box-shadow 0.2s',
                  cursor: 'pointer'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.transform = 'translateY(-4px)';
                  e.currentTarget.style.boxShadow = '0 8px 16px rgba(0,0,0,0.1)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = 'none';
                  e.currentTarget.style.boxShadow = '0 2px 4px rgba(0,0,0,0.05)';
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
                  <div style={{ display: 'flex', flexDirection: 'column' }}>
                    <span style={{
                      fontWeight: 'bold',
                      fontSize: '1.1rem',
                      color: '#333'
                    }}>
                      {trait}
                    </span>
                    <span style={{ fontSize: '0.9rem', color: '#666', marginTop: '0.2rem' }}>
                      {count} instances
                    </span>
                  </div>
                  <div onClick={(e) => e.preventDefault()}>
                    <Tooltip text={definitions[trait]}>
                      <div style={{
                        background: '#eee',
                        borderRadius: '50%',
                        width: '20px',
                        height: '20px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        fontSize: '0.8rem',
                        fontWeight: 'bold',
                        color: '#666'
                      }}>?</div>
                    </Tooltip>
                  </div>
                </div>

                <div style={{ marginTop: '1rem', minHeight: '40px' }}>
                  {stats[trait] && <Sparkline counts={stats[trait]} color={color} />}
                </div>
              </div>
            </Link>
          </div>
        ))}
      </div>
    </div>
  );
};

const ThemePage = () => {
  const { traitId } = useParams();
  const decodedTrait = decodeURIComponent(traitId);
  const [quotes, setQuotes] = useState([]);

  useEffect(() => {
    fetch('./data.json')
      .then(res => res.json())
      .then(data => {
        const relevant = [];
        data.forEach(chunk => {
          chunk.concepts.forEach(concept => {
            if (concept.trait === decodedTrait) {
              relevant.push({ ...concept, chunk_id: chunk.chunk_id });
            }
          });
        });
        setQuotes(relevant);
      });
  }, [decodedTrait]);

  const color = TRAIT_COLORS[decodedTrait] || '#eee';

  return (
    <div style={{ padding: '2rem', maxWidth: '800px', margin: '0 auto' }}>
      <Link to="/themes" style={{ display: 'inline-block', marginBottom: '1rem', color: '#666', textDecoration: 'none' }}>← Back to Themes</Link>
      <div style={{ borderBottom: `4px solid ${color}`, marginBottom: '2rem' }}>
        <h1>{decodedTrait}</h1>
        <p>{quotes.length} instances found</p>
      </div>

      {quotes.map((q, i) => (
        <div key={i} style={{ background: '#f9f9f9', padding: '1rem', borderRadius: '8px', marginBottom: '1rem', borderLeft: `4px solid ${color}` }}>
          <blockquote style={{ fontStyle: 'italic', margin: '0 0 1rem 0' }}>"{q.quote}"</blockquote>
          <p>{q.explanation}</p>
          <div style={{ fontSize: '0.8rem', color: '#666' }}>
            Confidence: {q.confidence} | Chunk: {q.chunk_id}
          </div>
        </div>
      ))}
    </div>
  );
};

const EntitiesList = () => {
  const [entityData, setEntityData] = useState({ entity_classes: [], classes: {} });

  useEffect(() => {
    fetch('./entities_data.json')
      .then(res => res.json())
      .then(setEntityData)
      .catch(() => setEntityData({ entity_classes: [], classes: {} }));
  }, []);

  return (
    <div style={{ padding: '2rem', maxWidth: '1000px', margin: '0 auto' }}>
      <h1 style={{ marginBottom: '0.6rem' }}>Entities</h1>
      <p style={{ color: '#666' }}>
        Browse extracted entities grouped by class. For SEO/crawlable pages, use the{' '}
        <a href="../entities/index.html">static entity index</a>.
      </p>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '1rem' }}>
        {entityData.entity_classes.map(cls => {
          const entities = (entityData.classes && entityData.classes[cls.id]) || [];
          const top = entities.slice(0, 8);

          return (
            <div key={cls.id} style={{ border: '1px solid #eee', borderRadius: '8px', padding: '1rem', background: '#fafafa' }}>
              <h3 style={{ marginTop: 0 }}>{cls.label}</h3>
              <p style={{ margin: '0 0 0.8rem 0', color: '#666', fontSize: '0.9rem' }}>
                {cls.entity_count} entities · {cls.mention_count} mentions
              </p>
              {top.map(entity => (
                <div key={entity.id} style={{ marginBottom: '0.3rem' }}>
                  <Link to={`/entity/${encodeURIComponent(entity.id)}`}>
                    {entity.label}
                  </Link>{' '}
                  <span style={{ color: '#666', fontSize: '0.85rem' }}>({entity.count})</span>
                </div>
              ))}
            </div>
          );
        })}
      </div>
    </div>
  );
};

const EntityPage = () => {
  const { entityId } = useParams();
  const decodedId = decodeURIComponent(entityId);
  const [entity, setEntity] = useState(null);

  useEffect(() => {
    fetch('./entities_data.json')
      .then(res => res.json())
      .then(data => {
        const classes = data.classes || {};
        for (const classId of Object.keys(classes)) {
          const found = classes[classId].find(e => e.id === decodedId);
          if (found) {
            setEntity(found);
            return;
          }
        }
        setEntity(undefined);
      })
      .catch(() => setEntity(undefined));
  }, [decodedId]);

  if (entity === null) {
    return <div style={{ padding: '2rem' }}>Loading entity...</div>;
  }

  if (entity === undefined) {
    return (
      <div style={{ padding: '2rem', maxWidth: '800px', margin: '0 auto' }}>
        <Link to="/entities">← Back to Entities</Link>
        <h1>Entity not found</h1>
      </div>
    );
  }

  const highlightMentions = (text, terms) => {
    if (!text || !terms || terms.length === 0) return text;

    const cleaned = Array.from(new Set(terms.filter(Boolean))).sort((a, b) => b.length - a.length);
    if (cleaned.length === 0) return text;

    const escaped = cleaned.map(term => term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
    const regex = new RegExp(`(${escaped.join('|')})`, 'gi');
    const parts = text.split(regex);

    return parts.map((part, index) => {
      if (cleaned.some(term => term.toLowerCase() === part.toLowerCase())) {
        return <strong key={index}>{part}</strong>;
      }
      return <React.Fragment key={index}>{part}</React.Fragment>;
    });
  };

  return (
    <div style={{ padding: '2rem', maxWidth: '800px', margin: '0 auto' }}>
      <Link to="/entities" style={{ display: 'inline-block', marginBottom: '1rem', color: '#666', textDecoration: 'none' }}>← Back to Entities</Link>
      <h1 style={{ marginBottom: '0.4rem' }}>{entity.label}</h1>
      <p style={{ marginTop: 0, color: '#666' }}>
        {entity.entity_class} · {entity.count} mentions · normalized {entity.normalized_count} ({entity.normalized_rate_percent}%)
      </p>

      {entity.mention_samples?.length > 0 && (
        <div style={{ marginBottom: '1rem' }}>
          <strong>Surface forms:</strong>{' '}
          {entity.mention_samples.join(' · ')}
        </div>
      )}

      <p style={{ color: '#666', marginTop: 0 }}>
        Showing {entity.snippets?.length || 0} context snippets for {entity.count} total mentions.
      </p>

      {(entity.snippets || []).map((snippet, i) => (
        <div key={i} style={{ background: '#f9f9f9', borderLeft: '4px solid #ccc', padding: '1rem', marginBottom: '0.7rem' }}>
          {highlightMentions(snippet, entity.mention_samples || [])}
        </div>
      ))}

      <p>
        <a href={`../entities/${entity.entity_class.replaceAll('_', '-')}.html`}>Open grouped static page</a>
      </p>
    </div>
  );
};

const EntityThemeView = () => {
  const [data, setData] = useState(null);
  const [selected, setSelected] = useState(null);
  const [minWeight, setMinWeight] = useState(2.5);
  const [maxLinks, setMaxLinks] = useState(140);
  const [hoveredNodeId, setHoveredNodeId] = useState(null);

  useEffect(() => {
    fetch('./entity_theme_data.json')
      .then(res => res.json())
      .then(setData)
      .catch(() => setData(undefined));
  }, []);

  if (data === null) {
    return <div style={{ padding: '2rem' }}>Loading entity-theme relationships...</div>;
  }

  if (data === undefined || !data.graph) {
    return (
      <div style={{ padding: '2rem', maxWidth: '900px', margin: '0 auto' }}>
        <h1>Entity × Theme Relationships</h1>
        <p>Relationship data not found. Generate `web/public/entity_theme_data.json` first.</p>
      </div>
    );
  }

  const allNodes = data.graph.nodes || [];
  const allLinks = data.graph.links || [];

  const idOf = value => (typeof value === 'object' && value !== null ? value.id : value);

  const filteredLinks = allLinks
    .filter(link => (link.value || 0) >= minWeight)
    .sort((a, b) => (b.value || 0) - (a.value || 0))
    .slice(0, maxLinks);

  const activeNodeIds = new Set();
  filteredLinks.forEach(link => {
    activeNodeIds.add(idOf(link.source));
    activeNodeIds.add(idOf(link.target));
  });

  const filteredNodes = allNodes.filter(node => activeNodeIds.has(node.id));
  const filteredTopEdges = (data.top_edges || [])
    .filter(edge => edge.weight >= minWeight)
    .slice(0, 80);

  return (
    <div style={{ padding: '1.5rem', maxWidth: '1200px', margin: '0 auto' }}>
      <h1 style={{ marginBottom: '0.4rem' }}>Entity × Theme Relationships</h1>
      <p style={{ color: '#666', marginTop: 0 }}>
        Co-mention graph from analysis quote/explanation text. Themes are labeled, entities are dots (hover to inspect).
      </p>

      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', marginBottom: '1rem', alignItems: 'center' }}>
        <label style={{ fontSize: '0.9rem' }}>
          Min edge weight: <strong>{minWeight.toFixed(1)}</strong>{' '}
          <input
            type="range"
            min="0.5"
            max="8"
            step="0.1"
            value={minWeight}
            onChange={e => setMinWeight(parseFloat(e.target.value))}
            style={{ verticalAlign: 'middle', marginLeft: '0.4rem' }}
          />
        </label>
        <label style={{ fontSize: '0.9rem' }}>
          Max links:{' '}
          <select value={maxLinks} onChange={e => setMaxLinks(parseInt(e.target.value, 10))}>
            <option value={80}>80</option>
            <option value={120}>120</option>
            <option value={140}>140</option>
            <option value={180}>180</option>
            <option value={240}>240</option>
          </select>
        </label>
        <span style={{ color: '#666', fontSize: '0.9rem' }}>
          Showing {filteredNodes.length} nodes / {filteredLinks.length} links
        </span>
      </div>

      <div style={{ height: '55vh', border: '1px solid #e5e5e5', borderRadius: '8px', marginBottom: '1rem' }}>
        <ForceGraph2D
          graphData={{ nodes: filteredNodes, links: filteredLinks }}
          d3AlphaDecay={0.03}
          d3VelocityDecay={0.4}
          cooldownTicks={120}
          linkWidth={link => Math.max(0.8, Math.min(5, (link.value || 1) / 2))}
          linkColor={() => 'rgba(120,120,120,0.35)'}
          nodeLabel={node => {
            if (node.group === 'theme') {
              return `${node.label} (theme)`;
            }
            return `${node.label} (${node.entity_class})`;
          }}
          nodeCanvasObject={(node, ctx, globalScale) => {
            const label = node.label || node.id;
            const isTheme = node.group === 'theme';
            const isHovered = hoveredNodeId === node.id;

            if (isTheme) {
              const fontSize = 12 / globalScale;
              ctx.font = `bold ${fontSize}px Sans-Serif`;
              const textWidth = ctx.measureText(label).width;
              const padding = 4 / globalScale;
              const boxW = textWidth + padding * 2;
              const boxH = fontSize + padding * 2;

              ctx.fillStyle = '#ffe0e0';
              ctx.fillRect(node.x - boxW / 2, node.y - boxH / 2, boxW, boxH);

              ctx.textAlign = 'center';
              ctx.textBaseline = 'middle';
              ctx.fillStyle = '#222';
              ctx.fillText(label, node.x, node.y);

              node.__bckgDimensions = [boxW, boxH];
              return;
            }

            const radius = Math.max(1.8, Math.min(6, ((node.count || 1) / 40) + 2));
            ctx.beginPath();
            ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false);
            ctx.fillStyle = '#6da6e8';
            ctx.fill();

            if (isHovered) {
              const fontSize = 10 / globalScale;
              ctx.font = `${fontSize}px Sans-Serif`;
              const textWidth = ctx.measureText(label).width;
              const pad = 3 / globalScale;
              const lx = node.x + radius + 4 / globalScale;
              const ly = node.y - radius - 2 / globalScale;

              ctx.fillStyle = 'rgba(255,255,255,0.92)';
              ctx.fillRect(lx - pad, ly - fontSize, textWidth + pad * 2, fontSize + pad * 2);
              ctx.fillStyle = '#111';
              ctx.textAlign = 'left';
              ctx.textBaseline = 'alphabetic';
              ctx.fillText(label, lx, ly);
            }

            node.__radius = radius;
          }}
          nodePointerAreaPaint={(node, color, ctx) => {
            ctx.fillStyle = color;
            if (node.group === 'theme') {
              const d = node.__bckgDimensions;
              if (d) {
                ctx.fillRect(node.x - d[0] / 2, node.y - d[1] / 2, d[0], d[1]);
              }
            } else {
              const r = node.__radius || 3;
              ctx.beginPath();
              ctx.arc(node.x, node.y, r + 2, 0, 2 * Math.PI, false);
              ctx.fill();
            }
          }}
          onNodeHover={node => setHoveredNodeId(node?.id || null)}
          onNodeClick={node => {
            if (node.group === 'entity') {
              window.location.hash = `#/entity/${encodeURIComponent(node.id)}`;
              return;
            }
            setSelected({ type: 'theme', value: node.id });
          }}
          onLinkClick={link => {
            const sourceId = idOf(link.source);
            const targetId = idOf(link.target);
            const match = filteredTopEdges.find(
              e => e.entity_id === sourceId && e.theme === targetId
            );
            if (match) {
              setSelected({ type: 'edge', value: match });
            }
          }}
        />
      </div>

      {selected?.type === 'edge' && (
        <div style={{ background: '#fafafa', border: '1px solid #eee', borderRadius: '8px', padding: '1rem', marginBottom: '1rem' }}>
          <h3 style={{ marginTop: 0 }}>{selected.value.entity_label} ↔ {selected.value.theme}</h3>
          <p style={{ marginTop: 0, color: '#666' }}>
            Weight: {selected.value.weight} · Matches: {selected.value.count}
          </p>
          {(selected.value.evidence || []).map((ev, i) => (
            <blockquote key={i} style={{ margin: '0.5rem 0', paddingLeft: '0.8rem', borderLeft: '3px solid #ddd' }}>
              {ev}
            </blockquote>
          ))}
        </div>
      )}

      <h2 style={{ marginBottom: '0.6rem' }}>Top Entity-Theme Links</h2>
      <div style={{ display: 'grid', gap: '0.6rem' }}>
        {filteredTopEdges.slice(0, 50).map((edge, i) => (
          <div key={i} style={{ border: '1px solid #eee', borderRadius: '8px', padding: '0.8rem' }}>
            <div>
              <Link to={`/entity/${encodeURIComponent(edge.entity_id)}`}>{edge.entity_label}</Link>
              {' '}↔ <strong>{edge.theme}</strong>
            </div>
            <div style={{ color: '#666', fontSize: '0.9rem' }}>
              Weight {edge.weight} · Matches {edge.count} · {edge.entity_class}
            </div>
            {edge.evidence?.[0] && (
              <div style={{ marginTop: '0.4rem', fontSize: '0.92rem' }}>
                “{edge.evidence[0]}”
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};


const GitHubRibbon = () => (
  <a href="https://github.com/andyed/fascist-language-analyzer" target="_blank" rel="noopener noreferrer" className="github-corner" aria-label="View source on GitHub">
    <svg width="80" height="80" viewBox="0 0 250 250" style={{ fill: '#151513', color: '#fff', position: 'absolute', top: 0, border: 0, right: 0, zIndex: 1000 }} aria-hidden="true">
      <path d="M0,0 L115,115 L130,115 L142,142 L250,250 L250,0 Z"></path>
      <path d="M128.3,109.0 C113.8,99.7 119.0,89.6 119.0,89.6 C122.0,82.7 120.5,78.6 120.5,78.6 C119.2,72.0 123.4,76.3 123.4,76.3 C127.3,80.9 125.5,87.3 125.5,87.3 C122.9,97.6 130.6,101.9 134.4,103.2" fill="currentColor" style={{ transformOrigin: '130px 106px' }} className="octo-arm"></path>
      <path d="M115.0,115.0 C114.9,115.1 118.7,116.5 119.8,115.4 L133.7,101.6 C136.9,99.2 139.9,98.4 142.2,98.6 C133.8,88.0 127.5,74.4 143.8,58.0 C148.5,53.4 154.0,51.2 159.7,51.0 C160.3,49.4 163.2,43.6 171.4,40.1 C171.4,40.1 176.1,42.5 178.8,56.2 C183.1,58.6 187.2,61.8 190.9,65.4 C194.5,69.0 197.7,73.2 200.1,77.6 C213.8,80.2 216.3,84.9 216.3,84.9 C212.7,93.1 206.9,96.0 205.4,96.6 C205.1,102.4 203.0,107.8 198.3,112.5 C181.9,128.9 168.3,122.5 157.7,114.1 C157.9,116.9 156.7,120.9 152.7,124.9 L141.0,136.5 C139.8,137.7 141.6,141.9 141.8,141.8 Z" fill="currentColor" className="octo-body"></path>
    </svg>
    <style>{`
            .github-corner:hover .octo-arm { animation: octocat-wave 560ms ease-in-out }
            @keyframes octocat-wave { 0%,100% { transform: rotate(0) } 20%,60% { transform: rotate(-25deg) } 40%,80% { transform: rotate(10deg) } }
            @media (max-width:500px) {
                .github-corner:hover .octo-arm { animation: none }
                .github-corner .octo-arm { animation: octocat-wave 560ms ease-in-out }
            }
        `}</style>
  </a>
);



const App = () => {
  return (
    <Router>
      <div className="App" style={{ position: 'relative' }}>
        <GitHubRibbon />
        <Nav />
        <Routes>
          <Route path="/" element={<GraphView />} />
          <Route path="/themes" element={<ThemeList />} />
          <Route path="/theme/:traitId" element={<ThemePage />} />
          <Route path="/entities" element={<EntitiesList />} />
          <Route path="/entity/:entityId" element={<EntityPage />} />
          <Route path="/entity-themes" element={<EntityThemeView />} />
        </Routes>
      </div>
    </Router>
  );
};

export default App;
