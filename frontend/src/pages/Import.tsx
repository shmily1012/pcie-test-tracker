import { useState } from 'react';
import { importMarkdown } from '../lib/api';
import { Upload, CheckCircle, AlertCircle } from 'lucide-react';

export default function Import() {
  const [file, setFile] = useState<File | null>(null);
  const [specSource, setSpecSource] = useState('');
  const [result, setResult] = useState<{ created: number; updated: number; errors: string[] } | null>(null);
  const [loading, setLoading] = useState(false);

  const handleImport = async () => {
    if (!file) return;
    setLoading(true);
    try {
      const r = await importMarkdown(file, specSource || undefined);
      setResult(r);
    } catch (e: any) {
      setResult({ created: 0, updated: 0, errors: [e.message] });
    }
    setLoading(false);
  };

  return (
    <div className="p-6 space-y-6">
      <h2 className="text-2xl font-bold">Import Test Plan</h2>
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-4 max-w-xl">
        <div>
          <label className="block text-sm text-slate-400 mb-2">Markdown File</label>
          <input type="file" accept=".md" onChange={e => setFile(e.target.files?.[0] || null)}
            className="text-sm text-slate-200 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0
              file:text-sm file:font-medium file:bg-blue-600 file:text-white hover:file:bg-blue-500" />
        </div>
        <div>
          <label className="block text-sm text-slate-400 mb-2">Spec Source (optional)</label>
          <input value={specSource} onChange={e => setSpecSource(e.target.value)} placeholder="e.g. PCIe Base 5.0"
            className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 w-full" />
        </div>
        <button onClick={handleImport} disabled={!file || loading}
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white px-4 py-2 rounded-lg text-sm">
          <Upload size={16} /> {loading ? 'Importing...' : 'Import'}
        </button>
        {result && (
          <div className={`p-4 rounded-lg ${result.errors.length ? 'bg-yellow-500/10 border border-yellow-500/30' : 'bg-green-500/10 border border-green-500/30'}`}>
            <div className="flex items-center gap-2 mb-2">
              {result.errors.length ? <AlertCircle size={16} className="text-yellow-400" /> : <CheckCircle size={16} className="text-green-400" />}
              <span className="font-medium">{result.created} created, {result.updated} updated</span>
            </div>
            {result.errors.map((e, i) => <p key={i} className="text-xs text-yellow-400">{e}</p>)}
          </div>
        )}
      </div>
    </div>
  );
}
