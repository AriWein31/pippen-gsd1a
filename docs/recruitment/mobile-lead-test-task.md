# Mobile Lead — Technical Test Task

**Project:** Pippen (GSD1A Intelligence OS)  
**Role:** Mobile Lead  
**Time Budget:** 2-3 hours  
**Due:** 48 hours from receiving this task

---

## The Challenge

Build a minimal offline-first glucose logging app. This is a simplified version of Pippen's core entry flow.

---

## Requirements

### 1. Screen: Log Glucose

Create a single screen with:

```
┌─────────────────────────────┐
│  9:41               🔋      │  ← Status bar
├─────────────────────────────┤
│                             │
│   Log Glucose               │  ← Title (20px, weight 600)
│                             │
│   ┌─────────────────────┐   │
│   │ 120                 │   │  ← Input (mg/dL)
│   └─────────────────────┘   │
│                             │
│   When?                     │
│   ┌─────────────────────┐   │
│   │ Now ▼               │   │  ← Time picker
│   └─────────────────────┘   │
│                             │
│   ┌─────────────────────┐   │
│   │      Save           │   │  ← Primary button
│   └─────────────────────┘   │
│                             │
│   Last saved: 2 min ago     │  ← Status text
│                             │
├─────────────────────────────┤
│  [📝 Log]    [📋 History]   │  ← Bottom nav (2 tabs)
└─────────────────────────────┘
```

**Specs:**
- Background: #F6F7F9
- Card/Input background: #FFFFFF
- Primary button: #315BFF with white text
- Border radius: 16px
- Input height: 56px
- Button height: 52px

### 2. Screen: History

Show list of saved readings:

```
┌─────────────────────────────┐
│  History              🔄    │  ← Sync button
├─────────────────────────────┤
│                             │
│   Today                     │
│   ┌─────────────────────┐   │
│   │ 120 mg/dL    9:30 AM│   │
│   │ Synced ✓            │   │
│   └─────────────────────┘   │
│                             │
│   ┌─────────────────────┐   │
│   │ 118 mg/dL    6:15 AM│   │
│   │ Pending sync...     │   │
│   └─────────────────────┘   │
│                             │
│   Yesterday                 │
│   ┌─────────────────────┐   │
│   │ 125 mg/dL    10:00PM│   │
│   │ Synced ✓            │   │
│   └─────────────────────┘   │
│                             │
├─────────────────────────────┤
│  [📝 Log]    [📋 History]   │
└─────────────────────────────┘
```

### 3. Offline-First Storage

- Save readings locally immediately (no network wait)
- Use SQLite (React Native) or IndexedDB (PWA)
- Show list from local storage
- Persist across app restarts

### 4. Sync When Online

Mock API (don't need real backend):

```typescript
// Mock API
const mockApi = {
  async saveGlucose(value: number, timestamp: Date) {
    // Simulate network delay
    await delay(500);
    
    // Simulate occasional failures (10%)
    if (Math.random() < 0.1) {
      throw new Error('Network error');
    }
    
    return { id: generateId(), synced: true };
  }
};
```

Sync behavior:
- When online: try to sync immediately
- On failure: queue for retry
- Show "Pending sync" status
- Auto-retry when connection restored
- Manual retry button (🔄)

### 5. Technical Stack

**Choose ONE:**

**Option A: React Native**
- React Native 0.72+
- TypeScript
- @react-native-async-storage/async-storage OR react-native-sqlite-storage
- React Navigation (bottom tabs)

**Option B: PWA**
- React 18+ or Vue 3
- TypeScript
- IndexedDB (via dexie.js or idb)
- Workbox (for service worker)
- React Router or Vue Router

---

## Deliverables

1. **GitHub repository** with:
   - Source code
   - README.md with setup instructions
   - `package.json` with dependencies

2. **README must include:**
   - How to run the app
   - Your approach (2-3 paragraphs)
   - Trade-offs you made
   - What you'd improve with more time

3. **Screenshots or screen recording** showing:
   - Logging glucose
   - Viewing history
   - Offline behavior
   - Sync behavior

---

## Evaluation Criteria

| Criterion | Weight | What We Look For |
|-----------|--------|------------------|
| **Offline-First** | 30% | App works without network. No blocking loaders. |
| **Code Quality** | 25% | Clean, typed, documented. Readable. |
| **UI Implementation** | 20% | Matches specs. Premium feel. |
| **Error Handling** | 15% | Graceful failures. Clear messages. |
| **Sync Logic** | 10% | Queue, retry, state management. |

---

## Time Budget

2-3 hours. We respect your time.

If you can't finish everything:
- Prioritize offline storage + basic UI
- Leave sync logic as comments explaining approach
- Document what's incomplete

---

## Submission

1. Push to your GitHub
2. Email/DM repository link
3. Include screenshots/recording

**Deadline:** 48 hours from now

---

## Questions?

Ask before you start. Better to clarify than guess.

---

Good luck. Build something you'd trust at 2am.
