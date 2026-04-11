# Mobile Lead — Role Specification

**Project:** Pippen (GSD1A Intelligence OS)  
**Start Date:** April 26, 2026  
**Duration:** Phase 1 Weeks 3-4, then ongoing  
**Model:** MiniMax 2.7

---

## The Role

Lead mobile development for a life-safety medical application. Build the patient-facing interface that must work flawlessly — even at 2am, even offline, even under stress.

This is not a typical consumer app. It's an intelligence operating system for a rare disease. The UI must feel premium, calm, and medically trustworthy.

---

## Responsibilities

### Week 3-4 (Immediate)
- React Native / PWA project setup
- Bottom navigation (5 tabs)
- Entry forms (glucose, cornstarch, meal, symptom)
- Offline-first SQLite storage
- Sync queue with conflict resolution

### Phase 2+ (Ongoing)
- Trends screen with charts
- Research Watch UI
- Recommendations screen
- Profile & settings
- Push notifications
- Deep linking
- Accessibility (WCAG 2.1 AA)

---

## Technical Requirements

### Must Have
- **React Native** (0.72+) OR **Progressive Web App** (React/Vue + service workers)
- **TypeScript** — all code typed
- **Offline-first architecture** — app works without network
- **SQLite or IndexedDB** — local data persistence
- **iOS & Android** — both platforms
- **Mobile UI/UX** — understands touch, gestures, thumb zones

### Nice to Have
- Expo experience
- Fastlane for CI/CD
- Push notification implementation (APNs/FCM)
- Healthcare app experience
- Accessibility expertise

### Design System
You'll implement from our DESIGN.md:
- Light theme: #F6F7F9 canvas, #FFFFFF surfaces
- Intelligence blue accent: #315BFF
- 5-tab bottom navigation
- Card-based UI (16-20px radius)
- Premium, calm, medically trustworthy aesthetic

---

## The Test Task

**Scenario:** Build a minimal offline-first glucose logging app.

**Time Budget:** 2-3 hours  
**Deliverable:** Working mobile app (React Native or PWA)

### Requirements

#### Core Functionality
1. **One screen:** "Log Glucose"
   - Numeric input (mg/dL)
   - Timestamp picker (default: now)
   - "Save" button

2. **Offline Storage**
   - Save readings locally (SQLite or localStorage)
   - Show list of saved readings
   - Persist across app restarts

3. **Sync When Online**
   - Mock API endpoint (don't need real backend)
   - Queue readings when offline
   - Auto-sync when connection restored
   - Show sync status

#### UI Requirements
- Match our design system (light theme, blue accents, cards)
- Bottom navigation placeholder (2 tabs: "Log" and "History")
- Works on iPhone 14 Pro size (390×844)
- Touch-friendly (44px min touch targets)

#### Technical Requirements
- TypeScript
- Offline-first (no "loading" spinners for local data)
- Error handling (invalid input, storage full, etc.)

### What We're Looking For

| Criterion | Weight | What We Want |
|-----------|--------|--------------|
| **Offline-First** | 30% | App works without network. No "please connect" blocks. |
| **Code Quality** | 25% | Clean, typed, documented. Easy to review. |
| **UI Implementation** | 20% | Matches design system. Feels premium. |
| **Error Handling** | 15% | Graceful failures. User-friendly messages. |
| **Sync Logic** | 10% | Queue, retry, conflict resolution. |

### Submission

1. GitHub repository with code
2. README with setup instructions
3. Screenshots or screen recording
4. Brief writeup of your approach

---

## Evaluation Process

1. **Task Assignment** — We send you the test
2. **Development** — You build (2-3 hours)
3. **Submission** — GitHub repo + README
4. **Review** — Ezra (GPT-5.4 Codex) reviews code
5. **Interview** — Discussion of your approach (30 min)
6. **Decision** — Offer or pass

---

## Why This Matters

GSD1A patients log data at all hours — often in stressful situations. The app must:
- Work immediately (no loading)
- Work offline (hospitals have poor signal)
- Be crystal clear (cognitive load is already high)
- Feel trustworthy (this is medical data)

Your code will be part of a system that helps people manage a life-threatening condition. Build it like lives depend on it — because they do.

---

## Questions?

Ask Ezra (Project Lead) during the interview.
