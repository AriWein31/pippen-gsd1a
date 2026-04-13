import { useState, useEffect, useCallback } from 'react';
import { fetchIntelligence } from '../api/client';
import type {
  BaselineMetric,
  PatternSignal,
  RiskScore,
  DailyBrief,
  IntelligenceView,
} from '../types';

// Returns the configured patient ID, or null when VITE_PATIENT_ID is not set.
// Do NOT fabricate an anonymous ID — that pollutes the intelligence backend
// with unidentifiable data and masks the configuration gap.
function getPatientId(): string | null {
  const envId = import.meta.env.VITE_PATIENT_ID;
  if (envId && envId.length > 0) return envId;
  return null;
}

const PATIENT_ID = getPatientId();

interface UseIntelligenceResult extends IntelligenceView {
  refetch: () => Promise<void>;
}

export function useIntelligence(
  refreshIntervalMs: number = 300000 // 5 minutes
): UseIntelligenceResult {
  const [risk, setRisk] = useState<RiskScore | null>(null);
  const [baselines, setBaselines] = useState<BaselineMetric[]>([]);
  const [patterns, setPatterns] = useState<PatternSignal[]>([]);
  const [brief, setBrief] = useState<DailyBrief | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [hasSufficientData, setHasSufficientData] = useState(false);
  const [isDegraded, setIsDegraded] = useState(false);
  const [isConfigured, setIsConfigured] = useState(!!PATIENT_ID);

  const fetchData = useCallback(async (): Promise<void> => {
    // Guard: skip fetch entirely when patient ID is not configured
    if (!PATIENT_ID) {
      setIsConfigured(false);
      setIsLoading(false);
      return;
    }

    try {
      const result = await fetchIntelligence(PATIENT_ID);
      setRisk(result.risk);
      setBaselines(result.baselines);
      setPatterns(result.patterns);
      setBrief(result.brief);
      setIsDegraded(result.isPartial);
      setIsConfigured(true);

      // Require at least one baseline with a real (non-null) value before
      // marking data as sufficient. A fallback brief alone does not count.
      const hasBaselineData = result.baselines.some(m => m.value !== null);
      setHasSufficientData(hasBaselineData);
    } catch {
      // keep previous values on error
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchData();

    const intervalId = setInterval(() => {
      void fetchData();
    }, refreshIntervalMs);

    return () => clearInterval(intervalId);
  }, [fetchData, refreshIntervalMs]);

  return { risk, baselines, patterns, brief, isLoading, hasSufficientData, isDegraded, isConfigured, refetch: fetchData };
}