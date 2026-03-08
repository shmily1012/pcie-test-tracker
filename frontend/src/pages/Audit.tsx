import { useEffect, useState } from 'react';
import api from '../lib/api';

interface AuditEntry {
  id: number; entity_type: string; entity_id: string; action: string;
  changed_by?: string; old_value?: string; new_value?: string; changed_at?: string;
}

export default function Audit() {
  const [logs, setLogs] = useState<AuditEntry[]>([]);
  useEffect(() => { api.get('/audit?limit=200').then(r => setLogs(r.data)); }, []);

  return (
    <div className="p-6 space-y-4">
      <h2 className="text-2xl font-bold">Audit Log</h2>
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead><tr className="border-b border-slate-800">
            <th className="text-left p-3 text-slate-400">Time</th>
            <th className="text-left p-3 text-slate-400">Action</th>
            <th className="text-left p-3 text-slate-400">Entity</th>
            <th className="text-left p-3 text-slate-400">By</th>
            <th className="text-left p-3 text-slate-400">Details</th>
          </tr></thead>
          <tbody>
            {logs.map(l => (
              <tr key={l.id} className="border-b border-slate-800/50 hover:bg-slate-800/30">
                <td className="p-3 text-xs text-slate-500">{l.changed_at ? new Date(l.changed_at).toLocaleString() : ''}</td>
                <td className="p-3"><span className={`px-2 py-0.5 rounded text-xs font-medium ${
                  l.action === 'create' ? 'bg-green-500/20 text-green-400' :
                  l.action === 'delete' ? 'bg-red-500/20 text-red-400' : 'bg-blue-500/20 text-blue-400'
                }`}>{l.action}</span></td>
                <td className="p-3 font-mono text-blue-400 text-xs">{l.entity_type}/{l.entity_id}</td>
                <td className="p-3 text-slate-400">{l.changed_by || '—'}</td>
                <td className="p-3 text-xs text-slate-500 max-w-xs truncate">{l.new_value?.slice(0, 80)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
