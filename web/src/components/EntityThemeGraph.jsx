import React, { useRef, useEffect, useCallback } from 'react';
import * as d3 from 'd3';
import { ENTITY_CLASS_COLORS, traitColorForTheme } from '../utils/graphHelpers';
import './EntityThemeGraph.css';

const ZOOM_LABEL_THRESHOLD = 2.0;

// D3+SVG bipartite force graph for entity-theme relationships.
// SVG rendering gives DOM-quality text — crisp labels at any zoom level.
const EntityThemeGraph = ({
  nodes,
  links,
  visibleClasses,
  onNodeClick,
  onLinkClick,
  width = 900,
  height = 550,
}) => {
  const svgRef = useRef(null);
  const simulationRef = useRef(null);

  // Build adjacency lookup: entityId → Set of linked theme ids (and vice versa)
  const adjacency = useRef(new Map());

  const buildGraph = useCallback(() => {
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    if (!nodes.length) return;

    // Deep-copy so D3 can mutate (adds x, y, vx, vy)
    const simNodes = nodes.map(d => ({ ...d }));
    const simLinks = links.map(d => ({ ...d }));

    // Build adjacency map for hover highlighting
    const adj = new Map();
    simLinks.forEach(link => {
      const sid = typeof link.source === 'object' ? link.source.id : link.source;
      const tid = typeof link.target === 'object' ? link.target.id : link.target;
      if (!adj.has(sid)) adj.set(sid, new Set());
      if (!adj.has(tid)) adj.set(tid, new Set());
      adj.get(sid).add(tid);
      adj.get(tid).add(sid);
    });
    adjacency.current = adj;

    // Scales
    const entityCounts = simNodes.filter(n => n.group === 'entity').map(n => n.count || 1);
    const radiusScale = d3.scaleSqrt()
      .domain([1, d3.max(entityCounts) || 1])
      .range([3, 10]);

    const linkValues = simLinks.map(l => l.value || 0);
    const maxLinkVal = d3.max(linkValues) || 1;
    const linkWidthScale = d3.scaleLinear()
      .domain([0, maxLinkVal])
      .range([0.5, 4])
      .clamp(true);
    const linkOpacityScale = d3.scaleLinear()
      .domain([0, maxLinkVal])
      .range([0.12, 0.5])
      .clamp(true);

    // Force simulation
    const simulation = d3.forceSimulation(simNodes)
      .force('link', d3.forceLink(simLinks)
        .id(d => d.id)
        .distance(link => {
          // Stronger connections → shorter links
          const v = link.value || 0;
          return 60 + (1 - v / maxLinkVal) * 100;
        })
        .strength(link => {
          const v = link.value || 0;
          return 0.3 + (v / maxLinkVal) * 0.4;
        })
      )
      .force('charge', d3.forceManyBody()
        .strength(d => d.group === 'theme' ? -400 : -120)
      )
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide()
        .radius(d => d.group === 'theme' ? 50 : radiusScale(d.count || 1) + 2)
        .strength(0.7)
      )
      .force('x', d3.forceX(width / 2).strength(0.03))
      .force('y', d3.forceY(height / 2).strength(0.03))
      .alphaDecay(0.02)
      .velocityDecay(0.3);

    simulationRef.current = simulation;

    // SVG layers
    const zoomGroup = svg.append('g').attr('class', 'zoom-container');
    const linksLayer = zoomGroup.append('g').attr('class', 'links-layer');
    const entitiesLayer = zoomGroup.append('g').attr('class', 'entities-layer');
    const themesLayer = zoomGroup.append('g').attr('class', 'themes-layer');

    // Zoom behavior
    const zoom = d3.zoom()
      .scaleExtent([0.3, 8])
      .on('zoom', (event) => {
        zoomGroup.attr('transform', event.transform);
        svg.classed('zoomed-in', event.transform.k > ZOOM_LABEL_THRESHOLD);
      });
    svg.call(zoom);

    // Double-click to reset zoom
    svg.on('dblclick.zoom', () => {
      svg.transition().duration(400).call(zoom.transform, d3.zoomIdentity);
    });

    // Draw links
    const linkEls = linksLayer.selectAll('.graph-link')
      .data(simLinks)
      .join('line')
        .attr('class', 'graph-link')
        .attr('stroke', '#888')
        .attr('stroke-width', d => linkWidthScale(d.value || 0))
        .attr('stroke-opacity', d => linkOpacityScale(d.value || 0))
        .style('cursor', 'pointer')
        .on('click', (event, d) => {
          event.stopPropagation();
          if (onLinkClick) onLinkClick(d);
        });

    // Draw entity nodes
    const entityNodes = simNodes.filter(n => n.group === 'entity');
    const entityGroups = entitiesLayer.selectAll('.entity-node')
      .data(entityNodes, d => d.id)
      .join('g')
        .attr('class', d => `entity-node entity-class-${d.entity_class}`)
        .attr('data-class', d => d.entity_class)
        .style('cursor', 'pointer')
        .call(drag(simulation));

    entityGroups.append('circle')
      .attr('r', d => radiusScale(d.count || 1))
      .attr('fill', d => ENTITY_CLASS_COLORS[d.entity_class] || '#999')
      .attr('stroke', '#fff')
      .attr('stroke-width', 0.5);

    entityGroups.append('text')
      .attr('class', 'entity-label')
      .attr('dy', d => -(radiusScale(d.count || 1) + 3))
      .attr('text-anchor', 'middle')
      .text(d => d.label);

    entityGroups
      .on('mouseenter', (event, d) => handleNodeHover(svg, d, adj, linkEls, entityGroups, themesLayer))
      .on('mouseleave', () => clearHover(svg, linkEls, entityGroups, themesLayer))
      .on('click', (event, d) => {
        event.stopPropagation();
        if (onNodeClick) onNodeClick(d);
      });

    // Draw theme nodes
    const themeNodes = simNodes.filter(n => n.group === 'theme');
    const themeGroups = themesLayer.selectAll('.theme-node')
      .data(themeNodes, d => d.id)
      .join('g')
        .attr('class', 'theme-node')
        .style('cursor', 'pointer')
        .call(drag(simulation));

    // Theme labels — render text first to measure, then add background rect
    const themeTexts = themeGroups.append('text')
      .attr('class', 'theme-label')
      .attr('text-anchor', 'middle')
      .attr('dominant-baseline', 'central')
      .text(d => d.label);

    // Add background rects sized to text bounding boxes
    themeGroups.each(function (d) {
      const textEl = d3.select(this).select('text').node();
      const bbox = textEl.getBBox();
      const pad = 5;
      d3.select(this).insert('rect', 'text')
        .attr('class', 'theme-bg')
        .attr('x', bbox.x - pad)
        .attr('y', bbox.y - pad)
        .attr('width', bbox.width + pad * 2)
        .attr('height', bbox.height + pad * 2)
        .attr('rx', 4)
        .attr('fill', traitColorForTheme(d.id))
        .attr('stroke', '#ccc')
        .attr('stroke-width', 0.5);
    });

    themeGroups
      .on('mouseenter', (event, d) => handleNodeHover(svg, d, adj, linkEls, entityGroups, themesLayer))
      .on('mouseleave', () => clearHover(svg, linkEls, entityGroups, themesLayer))
      .on('click', (event, d) => {
        event.stopPropagation();
        if (onNodeClick) onNodeClick(d);
      });

    // Tick handler — update positions
    simulation.on('tick', () => {
      linkEls
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y);

      entityGroups.attr('transform', d => `translate(${d.x},${d.y})`);
      themeGroups.attr('transform', d => `translate(${d.x},${d.y})`);
    });
  }, [nodes, links, width, height, onNodeClick, onLinkClick]);

  // Rebuild graph when data changes
  useEffect(() => {
    buildGraph();
    return () => {
      if (simulationRef.current) {
        simulationRef.current.stop();
        simulationRef.current = null;
      }
    };
  }, [buildGraph]);

  // Apply entity class visibility via CSS opacity (no layout change)
  useEffect(() => {
    if (!svgRef.current) return;
    const svg = d3.select(svgRef.current);

    svg.selectAll('.entity-node')
      .transition().duration(300)
      .style('opacity', function () {
        const cls = d3.select(this).attr('data-class');
        return visibleClasses.has(cls) ? 1 : 0;
      })
      .on('end', function () {
        const cls = d3.select(this).attr('data-class');
        d3.select(this).style('pointer-events', visibleClasses.has(cls) ? 'auto' : 'none');
      });

    // Fade links connected to hidden entities
    svg.selectAll('.graph-link')
      .transition().duration(300)
      .style('opacity', function (d) {
        const srcNode = typeof d.source === 'object' ? d.source : null;
        const tgtNode = typeof d.target === 'object' ? d.target : null;
        if (srcNode?.group === 'entity' && !visibleClasses.has(srcNode.entity_class)) return 0;
        if (tgtNode?.group === 'entity' && !visibleClasses.has(tgtNode.entity_class)) return 0;
        return null; // keep original stroke-opacity
      });
  }, [visibleClasses]);

  return (
    <svg
      ref={svgRef}
      className="entity-theme-graph"
      width={width}
      height={height}
      style={{ display: 'block', width: '100%', height: '100%' }}
      viewBox={`0 0 ${width} ${height}`}
    />
  );
};

// Drag behavior for force simulation nodes
function drag(simulation) {
  return d3.drag()
    .on('start', (event, d) => {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
    })
    .on('drag', (event, d) => {
      d.fx = event.x;
      d.fy = event.y;
    })
    .on('end', (event, d) => {
      if (!event.active) simulation.alphaTarget(0);
      d.fx = null;
      d.fy = null;
    });
}

// Hover: highlight connected edges and nodes, dim everything else
function handleNodeHover(svg, hoveredNode, adj, linkEls, entityGroups, themesLayer) {
  const connectedIds = adj.get(hoveredNode.id) || new Set();

  svg.classed('has-hover', true);

  linkEls.classed('highlighted', d => {
    const sid = typeof d.source === 'object' ? d.source.id : d.source;
    const tid = typeof d.target === 'object' ? d.target.id : d.target;
    return sid === hoveredNode.id || tid === hoveredNode.id;
  });

  entityGroups.classed('highlighted', d => d.id === hoveredNode.id || connectedIds.has(d.id));
  themesLayer.selectAll('.theme-node')
    .classed('highlighted', d => d.id === hoveredNode.id || connectedIds.has(d.id));
}

function clearHover(svg, linkEls, entityGroups, themesLayer) {
  svg.classed('has-hover', false);
  linkEls.classed('highlighted', false);
  entityGroups.classed('highlighted', false);
  themesLayer.selectAll('.theme-node').classed('highlighted', false);
}

export default EntityThemeGraph;
