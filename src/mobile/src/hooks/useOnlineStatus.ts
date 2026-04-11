import { useState, useEffect } from 'react';
import { isOnline, onConnectivityChange } from '../api/client';

export function useOnlineStatus(): boolean {
  const [online, setOnline] = useState<boolean>(isOnline());

  useEffect(() => {
    const cleanup = onConnectivityChange(setOnline);
    return cleanup;
  }, []);

  return online;
}

export function useOnlineStatusWithCallback(
  callback: (online: boolean) => void
): void {
  useEffect(() => {
    const cleanup = onConnectivityChange(callback);
    return cleanup;
  }, [callback]);
}
