import type {
  GlucoseEntry,
  CornstarchEntry,
  MealEntry,
  SymptomEntry,
  ActiveCourse,
  ApiResponse,
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
