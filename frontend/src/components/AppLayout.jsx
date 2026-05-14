import { Menu } from "lucide-react";
import { useState } from "react";
import Sidebar from "./Sidebar";

export default function AppLayout({ title, subtitle, actions, children }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="app-shell">
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      {sidebarOpen && (
        <button
          className="sidebar-scrim"
          onClick={() => setSidebarOpen(false)}
          aria-label="Close navigation"
        />
      )}
      <main className="app-main">
        <header className="page-header">
          <div className="page-title-row">
            <button
              className="icon-btn mobile-menu"
              onClick={() => setSidebarOpen(true)}
              aria-label="Open navigation"
            >
              <Menu size={20} />
            </button>
            <div>
              <h1>{title}</h1>
              {subtitle && <p>{subtitle}</p>}
            </div>
          </div>
          {actions && <div className="page-actions">{actions}</div>}
        </header>
        {children}
      </main>
    </div>
  );
}
