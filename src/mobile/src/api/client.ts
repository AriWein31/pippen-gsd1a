import type {
  GlucoseEntry,
  CornstarchEntry,
  MealEntry,
  SymptomEntry,
  ActiveCourse,
  ApiResponse,
  BaselineMetric,
  PatternSignal,
  RiskScore,
  DailyBrief,
} from '../types';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000/api';

async function fetchApi<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return {
        success: false,
        error: errorData.error || `HTTP ${response.status}: ${response.statusText}`,
      };
    }

    const data = await response.json();
    return { success: true, data };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Network error',
    };
  }
}

// Log glucose reading
export async function logGlucose(
  patientId: string,
  entry: Omit<GlucoseEntry, 'id' | 'patientId' | 'createdAt' | 'syncStatus'>
): Promise<ApiResponse<GlucoseEntry>> {
  return fetchApi<GlucoseEntry>(`/patients/${patientId}/glucose`, {
    method: 'POST',
    body: JSON.stringify(entry),
  });
}

// Log cornstarch
export async function logCornstarch(
  patientId: string,
  entry: Omit<CornstarchEntry, 'id' | 'patientId' | 'createdAt' | 'syncStatus'>
): Promise<ApiResponse<CornstarchEntry>> {
  return fetchApi<CornstarchEntry>(`/patients/${patientId}/cornstarch`, {
    method: 'POST',
    body: JSON.stringify(entry),
  });
}

// Log meal
export async function logMeal(
  patientId: string,
  entry: Omit<MealEntry, 'id' | 'patientId' | 'createdAt' | 'syncStatus'>
): Promise<ApiResponse<MealEntry>> {
  return fetchApi<MealEntry>(`/patients/${patientId}/meals`, {
    method: 'POST',
    body: JSON.stringify(entry),
  });
}

// Log symptom
export async function logSymptom(
  patientId: string,
  entry: Omit<SymptomEntry, 'id' | 'patientId' | 'createdAt' | 'syncStatus'>
): Promise<ApiResponse<SymptomEntry>> {
  return fetchApi<SymptomEntry>(`/patients/${patientId}/symptoms`, {
    method: 'POST',
    body: JSON.stringify(entry),
  });
}

// Get active course
export async function getActiveCourse(
  patientId: string
): Promise<ApiResponse<ActiveCourse>> {
  return fetchApi<ActiveCourse>(`/patients/${patientId}/active-course`);
}

// ---- Intelligence Endpoints (Week 6) ----

// Get risk score
export async function getRiskScore(
  patientId: string
): Promise<ApiResponse<RiskScore>> {
  return fetchApi<RiskScore>(`/patients/${patientId}/risk`);
}

// Get baselines
export async function getBaselines(
  patientId: string
): Promise<ApiResponse<BaselineMetric[]>> {
  return fetchApi<BaselineMetric[]>(`/patients/${patientId}/baselines`);
}

// Get patterns
export async function getPatterns(
  patientId: string
): Promise<ApiResponse<PatternSignal[]>> {
  return fetchApi<PatternSignal[]>(`/patients/${patientId}/patterns`);
}

// Get daily brief
export async function getDailyBrief(
  patientId: string
): Promise<ApiResponse<DailyBrief>> {
  return fetchApi<DailyBrief>(`/patients/${patientId}/daily-brief`);
}

// Fetch all intelligence data in parallel
export async function fetchIntelligence(
  patientId: string
): Promise<{
  risk: RiskScore | null;
  baselines: BaselineMetric[];
  patterns: PatternSignal[];
  brief: DailyBrief | null;
  isPartial: boolean;  // true when ≥1 endpoint failed
}> {
  const results = await Promise.allSettled([
    getRiskScore(patientId),
    getBaselines(patientId),
    getPatterns(patientId),
    getDailyBrief(patientId),
  ]);

  const [riskResult, baselinesResult, patternsResult, briefResult] = results;

  let risk: RiskScore | null = null;
  let riskFailed = false;
  if (riskResult.status === 'fulfilled') {
    const r = riskResult.value as ApiResponse<RiskScore>;
    if (r.success && r.data) risk = r.data;
    else riskFailed = true;
  } else {
    riskFailed = true;
  }

  let baselines: BaselineMetric[] = [];
  let baselinesFailed = false;
  if (baselinesResult.status === 'fulfilled') {
    const b = baselinesResult.value as ApiResponse<BaselineMetric[]>;
    if (b.success && b.data) baselines = b.data;
    else baselinesFailed = true;
  } else {
    baselinesFailed = true;
  }

  let patterns: PatternSignal[] = [];
  let patternsFailed = false;
  if (patternsResult.status === 'fulfilled') {
    const p = patternsResult.value as ApiResponse<PatternSignal[]>;
    if (p.success && p.data) patterns = p.data;
    else patternsFailed = true;
  } else {
    patternsFailed = true;
  }

  let brief: DailyBrief | null = null;
  let briefFailed = false;
  if (briefResult.status === 'fulfilled') {
    const br = briefResult.value as ApiResponse<DailyBrief>;
    if (br.success && br.data) brief = br.data;
    else briefFailed = true;
  } else {
    briefFailed = true;
  }

  return {
    risk,
    baselines,
    patterns,
    brief,
    isPartial: riskFailed || baselinesFailed || patternsFailed || briefFailed,
  };
}

// ---- Connectivity ----

// Check if online
export function isOnline(): boolean {
  return navigator.onLine;
}

// Listen for online/offline events
export function onConnectivityChange(callback: (online: boolean) => void): () => void {
  const handleOnline = () => callback(true);
  const handleOffline = () => callback(false);

  window.addEventListener('online', handleOnline);
  window.addEventListener('offline', handleOffline);

  return () => {
    window.removeEventListener('online', handleOnline);
    window.removeEventListener('offline', handleOffline);
  };
}