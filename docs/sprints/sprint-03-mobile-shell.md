# Sprint 03: Mobile Shell (Weeks 3-4)

**Sprint Duration:** Weeks 3-4 (April 26 - May 9, 2026)  
**Goal:** Mobile app shell with offline-first entry forms  
**Lead:** Candidate 3 (Mobile Lead)  
**Status:** 🟢 Ready to Start

---

## Week 3: Mobile App Shell (April 26 - May 2)

### Assigned To: Candidate 3 (Mobile Lead)

### Context

Backend APIs are ready:
- `POST /patients/{id}/glucose` — Log glucose reading
- `POST /patients/{id}/cornstarch` — Log cornstarch (creates 5.15h course)
- `POST /patients/{id}/meals` — Log meal (creates 2h course if not cornstarch)
- `POST /patients/{id}/symptoms` — Log symptom
- `GET /patients/{id}/active-course` — Get current coverage

Design system: `/docs/design-system.md`

### Week 3 Tasks

#### Task 3.1: Project Setup (8h)
**Deliverable:** Working mobile project scaffold

Choose ONE:
- **Option A:** React Native 0.72+ with TypeScript
- **Option B:** PWA with React 18+ + Vite + TypeScript

Setup:
- [ ] Project initialization
- [ ] TypeScript configuration
- [ ] Development environment (Metro for RN, or Vite dev server)
- [ ] Build scripts for iOS/Android (RN) or production build (PWA)
- [ ] `.env.example` for API endpoints

**Reference:** Your test task repo structure (pippen-glucose-app)

#### Task 3.2: Bottom Navigation (4h)
**Deliverable:** 5-tab navigation working

Implement:
- [ ] Now (Intelligence Home)
- [ ] Trends (Patterns)
- [ ] Watch (Research)
- [ ] Actions (Recommendations)
- [ ] Profile (Settings)

Specs:
- Fixed bottom position
- Active tab: filled icon + label
- Inactive tab: outline icon
- Intelligence blue (#315BFF) for active

#### Task 3.3: Offline-First Storage (10h)
**Deliverable:** Local database with sync queue

Implement:
- [ ] Local storage (SQLite for RN, or IndexedDB for PWA)
- [ ] Tables:
  - `readings` — Glucose readings (pending + synced)
  - `courses` — Coverage courses (from backend)
  - `sync_queue` — Pending API calls
- [ ] Sync status tracking per record
- [ ] Conflict resolution strategy

Key requirement: **App works without network. No blocking loaders for local data.**

#### Task 3.4: Entry Forms (12h)
**Deliverable:** 4 entry forms, offline-first

Forms:

**1. Log Glucose**
- Numeric input (mg/dL)
- Time picker (default: now)
- Context tags (fasting, post-meal, bedtime)
- Save → local DB immediately → sync in background

**2. Log Cornstarch**
- Grams input
- Brand/type
- Bedtime toggle (affects expectations)
- Save → local DB + API call (creates course)

**3. Log Meal**
- Meal type (breakfast, lunch, dinner, snack)
- Description
- Contains cornstarch toggle
- Save → local DB + API call

**4. Log Symptom**
- Symptom type (dropdown)
- Severity (1-10)
- Notes
- Save → local DB + API call

**Offline behavior:**
- Save to local DB immediately
- Show "Pending sync" status
- Auto-sync when online
- Manual retry button

#### Task 3.5: Active Course Display (6h)
**Deliverable:** Show current coverage on "Now" screen

Implement:
- [ ] Fetch active course from backend
- [ ] Display:
  - Time remaining until coverage expires
  - Progress bar (visual)
  - Next dose reminder
- [ ] Update in real-time (or every minute)

Example:
```
┌─────────────────────────────┐
│  Current Coverage           │
│                             │
│  🌙 Bedtime Cornstarch      │
│  ⏱️ 3h 42m remaining        │
│  ████████████░░░░░ 72%      │
│                             │
│  Next dose: ~2:09 AM        │
└─────────────────────────────┘
```

### Definition of Done (Week 3)

- [ ] App installs and runs on device/simulator
- [ ] All 5 tabs navigateable
- [ ] 4 entry forms work offline
- [ ] Data syncs when online
- [ ] Active course displays with countdown
- [ ] UI matches design system

---

## Week 4: Polish & Night Alarm Prep (May 3-9)

### Task 4.1: Error Handling & Edge Cases (6h)

- [ ] Network error handling
- [ ] Invalid input validation
- [ ] Storage full handling
- [ ] Duplicate submission prevention

### Task 4.2: Push Notifications Setup (8h)

- [ ] APNs (iOS) configuration
- [ ] FCM (Android) configuration
- [ ] Request notification permissions
- [ ] Test push delivery

### Task 4.3: PWA/App Store Prep (6h)

- [ ] App icons (all sizes)
- [ ] Splash screen
- [ ] PWA manifest (if PWA)
- [ ] App Store / Play Store metadata

### Definition of Done (Week 4)

- [ ] Graceful error handling
- [ ] Push notifications working
- [ ] App store ready (or PWA installable)
- [ ] Week 4 safety audit passed (Ezra)

---

## API Integration

### Endpoints to Use

```typescript
const API = {
  // Entries
  logGlucose: (patientId, data) => POST `/patients/${patientId}/glucose`,
  logCornstarch: (patientId, data) => POST `/patients/${patientId}/cornstarch`,
  logMeal: (patientId, data) => POST `/patients/${patientId}/meals`,
  logSymptom: (patientId, data) => POST `/patients/${patientId}/symptoms`,
  
  // Coverage
  getActiveCourse: (patientId) => GET `/patients/${patientId}/active-course`,
  getCourses: (patientId, start, end) => GET `/patients/${patientId}/courses`,
}
```

### Offline-First Pattern

```typescript
// Save entry (works offline)
async function saveEntry(entry) {
  // 1. Save to local DB immediately
  await localDb.entries.add({
    ...entry,
    status: 'pending',
    createdAt: new Date(),
  });
  
  // 2. Try to sync (if online)
  if (navigator.onLine) {
    await syncEntry(entry);
  }
}

// Sync with backend
async function syncEntry(entry) {
  try {
    const result = await api.logGlucose(entry);
    await localDb.entries.update(entry.id, {
      status: 'synced',
      syncedAt: new Date(),
    });
  } catch (error) {
    // Keep as pending, will retry
    console.error('Sync failed:', error);
  }
}
```

---

## Design System Reference

See: `/docs/design-system.md`

Key specs:
- Background: #F6F7F9
- Cards: #FFFFFF, 16px radius
- Primary: #315BFF
- Typography: Inter/Inter Tight
- Touch targets: 44px minimum

---

## Quality Standards

- TypeScript strict mode
- All functions typed
- Error handling for all async operations
- Loading states (non-blocking)
- Accessibility labels

---

## Git Workflow

1. `git checkout -b feature/week3-mobile-shell`
2. Commit regularly with clear messages
3. `git push origin feature/week3-mobile-shell`
4. Ezra reviews and merges

---

## Success Criteria

By end of Week 4:
- Patient can log all 4 entry types
- App works offline
- Data syncs when online
- Active course visible with countdown
- Push notifications configured
- App store ready

---

**Questions?** Ask Ezra.
