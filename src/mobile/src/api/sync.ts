import { isOnline, logGlucose, logCornstarch, logMeal, logSymptom } from './client';
import {
  db,
  addToSyncQueue,
  getPendingSyncItems,
  removeFromSyncQueue,
  updateSyncQueueItem,
  updateEntrySyncStatus,
  type StoredActiveCourse,
} from '../db/database';
import type { Entry, SyncQueueItem, GlucoseEntry, CornstarchEntry, MealEntry, SymptomEntry } from '../types';

const PATIENT_ID = import.meta.env.VITE_PATIENT_ID || 'default-patient';

// Sync a single entry to the API
async function syncEntry(item: SyncQueueItem): Promise<boolean> {
  const entry = await getEntryFromDb(item.entryType, item.entryId);
  if (!entry) {
    // Entry was deleted, remove from queue
    await removeFromSyncQueue(item.id!);
    return true;
  }

  let result;
  switch (item.entryType) {
    case 'glucose':
      result = await logGlucose(PATIENT_ID, entry as Omit<GlucoseEntry, 'id' | 'patientId' | 'createdAt' | 'syncStatus'>);
      break;
    case 'cornstarch':
      result = await logCornstarch(PATIENT_ID, entry as Omit<CornstarchEntry, 'id' | 'patientId' | 'createdAt' | 'syncStatus'>);
      break;
    case 'meal':
      result = await logMeal(PATIENT_ID, entry as Omit<MealEntry, 'id' | 'patientId' | 'createdAt' | 'syncStatus'>);
      break;
    case 'symptom':
      result = await logSymptom(PATIENT_ID, entry as Omit<SymptomEntry, 'id' | 'patientId' | 'createdAt' | 'syncStatus'>);
      break;
  }

  return result?.success ?? false;
}

// Get entry from the appropriate table
async function getEntryFromDb(type: Entry['type'], id: number): Promise<Entry | undefined> {
  switch (type) {
    case 'glucose':
      return db.glucoseEntries.get(id);
    case 'cornstarch':
      return db.cornstarchEntries.get(id);
    case 'meal':
      return db.mealEntries.get(id);
    case 'symptom':
      return db.symptomEntries.get(id);
  }
}

// Process sync queue
export async function processSyncQueue(): Promise<{ synced: number; failed: number }> {
  if (!isOnline()) {
    return { synced: 0, failed: 0 };
  }

  const pendingItems = await getPendingSyncItems();
  let synced = 0;
  let failed = 0;

  for (const item of pendingItems) {
    try {
      // Mark entry as syncing
      await updateEntrySyncStatus(item.entryType, item.entryId, 'syncing');

      const success = await syncEntry(item);

      if (success) {
        await updateEntrySyncStatus(item.entryType, item.entryId, 'synced');
        await removeFromSyncQueue(item.id!);
        synced++;
      } else {
        throw new Error('Sync returned failure');
      }
    } catch (error) {
      // Mark as failed, increment attempts
      await updateEntrySyncStatus(item.entryType, item.entryId, 'failed');
      await updateSyncQueueItem(item.id!, {
        attempts: item.attempts + 1,
        lastAttempt: new Date(),
        error: error instanceof Error ? error.message : 'Unknown error',
      });
      failed++;
    }
  }

  return { synced, failed };
}

// Queue an entry for sync
export async function queueEntrySync(entry: Entry, entryId: number): Promise<void> {
  await addToSyncQueue({
    entryId,
    entryType: entry.type,
    payload: entry as unknown as Record<string, unknown>,
    attempts: 0,
  });
}

// Background sync worker
let syncInterval: ReturnType<typeof setInterval> | null = null;

export function startBackgroundSync(intervalMs: number = 30000): void {
  if (syncInterval) return;

  // Initial sync
  processSyncQueue();

  // Periodic sync
  syncInterval = setInterval(() => {
    if (isOnline()) {
      processSyncQueue();
    }
  }, intervalMs);

  // Also sync when coming online
  window.addEventListener('online', () => {
    processSyncQueue();
  });
}

export function stopBackgroundSync(): void {
  if (syncInterval) {
    clearInterval(syncInterval);
    syncInterval = null;
  }
}

// Get active course with local cache fallback
export async function fetchActiveCourseWithCache(): Promise<StoredActiveCourse | null> {
  // Try online fetch first
  if (isOnline()) {
    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_BASE || 'http://localhost:8000/api'}/patients/${PATIENT_ID}/active-course`
      );
      if (response.ok) {
        const course = await response.json();
        if (course) {
          await db.activeCourse.put({
            ...course,
            fetchedAt: new Date(),
          } as StoredActiveCourse);
          return course as StoredActiveCourse;
        }
      }
    } catch {
      // Fall through to cache
    }
  }

  // Fall back to cached
  const cached = await db.activeCourse.toArray();
  if (cached.length > 0) {
    return cached.sort((a, b) => b.fetchedAt.getTime() - a.fetchedAt.getTime())[0];
  }

  return null;
}
