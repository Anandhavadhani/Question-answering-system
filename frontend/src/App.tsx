import React from 'react';
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import UploadPage from './pages/UploadPage';
import ChatPage from './pages/ChatPage';
import LibraryPage from './pages/LibraryPage';

const navItems = [
  { label: 'Chat', to: '/chat' },
  { label: 'Library', to: '/library' },
  { label: 'Uploads', to: '/upload' },
];

function AppShell() {
  const location = useLocation();

  return (
    <div className="app-shell">
      <aside className="sidebar-panel">
        <div className="brand-row">
          <div className="brand-mark" />
          <div className="brand-name">DocMind</div>
        </div>

        <nav className="sidebar-nav" aria-label="Main navigation">
          {navItems.map(({ label, to }) => {
            const active =
              (to === '/upload' && location.pathname === '/') ||
              location.pathname === to ||
              (to === '/chat' && location.pathname === '/');

            return (
              <Link
                key={to}
                to={to}
                className={`nav-item ${active ? 'active' : ''}`}
              >
                {label}
              </Link>
            );
          })}
        </nav>

        <div className="sidebar-note">
          Answers are grounded only in your uploaded documents.
        </div>
      </aside>

      <main className="workspace-panel">
        <Routes>
          <Route path="/" element={<ChatPage />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/library" element={<LibraryPage />} />
        </Routes>
      </main>
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AppShell />
    </BrowserRouter>
  );
}

export default App;
