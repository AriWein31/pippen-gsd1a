/**
 * useNow — polls the unified /patients/{id}/now endpoint every 5 minutes.
 * Returns NowScreen data including recommendations, changes, risk, brief, and alerts.
 */

import { useCallback, useEffect, useState } from 'react';
import { fetchNow } from '../api/client';
import type { NowScreen, Recommendation, Change } from '../api/client';

const NOW_REFRESH_INTERVAL = 5 * 60 * 1000; // 5 minutes

function getPatientId(): string | null {
  const envId = import.meta.env.VITE_PATIENT_ID;
  if (envId && envId.length > 0) return envId;
  return null;
}

const PATIENT_ID = getPatientId();

// Realistic mock data for development when backend is unavailable
const MOCK_NOW: NowScreen = {
  patient_id: PATIENT_ID ?? 'dev-patient',
  generated_at: new Date().toISOString(),
  recommendations: [
    {
      id: 'rec-dev-1',
      priority: 'high',
      category: 'timing',
      headline: 'Pattern detected: review needed',
      explanation:
        'A recurring pattern has been detected. Check the intelligence panel for details.',
      suggested_action: 'Review this pattern with your clinician at your next visit',
      confidence: 0.80,
      sources: ['pattern:detected'],
      created_at: new Date().toISOString(),
    },
    {
      id: 'rec-dev-2',
      priority: 'medium',
      category: 'glucose',
      headline: 'Weekly summary available',
      explanation:
        'Your weekly glucose summary is ready. Review the changes panel for week-over-week trends.',
      suggested_action: 'Check the Changes panel for details',
      confidence: 0.70,
      sources: ['baseline:weekly_summary'],
      created_at: new Date().toISOString(),
    },
    {
      id: 'rec-dev-3',
      priority: 'low',
      category: 'general',
      headline: 'All metrics within target range',
      explanation:
        'No significant changes or alerts detected this week. Continue with your current care plan.',
      suggested_action: 'Keep logging as normal',
      confidence: 0.85,
      sources: [],
      created_at: new Date().toISOString(),
    },
  ],
  changes: [
    {
      metric: 'avg_glucose',
      direction: 'up',
      delta: 10,
      delta_pct: 8,
      summary: 'Avg glucose slightly up this week',
    },
    {
      metric: 'low_frequency',
      direction: 'stable',
      delta: 0,
      delta_pct: 2,
      summary: 'Low event frequency unchanged',
    },
    {
      metric: 'variability',
      direction: 'stable',
      delta: 0.05,
      delta_pct: 5,
      summary: 'Variability within normal range',
    },
    {
      metric: 'bedtime_dose_timing',
      direction: 'stable',
      delta: 5,
      delta_pct: 8,
      summary: 'Bedtime dose timing consistent',
    },
  ],
  risk: {
    patient_id: PATIENT_ID ?? 'dev-patient',
    risk_score: 2.0,
    risk_level: 'low',
    confidence: 0.75,
    factors: [
      {
        factor: 'recent_stability',
        weight: 0.4,
        severity: 1,
        confidence: 0.80,
        reason: 'Glucose metrics within normal range this week',
      },
    ],
    supporting_events: [],
    generated_at: new Date().toISOString(),
  },
  brief: {
    brief_date: new Date().toISOString().split('T')[0],
    patient_id: PATIENT_ID ?? 'dev-patient',
    summary: 'Week progressed within target ranges with no critical events',
    what_changed: [
      'No significant changes in overnight glucose metrics',
      'Bedtime dosing timing remains consistent',
    ],
    what_matters: [
      'Continue monitoring as normal',
      'Keep logging all overnight readings',
    ],
    recommended_attention: [
      'Maintain current logging routine',
      'Review any deviations with your clinician',
    ],
    confidence: 0.75,
    supporting_events: [],
    generated_at: new Date().toISOString(),
  },
  active_alerts: [],
};

export interface UseNowResult {
  nowData: NowScreen | null;
  recommendations: Recommendation[];
  changes: Change[];
  loading: boolean;
  error: string | null;
  isConfigured: boolean;
  isMock: boolean;
  refetch: () => Promise<void>;
}

export function useNow(): UseNowResult {
  const [nowData, setNowData] = useState<NowScreen | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isConfigured, setIsConfigured] = useState(!!PATIENT_ID);
  const [isMock, setIsMock] = useState(false);

  const load = useCallback(async (): Promise<void> => {
    if (!PATIENT_ID) {
      setIsConfigured(false);
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const res = await fetchNow(PATIENT_ID);
      if (res.success && res.data) {
        setNowData(res.data);
        setIsMock(false);
      } else {
        // Backend unavailable — fall back to mock data for dev
        setNowData(MOCK_NOW);
        setIsMock(true);
      }
    } catch {
      setNowData(MOCK_NOW);
      setIsMock(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
    const interval = setInterval(() => { void load(); }, NOW_REFRESH_INTERVAL);
    return () => clearInterval(interval);
  }, [load]);

  return {
    nowData,
    recommendations: nowData?.recommendations ?? [],
    changes: nowData?.changes ?? [],
    loading,
    error,
    isConfigured,
    isMock,
    refetch: load,
  };
}
