import Dexie, { Table } from 'dexie';
import type {
  GlucoseEntry,
  CornstarchEntry,
  MealEntry,
  SymptomEntry,
  SyncQueueItem,
  ActiveCourse,
  Entry,
} from '../types';

export interface StoredActiveCourse {
  id: string;
  type: 'cornstarch' | 'meal';
  startedAt: Date;
  endsAt: Date;
  grams?: number;
  mealType?: string;
  nextDose?: Date;
  fetchedAt: Date;
}

class PippenDatabase extends Dexie {
  glucoseEntries!: Table<GlucoseEntry, number>;
  cornstarchEntries!: Table<CornstarchEntry, number>;
  mealEntries!: Table<MealEntry, number>;
  symptomEntries!: Table<SymptomEntry, number>;
  syncQueue!: Table<SyncQueueItem, number>;
  activeCourse!: Table<StoredActiveCourse, string>;

  constructor() {
    super('PippenDB');

    this.version(1).stores({
      glucoseEntries: '++id, patientId, measuredAt, syncStatus, createdAt',
      cornstarchEntries: '++id, patientId, isBedtime, syncStatus, createdAt',
      mealEntries: '++id, patientId, mealType, syncStatus, createdAt',
      symptomEntries: '++id, patientId, symptomType, syncStatus, createdAt',
      syncQueue: '++id, entryId, entryType, attempts',
      activeCourse: 'id, fetchedAt',
    });
  }
}

export const db = new PippenDatabase();

// Helper to get the right table for an entry type
export function getEntryTable(entry: Entry): Table<Entry, number> {
  switch (entry.type) {
    case 'glucose':
      return db.glucoseEntries as unknown as Table<Entry, number>;
    case 'cornstarch':
      return db.cornstarchEntries as unknown as Table<Entry, number>;
    case 'meal':
      return db.mealEntries as unknown as Table<Entry, number>;
    case 'symptom':
      return db.symptomEntries as unknown as Table<Entry, number>;
  }
}

// Add entry to appropriate table
export async function addEntry(entry: Entry): Promise<number> {
  switch (entry.type) {
    case 'glucose':
      return db.glucoseEntries.add(entry as GlucoseEntry);
    case 'cornstarch':
      return db.cornstarchEntries.add(entry as CornstarchEntry);
    case 'meal':
      return db.mealEntries.add(entry as MealEntry);
    case 'symptom':
      return db.symptomEntries.add(entry as SymptomEntry);
  }
}

// Update entry sync status
export async function updateEntrySyncStatus(
  entryType: Entry['type'],
  entryId: number,
  status: Entry['syncStatus']
): Promise<void> {
  const table = getEntryTableByType(entryType);
  await table.update(entryId, {
    syncStatus: status,
    syncedAt: status === 'synced' ? new Date() : undefined,
  } as Partial<Entry>);
}

function getEntryTableByType(type: Entry['type']): Table<GlucoseEntry | CornstarchEntry | MealEntry | SymptomEntry, number> {
  switch (type) {
    case 'glucose':
      return db.glucoseEntries as Table<GlucoseEntry, number>;
    case 'cornstarch':
      return db.cornstarchEntries as Table<CornstarchEntry, number>;
    case 'meal':
      return db.mealEntries as Table<MealEntry, number>;
    case 'symptom':
      return db.symptomEntries as Table<SymptomEntry, number>;
  }
}

// Add item to sync queue
export async function addToSyncQueue(item: Omit<SyncQueueItem, 'id'>): Promise<number> {
  return db.syncQueue.add(item as SyncQueueItem);
}

// Get pending sync items
export async function getPendingSyncItems(): Promise<SyncQueueItem[]> {
  return db.syncQueue.where('attempts').below(5).toArray();
}

// Remove from sync queue
export async function removeFromSyncQueue(id: number): Promise<void> {
  await db.syncQueue.delete(id);
}

// Update sync queue item
export async function updateSyncQueueItem(
  id: number,
  updates: Partial<SyncQueueItem>
): Promise<void> {
  await db.syncQueue.update(id, updates);
}

// Store active course locally
export async function storeActiveCourse(course: ActiveCourse): Promise<void> {
  const stored: StoredActiveCourse = {
    ...course,
    fetchedAt: new Date(),
  };
  await db.activeCourse.put(stored);
}

// Get cached active course
export async function getCachedActiveCourse(): Promise<StoredActiveCourse | undefined> {
  const courses = await db.activeCourse.toArray();
  if (courses.length === 0) return undefined;
  // Return the most recent one
  return courses.sort((a, b) => b.fetchedAt.getTime() - a.fetchedAt.getTime())[0];
}

// Clear old cached courses
export async function clearOldCachedCourses(maxAgeMs: number = 24 * 60 * 60 * 1000): Promise<void> {
  const cutoff = new Date(Date.now() - maxAgeMs);
  await db.activeCourse.where('fetchedAt').below(cutoff).delete();
}

// Get all entries for a patient
export async function getEntriesByPatient(
  patientId: string
): Promise<{
  glucose: GlucoseEntry[];
  cornstarch: CornstarchEntry[];
  meals: MealEntry[];
  symptoms: SymptomEntry[];
}> {
  const [glucose, cornstarch, meals, symptoms] = await Promise.all([
    db.glucoseEntries.where('patientId').equals(patientId).toArray(),
    db.cornstarchEntries.where('patientId').equals(patientId).toArray(),
    db.mealEntries.where('patientId').equals(patientId).toArray(),
    db.symptomEntries.where('patientId').equals(patientId).toArray(),
  ]);

  return { glucose, cornstarch, meals, symptoms };
}

// Re-export queueEntrySync for convenience
export { queueEntrySync } from '../api/sync';

// Get pending entries count
export async function getPendingCount(): Promise<number> {
  const [glucose, cornstarch, meals, symptoms] = await Promise.all([
    db.glucoseEntries.where('syncStatus').equals('pending').count(),
    db.cornstarchEntries.where('syncStatus').equals('pending').count(),
    db.mealEntries.where('syncStatus').equals('pending').count(),
    db.symptomEntries.where('syncStatus').equals('pending').count(),
  ]);
  return glucose + cornstarch + meals + symptoms;
}
