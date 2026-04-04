import { useState, useEffect } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { LayoutDashboard, List, FileText, Upload, History, Search } from 'lucide-react';
import FindDialog from './FindDialog';

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/test-cases', icon: List, label: 'Test Cases' },
  { to: '/reports', icon: FileText, label: 'Reports' },
  { to: '/import', icon: Upload, label: 'Import' },
  { to: '/audit', icon: History, label: 'Audit Log' },
];

export default function Layout() {
  const [findOpen, setFindOpen] = useState(false);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setFindOpen(v => !v);
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, []);

  return (
    <div className="flex h-screen" style={{ background: '#0f0e0d' }}>
      <aside
        className="w-56 flex flex-col"
        style={{ background: '#2d2a27', borderRight: '1px solid #803812' }}
      >
        <div className="p-4" style={{ borderBottom: '1px solid #803812' }}>
          <h1 className="text-lg font-bold flex items-center gap-2" style={{ color: '#FE7B23' }}>
            <span className="text-2xl">⚡</span> PCIe Tracker
          </h1>
          <p className="text-xs mt-1" style={{ color: '#55250c' }}>Test Plan Manager</p>
        </div>
        <button onClick={() => setFindOpen(true)}
          className="mx-2 mt-2 flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors"
          style={{ background: 'rgba(254, 123, 35, 0.08)', color: '#fff5e3aa', border: '1px solid #803812' }}>
          <Search size={16} />
          <span className="flex-1 text-left">Find...</span>
          <kbd className="text-[10px] border rounded px-1 py-0.5" style={{ borderColor: '#803812', color: '#55250c' }}>
            Ctrl K
          </kbd>
        </button>
        <nav className="flex-1 p-2 space-y-1">
          {navItems.map(item => (
            <NavLink key={item.to} to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                  isActive ? '' : ''
                }`
              }
              style={({ isActive }) => ({
                background: isActive ? 'rgba(254, 123, 35, 0.15)' : 'transparent',
                color: isActive ? '#FE7B23' : '#fff5e3aa',
              })}
            >
              <item.icon size={18} />
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="p-4 text-xs" style={{ borderTop: '1px solid #803812', color: '#55250c' }}>
          v1.0.0 · PCIe 5.0 + OCP 2.5
        </div>
      </aside>
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
      <FindDialog open={findOpen} onClose={() => setFindOpen(false)} />
    </div>
  );
}
