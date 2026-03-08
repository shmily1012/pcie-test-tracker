import { useEffect, useState } from 'react';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { fetchSummary, fetchCoverage, fetchHeatmap, DashboardSummary, CoverageItem, HeatmapCell } from '../lib/api';
import { Activity, CheckCircle, AlertTriangle, XCircle } from 'lucide-react';

const STATUS_COLORS: Record<string, string> = {
  pass: '#22c55e', fail: '#ef4444', blocked: '#eab308', skip: '#6b7280', not_started: '#334155'
};

function StatCard({ label, value, icon: Icon, color }: { label: string; value: string | number; icon: any; color: string }) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-slate-400">{label}</p>
          <p className="text-3xl font-bold mt-1" style={{ color }}>{value}</p>
        </div>
        <Icon size={32} className="opacity-30" style={{ color }} />
      </div>
    </div>
  );
}

export default function Dashboard() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [coverage, setCoverage] = useState<CoverageItem[]>([]);
  const [heatmap, setHeatmap] = useState<HeatmapCell[]>([]);

  useEffect(() => {
    fetchSummary().then(setSummary);
    fetchCoverage().then(setCoverage);
    fetchHeatmap().then(setHeatmap);
  }, []);

  if (!summary) return <div className="p-8 text-slate-400">Loading...</div>;

  const pieData = Object.entries(summary.by_status).map(([name, value]) => ({ name, value }));
  const barData = coverage.map(c => ({
    name: c.category.length > 20 ? c.category.slice(0, 18) + '…' : c.category,
    Pass: c.passed, Fail: c.failed, Blocked: c.blocked, 'Not Started': c.not_started
  }));

  // Heatmap data
  const categories = [...new Set(heatmap.map(h => h.category))].sort();
  const priorities = ['P0', 'P1', 'P2'];

  return (
    <div className="p-6 space-y-6">
      <h2 className="text-2xl font-bold">Dashboard</h2>

      <div className="grid grid-cols-4 gap-4">
        <StatCard label="Total Tests" value={summary.total} icon={Activity} color="#3b82f6" />
        <StatCard label="Pass Rate" value={`${summary.pass_rate}%`} icon={CheckCircle} color="#22c55e" />
        <StatCard label="P0 Coverage" value={`${summary.p0_coverage}%`} icon={AlertTriangle} color="#eab308" />
        <StatCard label="Blocked" value={summary.by_status.blocked || 0} icon={XCircle} color="#ef4444" />
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-slate-300 mb-4">Status Distribution</h3>
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie data={pieData} cx="50%" cy="50%" innerRadius={60} outerRadius={100}
                   dataKey="value" paddingAngle={2}>
                {pieData.map((entry) => (
                  <Cell key={entry.name} fill={STATUS_COLORS[entry.name] || '#334155'} />
                ))}
              </Pie>
              <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }} />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
          <h3 className="text-sm font-semibold text-slate-300 mb-4">Coverage by Category</h3>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={barData} layout="vertical">
              <XAxis type="number" stroke="#64748b" />
              <YAxis type="category" dataKey="name" width={150} stroke="#64748b" tick={{ fontSize: 11 }} />
              <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8 }} />
              <Bar dataKey="Pass" stackId="a" fill="#22c55e" />
              <Bar dataKey="Fail" stackId="a" fill="#ef4444" />
              <Bar dataKey="Blocked" stackId="a" fill="#eab308" />
              <Bar dataKey="Not Started" stackId="a" fill="#334155" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
        <h3 className="text-sm font-semibold text-slate-300 mb-4">Category × Priority Heatmap</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr>
                <th className="text-left p-2 text-slate-400">Category</th>
                {priorities.map(p => <th key={p} className="p-2 text-center text-slate-400">{p}</th>)}
              </tr>
            </thead>
            <tbody>
              {categories.map(cat => (
                <tr key={cat} className="border-t border-slate-800">
                  <td className="p-2 text-slate-300">{cat}</td>
                  {priorities.map(pri => {
                    const cell = heatmap.find(h => h.category === cat && h.priority === pri);
                    const pct = cell?.coverage_pct || 0;
                    const bg = pct >= 80 ? 'bg-green-500/30' : pct >= 40 ? 'bg-yellow-500/30' : pct > 0 ? 'bg-red-500/30' : 'bg-slate-800';
                    return (
                      <td key={pri} className={`p-2 text-center ${bg} rounded`}>
                        {cell ? `${cell.passed}/${cell.total}` : '—'}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
