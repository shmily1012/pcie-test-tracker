import { useEffect, useState, useMemo, useRef, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useReactTable, getCoreRowModel, getSortedRowModel,
         getPaginationRowModel, flexRender, type ColumnDef, type SortingState } from '@tanstack/react-table';
import { fetchTestCases, fetchFilters, updateStatus, type TestCase, type FilterOptions } from '../lib/api';
import { PriorityBadge } from '../components/StatusBadge';
import { Search, ChevronUp, ChevronDown, X } from 'lucide-react';

const statusOptions = ['not_started', 'pass', 'fail', 'blocked', 'skip'];

export default function TestCases() {
  const [data, setData] = useState<TestCase[]>([]);
  const [filters, setFilters] = useState<FilterOptions | null>(null);
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [catFilter, setCatFilter] = useState<string>('');
  const [priFilter, setPriFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [specSourceFilter, setSpecSourceFilter] = useState<string>('');
  const [sorting, setSorting] = useState<SortingState>([]);
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const initialPage = parseInt(searchParams.get('page') || '1', 10) - 1;
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  // Debounce search input
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => setDebouncedSearch(search), 250);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [search]);

  const load = useCallback(() => {
    const params: Record<string, string> = {};
    if (debouncedSearch) params.search = debouncedSearch;
    if (catFilter) params.category = catFilter;
    if (priFilter) params.priority = priFilter;
    if (statusFilter) params.status = statusFilter;
    if (specSourceFilter) params.spec_source = specSourceFilter;
    fetchTestCases(params).then(setData);
  }, [debouncedSearch, catFilter, priFilter, statusFilter, specSourceFilter]);

  useEffect(() => { load(); fetchFilters().then(setFilters); }, []);
  useEffect(() => { load(); }, [debouncedSearch, catFilter, priFilter, statusFilter, specSourceFilter]);

  const hasActiveFilters = catFilter || priFilter || statusFilter || specSourceFilter || debouncedSearch;
  const clearAllFilters = () => {
    setSearch(''); setCatFilter(''); setPriFilter(''); setStatusFilter(''); setSpecSourceFilter('');
  };

  const handleStatusChange = async (id: string, status: string) => {
    await updateStatus(id, status);
    load();
  };

  const columns = useMemo<ColumnDef<TestCase>[]>(() => [
    { accessorKey: 'id', header: 'ID', size: 120,
      cell: ({ row }) => <span className="font-mono text-blue-400 cursor-pointer hover:underline"
        onClick={() => navigate(`/test-cases/${row.original.id}`)}>{row.original.id}</span> },
    { accessorKey: 'title', header: 'Title', size: 300,
      cell: ({ row }) => <span className="text-slate-200 truncate block max-w-[300px]">{row.original.title}</span> },
    { accessorKey: 'category', header: 'Category', size: 180 },
    { accessorKey: 'priority', header: 'Priority', size: 80,
      cell: ({ row }) => <PriorityBadge priority={row.original.priority} /> },
    { accessorKey: 'spec_ref', header: 'Spec Ref', size: 140,
      cell: ({ row }) => <span className="text-slate-400 text-xs font-mono">{row.original.spec_ref || '—'}</span> },
    { accessorKey: 'status', header: 'Status', size: 140,
      cell: ({ row }) => (
        <select value={row.original.status}
          onChange={(e) => handleStatusChange(row.original.id, e.target.value)}
          className="bg-slate-800 border border-slate-700 rounded px-2 py-1 text-xs text-slate-200 cursor-pointer">
          {statusOptions.map(s => <option key={s} value={s}>{s.replace('_', ' ')}</option>)}
        </select>
      ) },
    { accessorKey: 'owner', header: 'Owner', size: 100,
      cell: ({ row }) => <span className="text-slate-400">{row.original.owner || '—'}</span> },
  ], [navigate]);

  const table = useReactTable({
    data, columns, state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: { pagination: { pageSize: 50, pageIndex: initialPage } },
  });

  // Sync page to URL when it changes
  useEffect(() => {
    const currentPage = table.getState().pagination.pageIndex + 1;
    const urlPage = parseInt(searchParams.get('page') || '1', 10);
    if (currentPage !== urlPage) {
      setSearchParams(prev => {
        const newParams = new URLSearchParams(prev);
        if (currentPage === 1) {
          newParams.delete('page');
        } else {
          newParams.set('page', String(currentPage));
        }
        return newParams;
      }, { replace: true });
    }
  }, [table.getState().pagination.pageIndex]);

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Test Cases</h2>
        <span className="text-slate-400 text-sm">{data.length} items</span>
      </div>

      <div className="flex gap-3 items-center flex-wrap">
        <div className="relative">
          <Search size={16} className="absolute left-3 top-2.5 text-slate-500" />
          <input type="text" placeholder="Search ID, title, description..." value={search} onChange={e => setSearch(e.target.value)}
            className="bg-slate-900 border border-slate-700 rounded-lg pl-9 pr-8 py-2 text-sm text-slate-200 w-72
              focus:outline-none focus:border-blue-500" />
          {search && (
            <button onClick={() => setSearch('')} className="absolute right-2.5 top-2.5 text-slate-500 hover:text-slate-300">
              <X size={16} />
            </button>
          )}
        </div>
        <select value={catFilter} onChange={e => setCatFilter(e.target.value)}
          className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200">
          <option value="">All Categories</option>
          {filters?.categories.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
        <select value={priFilter} onChange={e => setPriFilter(e.target.value)}
          className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200">
          <option value="">All Priorities</option>
          {filters?.priorities.map(p => <option key={p} value={p}>{p}</option>)}
        </select>
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
          className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200">
          <option value="">All Statuses</option>
          {statusOptions.map(s => <option key={s} value={s}>{s.replace('_', ' ')}</option>)}
        </select>
        <select value={specSourceFilter} onChange={e => setSpecSourceFilter(e.target.value)}
          className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200">
          <option value="">All Spec Sources</option>
          {filters?.spec_sources.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        {hasActiveFilters && (
          <button onClick={clearAllFilters}
            className="flex items-center gap-1 px-3 py-2 text-sm text-slate-400 hover:text-slate-200
              bg-slate-900 border border-slate-700 rounded-lg transition-colors">
            <X size={14} /> Clear
          </button>
        )}
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              {table.getHeaderGroups().map(hg => (
                <tr key={hg.id} className="border-b border-slate-800">
                  {hg.headers.map(h => (
                    <th key={h.id} className="text-left p-3 text-slate-400 font-medium cursor-pointer select-none
                        hover:text-slate-200 transition-colors"
                      onClick={h.column.getToggleSortingHandler()} style={{ width: h.getSize() }}>
                      <div className="flex items-center gap-1">
                        {flexRender(h.column.columnDef.header, h.getContext())}
                        {h.column.getIsSorted() === 'asc' ? <ChevronUp size={14} /> :
                         h.column.getIsSorted() === 'desc' ? <ChevronDown size={14} /> : null}
                      </div>
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody>
              {table.getRowModel().rows.map(row => (
                <tr key={row.id} className="border-b border-slate-800/50 hover:bg-slate-800/50 transition-colors">
                  {row.getVisibleCells().map(cell => (
                    <td key={cell.id} className="p-3">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="flex items-center justify-between p-3 border-t border-slate-800 text-sm text-slate-400">
          <span>Page {table.getState().pagination.pageIndex + 1} of {table.getPageCount()}</span>
          <div className="flex gap-2">
            <button onClick={() => table.previousPage()} disabled={!table.getCanPreviousPage()}
              className="px-3 py-1 bg-slate-800 rounded disabled:opacity-30 hover:bg-slate-700">Prev</button>
            <button onClick={() => table.nextPage()} disabled={!table.getCanNextPage()}
              className="px-3 py-1 bg-slate-800 rounded disabled:opacity-30 hover:bg-slate-700">Next</button>
          </div>
        </div>
      </div>
    </div>
  );
}
