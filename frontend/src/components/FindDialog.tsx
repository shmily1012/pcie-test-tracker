import { useEffect, useState, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { fetchTestCases, type TestCase } from '../lib/api';
import { Search, X, ArrowRight } from 'lucide-react';
import { PriorityBadge, StatusBadge } from './StatusBadge';

export default function FindDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<TestCase[]>([]);
  const [selected, setSelected] = useState(0);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  useEffect(() => {
    if (open) {
      setQuery('');
      setResults([]);
      setSelected(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  const doSearch = useCallback((q: string) => {
    if (!q.trim()) { setResults([]); return; }
    setLoading(true);
    fetchTestCases({ search: q, limit: '20' }).then(data => {
      setResults(data);
      setSelected(0);
    }).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => doSearch(query), 200);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [query, doSearch]);

  const goTo = (tc: TestCase) => {
    onClose();
    navigate(`/test-cases/${tc.id}`);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); setSelected(s => Math.min(s + 1, results.length - 1)); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setSelected(s => Math.max(s - 1, 0)); }
    else if (e.key === 'Enter' && results[selected]) { goTo(results[selected]); }
    else if (e.key === 'Escape') { onClose(); }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh]" onClick={onClose}>
      <div className="fixed inset-0 bg-black/60" />
      <div className="relative w-full max-w-xl bg-slate-900 border border-slate-700 rounded-xl shadow-2xl overflow-hidden"
        onClick={e => e.stopPropagation()}>
        <div className="flex items-center gap-3 px-4 py-3 border-b border-slate-800">
          <Search size={18} className="text-slate-500 shrink-0" />
          <input ref={inputRef} value={query} onChange={e => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Find test cases by ID, title, or description..."
            className="flex-1 bg-transparent text-slate-200 text-sm outline-none placeholder:text-slate-600" />
          {query && (
            <button onClick={() => setQuery('')} className="text-slate-500 hover:text-slate-300">
              <X size={16} />
            </button>
          )}
          <kbd className="hidden sm:inline-block text-[10px] text-slate-600 border border-slate-700 rounded px-1.5 py-0.5">ESC</kbd>
        </div>

        {query.trim() && (
          <div className="max-h-[50vh] overflow-y-auto">
            {loading && results.length === 0 && (
              <div className="p-6 text-center text-slate-500 text-sm">Searching...</div>
            )}
            {!loading && results.length === 0 && query.trim() && (
              <div className="p-6 text-center text-slate-500 text-sm">No test cases found</div>
            )}
            {results.map((tc, i) => (
              <button key={tc.id} onClick={() => goTo(tc)}
                onMouseEnter={() => setSelected(i)}
                className={`w-full text-left px-4 py-3 flex items-center gap-3 transition-colors ${
                  i === selected ? 'bg-slate-800' : 'hover:bg-slate-800/50'
                }`}>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-blue-400 text-sm shrink-0">{tc.id}</span>
                    <span className="text-slate-200 text-sm truncate">{tc.title}</span>
                  </div>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-xs text-slate-500">{tc.category}</span>
                    <StatusBadge status={tc.status} />
                    <PriorityBadge priority={tc.priority} />
                  </div>
                </div>
                {i === selected && <ArrowRight size={14} className="text-slate-500 shrink-0" />}
              </button>
            ))}
          </div>
        )}

        {!query.trim() && (
          <div className="p-6 text-center text-slate-600 text-xs">
            Type to search across {'\u00B7'} Use <kbd className="border border-slate-700 rounded px-1 py-0.5 mx-0.5">↑↓</kbd> to navigate {'\u00B7'} <kbd className="border border-slate-700 rounded px-1 py-0.5 mx-0.5">Enter</kbd> to open
          </div>
        )}
      </div>
    </div>
  );
}
