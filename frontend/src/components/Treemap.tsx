import { useMemo, useState, useCallback } from 'react';
import { treemap, hierarchy, treemapSquarify } from 'd3-hierarchy';
import type { TreemapNode } from '../lib/api';

// Everpure-inspired palette
const COLORS = {
  bg: '#0f0e0d',
  cardBg: '#2d2a27',
  orange: '#FE7B23',
  deepOrange: '#D55D1D',
  darkBrown: '#55250c',
  cream: '#fff5e3',
  green: '#4ade80',
  red: '#ef4444',
  border: '#803812',
};

function getBlockColor(node: TreemapNode): string {
  if (node.total === 0) return COLORS.cardBg;
  if (node.not_started === node.total) return COLORS.darkBrown;
  const passRate = node.passed / node.total;
  if (passRate >= 0.8) return COLORS.green;
  if (node.failed > 0) return COLORS.deepOrange;
  return COLORS.deepOrange;
}

function getBlockBorderColor(node: TreemapNode): string {
  if (node.failed > 0) return COLORS.red;
  return COLORS.border;
}

interface TreemapProps {
  data: TreemapNode;
  width: number;
  height: number;
}

export default function Treemap({ data, width, height }: TreemapProps) {
  const [currentNode, setCurrentNode] = useState<TreemapNode>(data);
  const [path, setPath] = useState<TreemapNode[]>([data]);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [tooltip, setTooltip] = useState<{
    x: number; y: number; node: TreemapNode;
  } | null>(null);

  // Reset when data changes
  useMemo(() => {
    setCurrentNode(data);
    setPath([data]);
  }, [data]);

  const layout = useMemo(() => {
    const root = hierarchy(currentNode)
      .sum(d => (d.children && d.children.length > 0) ? 0 : d.total)
      .sort((a, b) => (b.value || 0) - (a.value || 0));

    const tm = treemap<TreemapNode>()
      .size([width, height])
      .padding(3)
      .paddingTop(28)
      .round(true)
      .tile(treemapSquarify);

    return tm(root);
  }, [currentNode, width, height]);

  const handleClick = useCallback((node: TreemapNode) => {
    if (node.children && node.children.length > 0) {
      const newPath = [...path, node];
      setCurrentNode(node);
      setPath(newPath);
    }
  }, [path]);

  const handleBreadcrumb = useCallback((index: number) => {
    const newPath = path.slice(0, index + 1);
    setCurrentNode(newPath[newPath.length - 1]);
    setPath(newPath);
  }, [path]);

  const leaves = layout.children || [];

  return (
    <div>
      {/* Breadcrumb */}
      <div className="flex items-center gap-1.5 mb-3 text-sm">
        {path.map((node, i) => (
          <span key={i} className="flex items-center gap-1.5">
            {i > 0 && <span style={{ color: '#55250c' }}>/</span>}
            <button
              onClick={() => handleBreadcrumb(i)}
              className="transition-colors"
              style={{
                color: i === path.length - 1 ? COLORS.orange : COLORS.cream,
                opacity: i === path.length - 1 ? 1 : 0.6,
                background: 'none',
                border: 'none',
                cursor: i < path.length - 1 ? 'pointer' : 'default',
                padding: 0,
                fontWeight: i === path.length - 1 ? 600 : 400,
              }}
            >
              {node.name === 'root' ? 'All Categories' : node.name}
            </button>
          </span>
        ))}
      </div>

      {/* Treemap SVG */}
      <div className="relative" style={{ width, height }}>
        <svg width={width} height={height}>
          {leaves.map((leaf) => {
            const d = leaf.data;
            const id = d.name;
            const w = leaf.x1 - leaf.x0;
            const h = leaf.y1 - leaf.y0;
            const isHovered = hoveredId === id;
            const hasChildren = d.children && d.children.length > 0;
            const blockColor = getBlockColor(d);
            const borderColor = getBlockBorderColor(d);
            const progressPct = d.total > 0 ? (d.passed / d.total) * 100 : 0;

            return (
              <g
                key={id}
                transform={`translate(${leaf.x0},${leaf.y0})`}
                onMouseEnter={(e) => {
                  setHoveredId(id);
                  setTooltip({ x: e.clientX, y: e.clientY, node: d });
                }}
                onMouseMove={(e) => {
                  setTooltip({ x: e.clientX, y: e.clientY, node: d });
                }}
                onMouseLeave={() => {
                  setHoveredId(null);
                  setTooltip(null);
                }}
                onClick={() => handleClick(d)}
                style={{ cursor: hasChildren ? 'pointer' : 'default' }}
              >
                {/* Block background */}
                <rect
                  width={w}
                  height={h}
                  rx={6}
                  fill={blockColor}
                  fillOpacity={0.25}
                  stroke={isHovered ? COLORS.orange : borderColor}
                  strokeWidth={isHovered ? 2 : 1}
                  style={{
                    transition: 'all 0.2s ease',
                    filter: isHovered ? `drop-shadow(0 0 8px ${COLORS.orange}66)` : 'none',
                  }}
                />

                {/* Category name */}
                {w > 60 && h > 35 && (
                  <text
                    x={8}
                    y={18}
                    fill={COLORS.cream}
                    fontSize={w > 120 ? 13 : 11}
                    fontWeight={600}
                    style={{ pointerEvents: 'none' }}
                  >
                    {d.name.length > w / 7 ? d.name.slice(0, Math.floor(w / 7)) + '…' : d.name}
                  </text>
                )}

                {/* Count */}
                {w > 50 && h > 50 && (
                  <text
                    x={8}
                    y={36}
                    fill={COLORS.orange}
                    fontSize={11}
                    fontWeight={500}
                    style={{ pointerEvents: 'none' }}
                  >
                    {d.total} tests
                  </text>
                )}

                {/* Mini progress bar */}
                {w > 60 && h > 60 && (
                  <g transform={`translate(8, ${h - 16})`}>
                    <rect width={w - 16} height={5} rx={2.5} fill={COLORS.darkBrown} />
                    <rect
                      width={Math.max(0, (w - 16) * progressPct / 100)}
                      height={5}
                      rx={2.5}
                      fill={progressPct >= 80 ? COLORS.green : COLORS.orange}
                    />
                  </g>
                )}

                {/* Fail glow border overlay */}
                {d.failed > 0 && (
                  <rect
                    width={w}
                    height={h}
                    rx={6}
                    fill="none"
                    stroke={COLORS.red}
                    strokeWidth={1}
                    strokeOpacity={0.4}
                    style={{ filter: `drop-shadow(0 0 4px ${COLORS.red}44)` }}
                  />
                )}
              </g>
            );
          })}
        </svg>

        {/* Tooltip */}
        {tooltip && (
          <div
            className="fixed z-50 pointer-events-none px-3 py-2 rounded-lg text-xs shadow-xl"
            style={{
              left: tooltip.x + 12,
              top: tooltip.y - 8,
              background: COLORS.cardBg,
              border: `1px solid ${COLORS.border}`,
              color: COLORS.cream,
            }}
          >
            <div className="font-semibold mb-1" style={{ color: COLORS.orange }}>
              {tooltip.node.name}
            </div>
            <div className="space-y-0.5">
              <div>Total: {tooltip.node.total}</div>
              <div style={{ color: COLORS.green }}>Pass: {tooltip.node.passed}</div>
              <div style={{ color: COLORS.red }}>Fail: {tooltip.node.failed}</div>
              <div style={{ color: '#eab308' }}>Blocked: {tooltip.node.blocked}</div>
              <div style={{ color: '#64748b' }}>Not started: {tooltip.node.not_started}</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
