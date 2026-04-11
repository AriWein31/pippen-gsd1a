import { useCallback, useEffect, useState } from 'react';

export type NotificationPermissionState = 'unsupported' | 'default' | 'granted' | 'denied';

function getPermission(): NotificationPermissionState {
  if (typeof window === 'undefined' || !('Notification' in window)) {
    return 'unsupported';
  }
  return Notification.permission as NotificationPermissionState;
}

export function useNotifications() {
  const [permission, setPermission] = useState<NotificationPermissionState>(getPermission());
  const [requesting, setRequesting] = useState(false);

  useEffect(() => {
    setPermission(getPermission());
  }, []);

  const requestPermission = useCallback(async () => {
    if (typeof window === 'undefined' || !('Notification' in window)) {
      setPermission('unsupported');
      return 'unsupported' as const;
    }

    setRequesting(true);
    try {
      const result = await Notification.requestPermission();
      setPermission(result as NotificationPermissionState);
      return result as NotificationPermissionState;
    } finally {
      setRequesting(false);
    }
  }, []);

  return {
    permission,
    requesting,
    supported: permission !== 'unsupported',
    requestPermission,
  };
}
