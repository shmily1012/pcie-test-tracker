import { useEffect, useState, useRef } from 'react';
import { fetchSummary, fetchTreemap, type DashboardSummary, type TreemapNode } from '../lib/api';
import Treemap from '../components/Treemap';
import { Activity, CheckCircle, AlertTriangle } from 'lucide-react';

const COLORS = {
  bg: '#0f0e0d',
  cardBg: '#2d2a27',
  orange: '#FE7B23',
  cream: '#fff5e3',
  green: '#4ade80',
  red: '#ef4444',
};

function StatPill({ label, value, icon: Icon, color }: {
  label: string; value: string | number; icon: any; color: string;
}) {
  return (
    <div
      className="flex items-center gap-3 px-5 py-3 rounded-xl"
      style={{ background: COLORS.cardBg, border: `1px solid ${color}33` }}
    >
      <Icon size={20} style={{ color, opacity: 0.7 }} />
      <div>
        <div className="text-xs" style={{ color: `${COLORS.cream}99` }}>{label}</div>
        <div className="text-xl font-bold" style={{ color }}>{value}</div>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [treemapData, setTreemapData] = useState<TreemapNode | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 500 });

  useEffect(() => {
    fetchSummary().then(setSummary);
    fetchTreemap().then(setTreemapData);
  }, []);

  useEffect(() => {
    const updateSize = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        setDimensions({
          width: Math.floor(rect.width),
          height: Math.max(400, Math.floor(window.innerHeight - 200)),
        });
      }
    };
    updateSize();
    window.addEventListener('resize', updateSize);
    return () => window.removeEventListener('resize', updateSize);
  }, []);

  if (!summary || !treemapData) {
    return (
      <div className="flex items-center justify-center h-full" style={{ color: COLORS.orange }}>
        Loading...
      </div>
    );
  }

  const needsAttention = (summary.by_status.fail || 0) + (summary.by_status.blocked || 0);

  return (
    <div className="p-6 h-full flex flex-col" style={{ background: COLORS.bg }}>
      {/* Top stat pills */}
      <div className="flex items-center gap-4 mb-5">
        <StatPill label="Total Tests" value={summary.total} icon={Activity} color={COLORS.orange} />
        <StatPill label="Pass Rate" value={`${summary.pass_rate}%`} icon={CheckCircle} color={
          summary.pass_rate >= 70 ? COLORS.green : summary.pass_rate >= 40 ? COLORS.orange : COLORS.red
        } />
        <StatPill label="Needs Attention" value={needsAttention} icon={AlertTriangle} color={
          needsAttention > 0 ? COLORS.red : COLORS.green
        } />
        <div className="flex-1" />
        <div className="text-xs" style={{ color: `${COLORS.cream}44` }}>
          Click a category to drill down
        </div>
      </div>

      {/* Treemap */}
      <div ref={containerRef} className="flex-1 min-h-0">
        <Treemap
          data={treemapData}
          width={dimensions.width}
          height={dimensions.height}
        />
      </div>
    </div>
  );
}
