import React, { useRef, useEffect, useState } from 'react';
import * as d3 from 'd3';
import { ENTITY_CLASS_COLORS, ENTITY_CLASS_LABELS, traitColorForTheme } from '../utils/graphHelpers';

// Max entities shown in the ego graph to keep it readable.
// Higher-weight connections are kept; the rest are dropped.
const MAX_ENTITIES = 40;
const ZOOM_LABEL_K = 1.8;

// Mini ego network showing entities connected to a single theme.
// Labels hidden by default; visible on zoom or hover (same pattern as main graph).
const ThemeEgoGraph = ({ themeId }) => {
  const svgRef = useRef(null);
  const [data, setData] = useState(null);

  useEffect(() => {
    fetch('./entity_theme_data.json')
      .then(res => res.json())
      .then(setData)
      .catch(() => setData(undefined));
  }, []);

  useEffect(() => {
    if (!data?.graph || !svgRef.current) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const allNodes = data.graph.nodes || [];
    const allLinks = data.graph.links || [];

    // Resolve the actual theme node ID — data uses "1. Cult of Tradition"
    // while the route param may be just "Cult of Tradition".
    const themeNodeCandidates = allNodes.filter(n =>
      n.group === 'theme' && (
        n.id === themeId ||
        n.id.replace(/^\d+\.\s*/, '') === themeId ||
        n.label === themeId
      )
    );
    const matchedThemeIds = new Set(themeNodeCandidates.map(n => n.id));
    if (matchedThemeIds.size === 0) return;

    const isMatchedTheme = (id) => matchedThemeIds.has(id);
    const primaryThemeId = themeNodeCandidates[0].id;
    const themeNode = (allNodes.find(n => n.id === primaryThemeId));
    if (!themeNode) return;

    // Find links connected to any matched theme ID
    const themeLinks = allLinks.filter(link => {
      const sid = typeof link.source === 'object' ? link.source.id : link.source;
      const tid = typeof link.target === 'object' ? link.target.id : link.target;
      return isMatchedTheme(sid) || isMatchedTheme(tid);
    });
    if (themeLinks.length === 0) return;

    // Sort by weight descending, keep top MAX_ENTITIES entities
    const sorted = [...themeLinks].sort((a, b) => (b.value || 0) - (a.value || 0));
    const keptEntityIds = new Set();
    const keptLinks = [];
    for (const link of sorted) {
      const sid = typeof link.source === 'object' ? link.source.id : link.source;
      const tid = typeof link.target === 'object' ? link.target.id : link.target;
      const entityId = isMatchedTheme(sid) ? tid : sid;
      if (keptEntityIds.size < MAX_ENTITIES || keptEntityIds.has(entityId)) {
        keptEntityIds.add(entityId);
        keptLinks.push(link);
      }
    }

    const nodeMap = new Map(allNodes.map(n => [n.id, n]));
    const nodes = [
      { ...themeNode },
      ...Array.from(keptEntityIds).map(id => ({ ...nodeMap.get(id) })).filter(Boolean)
    ];

    // Remap variant theme IDs in links to the primary theme ID
    const links = keptLinks.map(l => {
      const copy = { ...l };
      const sid = typeof copy.source === 'object' ? copy.source.id : copy.source;
      const tid = typeof copy.target === 'object' ? copy.target.id : copy.target;
      if (isMatchedTheme(sid) && sid !== primaryThemeId) copy.source = primaryThemeId;
      if (isMatchedTheme(tid) && tid !== primaryThemeId) copy.target = primaryThemeId;
      return copy;
    });

    const width = svgRef.current.clientWidth || 600;
    const height = 400;
    svg.attr('viewBox', `0 0 ${width} ${height}`);

    // Scales
    const entityCounts = nodes.filter(n => n.group === 'entity').map(n => n.count || 1);
    const radiusScale = d3.scaleSqrt()
      .domain([1, d3.max(entityCounts) || 1])
      .range([4, 14]);
    const maxVal = d3.max(links, l => l.value) || 1;

    // Force simulation — ego layout: theme pinned at center
    const simulation = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(links).id(d => d.id)
        .distance(d => 50 + (1 - (d.value || 0) / maxVal) * 80)
        .strength(d => 0.3 + ((d.value || 0) / maxVal) * 0.5)
      )
      .force('charge', d3.forceManyBody().strength(-120))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(d =>
        d.group === 'theme' ? 55 : radiusScale(d.count || 1) + 6
      ).strength(0.8))
      .alphaDecay(0.04)
      .velocityDecay(0.35);

    // Pin theme at center
    nodes.forEach(n => {
      if (matchedThemeIds.has(n.id)) {
        n.fx = width / 2;
        n.fy = height / 2;
      }
    });

    // Adjacency for hover highlighting
    const adj = new Map();
    links.forEach(link => {
      const sid = typeof link.source === 'object' ? link.source.id : link.source;
      const tid = typeof link.target === 'object' ? link.target.id : link.target;
      if (!adj.has(sid)) adj.set(sid, new Set());
      if (!adj.has(tid)) adj.set(tid, new Set());
      adj.get(sid).add(tid);
      adj.get(tid).add(sid);
    });

    // SVG layers
    const g = svg.append('g');
    const linksLayer = g.append('g');
    const nodesLayer = g.append('g');

    // Zoom + pan
    const zoom = d3.zoom()
      .scaleExtent([0.5, 6])
      .on('zoom', (event) => {
        g.attr('transform', event.transform);
        svg.classed('ego-zoomed', event.transform.k > ZOOM_LABEL_K);
      });
    svg.call(zoom);
    svg.on('dblclick.zoom', () => {
      svg.transition().duration(400).call(zoom.transform, d3.zoomIdentity);
    });

    // Draw links
    const linkEls = linksLayer.selectAll('line')
      .data(links)
      .join('line')
        .attr('stroke', '#aaa')
        .attr('stroke-width', d => Math.max(0.8, (d.value / maxVal) * 3))
        .attr('stroke-opacity', 0.35);

    // Draw entity nodes
    const entityData = nodes.filter(n => n.group === 'entity');
    const entityGroups = nodesLayer.selectAll('.ego-entity')
      .data(entityData, d => d.id)
      .join('g')
        .attr('class', 'ego-entity')
        .style('cursor', 'pointer')
        .on('click', (event, d) => {
          window.location.hash = `#/entity/${encodeURIComponent(d.id)}`;
        })
        .on('mouseenter', (event, d) => {
          const connected = adj.get(d.id) || new Set();
          svg.classed('ego-has-hover', true);
          linkEls.classed('ego-hl', lk => {
            const s = typeof lk.source === 'object' ? lk.source.id : lk.source;
            const t = typeof lk.target === 'object' ? lk.target.id : lk.target;
            return s === d.id || t === d.id;
          });
          entityGroups.classed('ego-hl', n => n.id === d.id || connected.has(n.id));
        })
        .on('mouseleave', () => {
          svg.classed('ego-has-hover', false);
          linkEls.classed('ego-hl', false);
          entityGroups.classed('ego-hl', false);
        });

    entityGroups.append('circle')
      .attr('r', d => radiusScale(d.count || 1))
      .attr('fill', d => ENTITY_CLASS_COLORS[d.entity_class] || '#999')
      .attr('stroke', '#fff')
      .attr('stroke-width', 0.8);

    entityGroups.append('text')
      .attr('class', 'ego-label')
      .attr('dy', d => -(radiusScale(d.count || 1) + 4))
      .attr('text-anchor', 'middle')
      .attr('font-size', '10px')
      .attr('fill', '#333')
      .text(d => d.label);

    // Draw theme node (center)
    const themeG = nodesLayer.selectAll('.ego-theme')
      .data(nodes.filter(n => n.group === 'theme'), d => d.id)
      .join('g')
        .attr('class', 'ego-theme');

    themeG.append('text')
      .attr('text-anchor', 'middle')
      .attr('dominant-baseline', 'central')
      .attr('font-weight', '600')
      .attr('font-size', '13px')
      .attr('fill', '#222')
      .text(d => d.label);

    // Background rect for theme — measure text then insert before it
    themeG.each(function () {
      const textEl = d3.select(this).select('text').node();
      const bbox = textEl.getBBox();
      const pad = 6;
      d3.select(this).insert('rect', 'text')
        .attr('x', bbox.x - pad)
        .attr('y', bbox.y - pad)
        .attr('width', bbox.width + pad * 2)
        .attr('height', bbox.height + pad * 2)
        .attr('rx', 5)
        .attr('fill', traitColorForTheme(primaryThemeId))
        .attr('stroke', '#ccc')
        .attr('stroke-width', 0.5);
    });

    // Tick
    simulation.on('tick', () => {
      linkEls
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y);
      entityGroups.attr('transform', d => `translate(${d.x},${d.y})`);
      themeG.attr('transform', d => `translate(${d.x},${d.y})`);
    });

    return () => simulation.stop();
  }, [data, themeId]);

  if (data === undefined) return null;
  if (data === null) return <div style={{ color: '#999', fontSize: '0.9rem', padding: '0.5rem 0' }}>Loading entity graph...</div>;

  return (
    <div style={{ marginBottom: '1.5rem' }}>
      <h3 style={{ marginBottom: '0.3rem', fontSize: '1rem', color: '#555' }}>Connected Entities</h3>
      <div style={{ border: '1px solid #e5e5e5', borderRadius: '8px', background: '#fafafa' }}>
        <svg
          ref={svgRef}
          width="100%"
          height="400"
          style={{ display: 'block' }}
        />
        <style>{`
          /* Ego graph: labels hidden by default, shown on zoom or hover */
          .ego-label {
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.2s;
          }
          .ego-zoomed .ego-label { opacity: 0.85; }
          .ego-entity:hover .ego-label { opacity: 1 !important; }

          /* Hover dimming */
          .ego-has-hover .ego-entity:not(.ego-hl) circle { opacity: 0.15; transition: opacity 0.15s; }
          .ego-has-hover .ego-entity.ego-hl .ego-label { opacity: 1 !important; }
          .ego-has-hover line:not(.ego-hl) { stroke-opacity: 0.04 !important; transition: stroke-opacity 0.15s; }
          .ego-has-hover line.ego-hl { stroke-opacity: 0.7 !important; }
        `}</style>
      </div>
      <div style={{ display: 'flex', gap: '0.8rem', flexWrap: 'wrap', marginTop: '0.4rem', fontSize: '0.8rem', color: '#888' }}>
        {Object.entries(ENTITY_CLASS_LABELS).map(([cls, label]) => (
          <span key={cls} style={{ display: 'flex', alignItems: 'center', gap: '3px' }}>
            <span style={{
              width: 8, height: 8, borderRadius: '50%',
              background: ENTITY_CLASS_COLORS[cls], display: 'inline-block'
            }} />
            {label}
          </span>
        ))}
        <span style={{ marginLeft: 'auto', fontStyle: 'italic' }}>Scroll to zoom, hover for labels</span>
      </div>
    </div>
  );
};

export default ThemeEgoGraph;
