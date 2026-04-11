import React from 'react';
import { useOnlineStatus } from '../hooks';
import { SyncIcon, CheckIcon, AlertIcon } from './Icons';

interface SyncStatusProps {
  pendingCount: number;
}

export const SyncStatus: React.FC<SyncStatusProps> = ({
  pendingCount,
}) => {
  const online = useOnlineStatus();

  if (!online) {
    return (
      <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#F6F7F9]">
        <AlertIcon size={16} color="#F59E0B" />
        <span className="text-sm text-[#F59E0B] font-medium">Offline</span>
      </div>
    );
  }

  if (pendingCount > 0) {
    return (
      <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#FEF3C7]">
        <SyncIcon size={16} color="#F59E0B" />
        <span className="text-sm text-[#F59E0B] font-medium">
          {pendingCount} pending
        </span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-[#D1FAE5]">
      <CheckIcon size={16} color="#10B981" />
      <span className="text-sm text-[#10B981] font-medium">Synced</span>
    </div>
  );
};
