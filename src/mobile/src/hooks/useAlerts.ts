/**
 * useAlerts — fetches and manages active intelligence alerts for the current patient.
 *
 * Refreshes every ALERTS_REFRESH_INTERVAL ms when a patient ID is configured.
 * Returns the most recent unacknowledged alerts ordered by severity.
 */

import { useCallback, useEffect, useState } from 'react';
import type {
  Alert,
} from '../types';
import {
  acknowledgeAlert,
  dismissAlert,
  fetchAlerts,
} from '../api/client';

const ALERTS_REFRESH_INTERVAL = 5 * 60 * 1000; // 5 minutes

// Get patient ID from env — same approach as useIntelligence.
const PATIENT_ID = (() => {
  const envId = import.meta.env.VITE_PATIENT_ID;
  return envId && envId.length > 0 ? envId : null;
})();

export interface UseAlertsResult {
  alerts: Alert[];
  isLoading: boolean;
  isError: boolean;
  errorMessage: string | null;
  hasActiveAlerts: boolean;
  criticalCount: number;
  highCount: number;
  mediumCount: number;
  lowCount: number;
  acknowledge: (alertId: string) => Promise<void>;
  dismiss: (alertId: string) => Promise<void>;
  refresh: () => Promise<void>;
}

export function useAlerts(): UseAlertsResult {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isError, setIsError] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!PATIENT_ID) {
      setAlerts([]);
      return;
    }
    setIsLoading(true);
    setIsError(false);
    setErrorMessage(null);
    try {
      const res = await fetchAlerts(PATIENT_ID);
      if (res.success && res.data) {
        setAlerts(res.data.alerts);
      } else {
        setIsError(true);
        setErrorMessage(res.error ?? 'Failed to fetch alerts');
      }
    } catch (e) {
      setIsError(true);
      setErrorMessage(e instanceof Error ? e.message : String(e));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
    const interval = setInterval(() => { void load(); }, ALERTS_REFRESH_INTERVAL);
    return () => clearInterval(interval);
  }, [load]);

  const acknowledge = useCallback(async (alertId: string) => {
    if (!PATIENT_ID) return;
    const res = await acknowledgeAlert(PATIENT_ID, alertId);
    if (res.success) {
      setAlerts(prev => prev.filter(a => a.id !== alertId));
    }
  }, []);

  const dismiss = useCallback(async (alertId: string) => {
    if (!PATIENT_ID) return;
    const res = await dismissAlert(PATIENT_ID, alertId);
    if (res.success) {
      setAlerts(prev => prev.filter(a => a.id !== alertId));
    }
  }, []);

  const hasActiveAlerts = alerts.length > 0;
  const criticalCount = alerts.filter(a => a.alert_severity === 'critical').length;
  const highCount = alerts.filter(a => a.alert_severity === 'high').length;
  const mediumCount = alerts.filter(a => a.alert_severity === 'medium').length;
  const lowCount = alerts.filter(a => a.alert_severity === 'low').length;

  return {
    alerts,
    isLoading,
    isError,
    errorMessage,
    hasActiveAlerts,
    criticalCount,
    highCount,
    mediumCount,
    lowCount,
    acknowledge,
    dismiss,
    refresh: load,
  };
}
