const statusConfig: Record<string, { label: string; bg: string; text: string }> = {
  pass: { label: 'Pass', bg: 'bg-green-500/20', text: 'text-green-400' },
  fail: { label: 'Fail', bg: 'bg-red-500/20', text: 'text-red-400' },
  blocked: { label: 'Blocked', bg: 'bg-yellow-500/20', text: 'text-yellow-400' },
  skip: { label: 'Skip', bg: 'bg-gray-500/20', text: 'text-gray-400' },
  not_started: { label: 'Not Started', bg: 'bg-slate-500/20', text: 'text-slate-400' },
};

const priorityConfig: Record<string, { bg: string; text: string }> = {
  P0: { bg: 'bg-red-500/20', text: 'text-red-400' },
  P1: { bg: 'bg-yellow-500/20', text: 'text-yellow-400' },
  P2: { bg: 'bg-blue-500/20', text: 'text-blue-400' },
};

export function StatusBadge({ status }: { status: string }) {
  const cfg = statusConfig[status] || statusConfig.not_started;
  return <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${cfg.bg} ${cfg.text}`}>{cfg.label}</span>;
}

export function PriorityBadge({ priority }: { priority: string }) {
  const cfg = priorityConfig[priority] || { bg: 'bg-slate-500/20', text: 'text-slate-400' };
  return <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${cfg.bg} ${cfg.text}`}>{priority}</span>;
}
