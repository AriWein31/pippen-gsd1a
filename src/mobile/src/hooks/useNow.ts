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
      id: 'rec-1',
      priority: 'high',
      category: 'timing',
      headline: 'Late bedtime dose — 3 nights running',
      explanation:
        'Your last 3 bedtime doses were 45–90 minutes late. This is likely causing the overnight lows you logged Tuesday and Wednesday.',
      suggested_action: 'Move tonight\'s dose 30 minutes earlier',
      confidence: 0.82,
      sources: ['pattern:late-dosing'],
      created_at: new Date().toISOString(),
    },
    {
      id: 'rec-2',
      priority: 'medium',
      category: 'glucose',
      headline: 'Average glucose up 18% this week',
      explanation:
        'Your overnight average glucose is 142 mg/dL vs 120 mg/dL last week. Post-dinner spikes are the likely driver.',
      suggested_action: 'Review this week\'s dinner bolus timing with your clinician',
      confidence: 0.71,
      sources: ['baseline:overnight_average_glucose'],
      created_at: new Date().toISOString(),
    },
    {
      id: 'rec-3',
      priority: 'low',
      category: 'general',
      headline: 'Data looks stable — no action needed',
      explanation:
        'No significant changes detected this week. Your glucose management is tracking consistently.',
      suggested_action: 'Keep logging as normal',
      confidence: 0.9,
      sources: [],
      created_at: new Date().toISOString(),
    },
  ],
  changes: [
    {
      metric: 'avg_glucose',
      direction: 'up',
      delta: 22,
      delta_pct: 18,
      summary: 'Avg glucose up 18% from last week',
    },
    {
      metric: 'low_frequency',
      direction: 'up',
      delta: 2,
      delta_pct: 40,
      summary: 'Low events up 40% from last week',
    },
    {
      metric: 'variability',
      direction: 'stable',
      delta: 0.1,
      delta_pct: 3,
      summary: 'Variability essentially unchanged',
    },
    {
      metric: 'bedtime_dose_minutes_late',
      direction: 'up',
      delta: 35,
      delta_pct: 88,
      summary: 'Bedtime dose 35 min later on average',
    },
  ],
  risk: {
    patient_id: PATIENT_ID ?? 'dev-patient',
    risk_score: 3.2,
    risk_level: 'medium',
    confidence: 0.78,
    factors: [
      {
        factor: 'late_dosing',
        weight: 0.35,
        severity: 2,
        confidence: 0.82,
        reason: '3 consecutive late doses at bedtime',
      },
      {
        factor: 'elevated_avg_glucose',
        weight: 0.25,
        severity: 2,
        confidence: 0.71,
        reason: 'Average glucose 18% above baseline',
      },
    ],
    supporting_events: [],
    generated_at: new Date().toISOString(),
  },
  brief: {
    brief_date: new Date().toISOString().split('T')[0],
    patient_id: PATIENT_ID ?? 'dev-patient',
    summary: 'Elevated overnight glucose with recurring late doses',
    what_changed: [
      'Avg glucose rose from 120 to 142 mg/dL',
      'Bedtime dose consistently 45–90 min late',
    ],
    what_matters: [
      'Overnight lows Tuesday and Wednesday may be dose-timing related',
      'Post-dinner spikes driving the weekly average up',
    ],
    recommended_attention: [
      'Shift bedtime dose 30 min earlier tonight',
      'Review dinner bolus timing with clinician at next visit',
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
