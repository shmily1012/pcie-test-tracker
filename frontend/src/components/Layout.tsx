import { NavLink, Outlet } from 'react-router-dom';
import { LayoutDashboard, List, FileText, Upload, History } from 'lucide-react';

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/test-cases', icon: List, label: 'Test Cases' },
  { to: '/reports', icon: FileText, label: 'Reports' },
  { to: '/import', icon: Upload, label: 'Import' },
  { to: '/audit', icon: History, label: 'Audit Log' },
];

export default function Layout() {
  return (
    <div className="flex h-screen bg-slate-950">
      <aside className="w-56 bg-slate-900 border-r border-slate-800 flex flex-col">
        <div className="p-4 border-b border-slate-800">
          <h1 className="text-lg font-bold text-blue-400 flex items-center gap-2">
            <span className="text-2xl">⚡</span> PCIe Tracker
          </h1>
          <p className="text-xs text-slate-500 mt-1">Test Plan Manager</p>
        </div>
        <nav className="flex-1 p-2 space-y-1">
          {navItems.map(item => (
            <NavLink key={item.to} to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                  isActive ? 'bg-blue-500/20 text-blue-400' : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
                }`
              }>
              <item.icon size={18} />
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="p-4 border-t border-slate-800 text-xs text-slate-600">
          v1.0.0 · PCIe 5.0 + OCP 2.5
        </div>
      </aside>
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
