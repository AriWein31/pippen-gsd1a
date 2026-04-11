import React from 'react';
import { Card, CardContent, CardHeader } from '../components/Card';
import { Button } from '../components/Button';
import { ProfileIcon, SyncIcon, MoonIcon, BellIcon } from '../components/Icons';
import { SyncStatus } from '../components/SyncStatus';
import { useOnlineStatus, useNotifications } from '../hooks';
import { processSyncQueue } from '../api/sync';
import { getPendingCount } from '../db/database';
import { useState, useEffect } from 'react';

export const ProfilePage: React.FC = () => {
  const online = useOnlineStatus();
  const [pendingCount, setPendingCount] = useState(0);
  const [syncing, setSyncing] = useState(false);
  const { permission, requesting, supported, requestPermission } = useNotifications();

  useEffect(() => {
    void getPendingCount().then(setPendingCount);
  }, []);

  const handleManualSync = async (): Promise<void> => {
    if (!online || syncing) return;
    setSyncing(true);
    await processSyncQueue();
    const count = await getPendingCount();
    setPendingCount(count);
    setSyncing(false);
  };

  return (
    <div className="min-h-screen bg-[#F6F7F9] pb-20">
      {/* Header */}
      <header className="bg-white px-4 py-6 border-b border-[#E5E7EB]">
        <h1 className="text-2xl font-bold text-[#1A1D21]">Profile</h1>
        <p className="text-sm text-[#8A8E97] mt-0.5">
          Settings and account info
        </p>
      </header>

      {/* Profile Card */}
      <section className="px-4 py-6">
        <Card>
          <CardContent>
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 rounded-full bg-[#315BFF] flex items-center justify-center">
                <ProfileIcon size={32} color="#FFFFFF" />
              </div>
              <div>
                <p className="font-semibold text-lg text-[#1A1D21]">
                  Patient
                </p>
                <p className="text-sm text-[#8A8E97]">
                  {import.meta.env.VITE_PATIENT_ID || 'default-patient'}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </section>

      {/* Sync Status */}
      <section className="px-4 py-6">
        <Card variant="outlined">
          <CardHeader>Sync Status</CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <SyncIcon size={20} color="#315BFF" />
                <div>
                  <p className="font-medium text-[#1A1D21]">Sync Queue</p>
                  <p className="text-sm text-[#8A8E97]">
                    {pendingCount} items pending
                  </p>
                </div>
              </div>
              <SyncStatus pendingCount={pendingCount} />
            </div>
            <Button
              variant="secondary"
              fullWidth
              onClick={void handleManualSync}
              loading={syncing}
              disabled={!online || pendingCount === 0}
            >
              {syncing ? 'Syncing...' : 'Sync Now'}
            </Button>
          </CardContent>
        </Card>
      </section>

      {/* Settings */}
      <section className="px-4 py-6">
        <Card variant="outlined">
          <CardHeader>Settings</CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between py-2">
              <div className="flex items-center gap-3">
                <MoonIcon size={20} color="#315BFF" />
                <p className="font-medium text-[#1A1D21]">Night Mode</p>
              </div>
              <button
                className="w-12 h-7 rounded-full bg-[#E5E7EB] transition-colors duration-200"
                disabled
              >
                <span className="block w-5 h-5 bg-white rounded-full shadow translate-x-1" />
              </button>
            </div>
            <div className="flex items-center justify-between py-2 gap-3">
              <div className="flex items-center gap-3">
                <BellIcon size={20} color="#315BFF" />
                <div>
                  <p className="font-medium text-[#1A1D21]">Notifications</p>
                  <p className="text-sm text-[#8A8E97]">
                    {supported ? `Permission: ${permission}` : 'Not supported in this browser'}
                  </p>
                </div>
              </div>
              <Button
                variant="secondary"
                onClick={() => {
                  void requestPermission();
                }}
                disabled={!supported || permission === 'granted' || requesting}
              >
                {permission === 'granted' ? 'Enabled' : requesting ? 'Requesting...' : 'Enable'}
              </Button>
            </div>
            <p className="text-sm text-[#8A8E97] pt-2">
              Week 4: notification permissions and alarm readiness are wired.
            </p>
          </CardContent>
        </Card>
      </section>

      {/* About */}
      <section className="px-4 py-6">
        <Card variant="outlined">
          <CardHeader>About</CardHeader>
          <CardContent>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-[#8A8E97]">App Version</span>
                <span className="text-[#1A1D21]">0.1.0</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#8A8E97]">Build</span>
                <span className="text-[#1A1D21]">Week 4</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#8A8E97]">Offline Support</span>
                <span className="text-[#10B981] font-medium">✓ Enabled</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </section>

      {/* Debug Info */}
      <section className="px-4 py-6">
        <Card variant="outlined">
          <CardContent>
            <p className="text-xs text-[#8A8E97] text-center">
              Pippen Mobile App • Built with React + TypeScript
              <br />
              Week 4: Night Alarm Readiness
            </p>
          </CardContent>
        </Card>
      </section>
    </div>
  );
};
