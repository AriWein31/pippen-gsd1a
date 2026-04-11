import { useState, useEffect, useCallback } from 'react';
import { fetchActiveCourseWithCache } from '../api/sync';
import type { StoredActiveCourse } from '../db/database';

interface UseActiveCourseResult {
  course: StoredActiveCourse | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function useActiveCourse(
  _patientId: string,
  refreshIntervalMs: number = 60000
): UseActiveCourseResult {
  const [course, setCourse] = useState<StoredActiveCourse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchCourse = useCallback(async (): Promise<void> => {
    try {
      const result = await fetchActiveCourseWithCache();
      setCourse(result);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch course');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchCourse();

    const intervalId = setInterval(() => {
      void fetchCourse();
    }, refreshIntervalMs);

    return () => clearInterval(intervalId);
  }, [fetchCourse, refreshIntervalMs]);

  return { course, loading, error, refetch: fetchCourse };
}
