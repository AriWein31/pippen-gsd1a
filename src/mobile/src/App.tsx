import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { BottomNav } from './components';
import {
  NowPage,
  TrendsPage,
  WatchPage,
  ActionsPage,
  ProfilePage,
} from './pages';
import { startBackgroundSync } from './api/sync';

const App: React.FC = () => {
  useEffect(() => {
    // Start background sync when app loads
    startBackgroundSync(30000); // Every 30 seconds

    // Register service worker for PWA offline support
    if ('serviceWorker' in navigator) {
      window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js').catch(() => {
          // Service worker registration failed - continue without it
        });
      });
    }
  }, []);

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-[#F6F7F9]">
        <Routes>
          <Route path="/" element={<NowPage />} />
          <Route path="/trends" element={<TrendsPage />} />
          <Route path="/watch" element={<WatchPage />} />
          <Route path="/actions" element={<ActionsPage />} />
          <Route path="/profile" element={<ProfilePage />} />
        </Routes>
        <BottomNav />
      </div>
    </BrowserRouter>
  );
};

export default App;
