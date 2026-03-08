import { fetchCoverage, exportCsv, CoverageItem } from '../lib/api';
import { useEffect, useState } from 'react';
import { Download } from 'lucide-react';

export default function Reports() {
  const [coverage, setCoverage] = useState<CoverageItem[]>([]);
  useEffect(() => { fetchCoverage().then(setCoverage); }, []);

  const total = coverage.reduce((a, c) => a + c.total, 0);
  const passed = coverage.reduce((a, c) => a + c.passed, 0);

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Reports</h2>
        <button onClick={exportCsv} className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg text-sm">
          <Download size={16} /> Export CSV
        </button>
      </div>
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-800">
              <th className="text-left p-3 text-slate-400">Category</th>
              <th className="p-3 text-slate-400 text-center">Total</th>
              <th className="p-3 text-center text-green-400">Pass</th>
              <th className="p-3 text-center text-red-400">Fail</th>
              <th className="p-3 text-center text-yellow-400">Blocked</th>
              <th className="p-3 text-center text-slate-400">Not Started</th>
              <th className="p-3 text-center text-slate-400">Coverage</th>
            </tr>
          </thead>
          <tbody>
            {coverage.map(c => (
              <tr key={c.category} className="border-b border-slate-800/50 hover:bg-slate-800/30">
                <td className="p-3 text-slate-200">{c.category}</td>
                <td className="p-3 text-center">{c.total}</td>
                <td className="p-3 text-center text-green-400">{c.passed}</td>
                <td className="p-3 text-center text-red-400">{c.failed}</td>
                <td className="p-3 text-center text-yellow-400">{c.blocked}</td>
                <td className="p-3 text-center text-slate-500">{c.not_started}</td>
                <td className="p-3 text-center">
                  <div className="flex items-center gap-2 justify-center">
                    <div className="w-24 h-2 bg-slate-800 rounded-full overflow-hidden">
                      <div className="h-full bg-green-500 rounded-full" style={{ width: `${c.coverage_pct}%` }} />
                    </div>
                    <span className="text-xs text-slate-400">{c.coverage_pct}%</span>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr className="border-t-2 border-slate-700 font-semibold">
              <td className="p-3">Total</td>
              <td className="p-3 text-center">{total}</td>
              <td className="p-3 text-center text-green-400">{passed}</td>
              <td className="p-3 text-center text-red-400">{coverage.reduce((a,c)=>a+c.failed,0)}</td>
              <td className="p-3 text-center text-yellow-400">{coverage.reduce((a,c)=>a+c.blocked,0)}</td>
              <td className="p-3 text-center text-slate-500">{coverage.reduce((a,c)=>a+c.not_started,0)}</td>
              <td className="p-3 text-center">{total > 0 ? (passed/total*100).toFixed(1) : 0}%</td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  );
}
