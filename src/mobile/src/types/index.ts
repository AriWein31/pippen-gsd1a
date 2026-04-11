// Glucose reading context
export type GlucoseContext = 'fasting' | 'post-meal' | 'bedtime';

// Meal types
export type MealType = 'breakfast' | 'lunch' | 'dinner' | 'snack';

// Symptom types
export type SymptomType =
  | 'hypoglycemia'
  | 'hyperglycemia'
  | 'fatigue'
  | 'dizziness'
  | 'headache'
  | 'nausea'
  | 'other';

// Sync status for offline-first
export type SyncStatus = 'pending' | 'syncing' | 'synced' | 'failed';

// Base entry interface
export interface BaseEntry {
  id?: number;
  patientId: string;
  createdAt: Date;
  syncStatus: SyncStatus;
  syncedAt?: Date;
}

// Glucose reading entry
export interface GlucoseEntry extends BaseEntry {
  type: 'glucose';
  value: number; // mg/dL
  context: GlucoseContext;
  measuredAt: Date;
}

// Cornstarch entry
export interface CornstarchEntry extends BaseEntry {
  type: 'cornstarch';
  grams: number;
  brand?: string;
  isBedtime: boolean;
}

// Meal entry
export interface MealEntry extends BaseEntry {
  type: 'meal';
  mealType: MealType;
  description: string;
  containsCornstarch: boolean;
}

// Symptom entry
export interface SymptomEntry extends BaseEntry {
  type: 'symptom';
  symptomType: SymptomType;
  severity: number; // 1-10
  notes?: string;
}

// Union type for all entries
export type Entry = GlucoseEntry | CornstarchEntry | MealEntry | SymptomEntry;

// Active coverage course from API
export interface ActiveCourse {
  id: string;
  type: 'cornstarch' | 'meal';
  startedAt: Date;
  endsAt: Date;
  grams?: number; // for cornstarch
  mealType?: MealType; // for meal
  nextDose?: Date;
}

// Sync queue item
export interface SyncQueueItem {
  id?: number;
  entryId: number;
  entryType: Entry['type'];
  payload: Record<string, unknown>;
  attempts: number;
  lastAttempt?: Date;
  error?: string;
}

// Navigation tab
export interface Tab {
  id: string;
  label: string;
  icon: string;
  activeIcon: string;
  path: string;
}

// API response types
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
}

// Form validation
export interface ValidationError {
  field: string;
  message: string;
}
