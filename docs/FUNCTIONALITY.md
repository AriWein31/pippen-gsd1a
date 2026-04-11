# Pippen Functionality Guide

**Complete feature documentation for Pippen GSD1A Intelligence OS.**

---

## Table of Contents

1. [Patient Data Entry](#patient-data-entry)
2. [Coverage Tracking](#coverage-tracking)
3. [Night Safety System](#night-safety-system)
4. [Mobile App Features](#mobile-app-features)
5. [Intelligence Layer (Week 5+)](#intelligence-layer)
6. [Research Watch (Future)](#research-watch)

---

## Patient Data Entry

### Glucose Readings
Log blood glucose measurements with context.

**Fields:**
- `value_mg_dl` (20-600 mg/dL) — Numeric input with validation
- `context` — Fasting, post-meal, bedtime
- `timestamp` — Defaults to now, editable

**Behavior:**
- Saved locally immediately (IndexedDB)
- Synced to backend when online
- Does NOT create coverage course (glucose doesn't provide coverage)
- Can resolve active alarm if new dose follows

### Cornstarch Doses
Primary GSD1A management tool — raw cornstarch provides 5.15 hours of glucose coverage.

**Fields:**
- `grams` (1-100g) — Amount consumed
- `brand` — Optional (e.g., "Argo", "Great Plains")
- `is_bedtime_dose` — Boolean flag
- `timestamp` — When taken

**Behavior:**
- Creates **coverage course** (5.15h duration)
- Bedtime doses marked for overnight expectations
- Automatically creates **night alarm** tracking
- Resolves any previous active alarms
- Chains to previous course if overlap

**Medical Context:**
Cornstarch is the cornerstone of GSD1A management. Uncooked cornstarch breaks down slowly, providing sustained glucose release. Bedtime doses are critical — missing overnight coverage risks severe hypoglycemia.

### Meals
Log meals, with special handling for cornstarch-containing meals.

**Fields:**
- `meal_type` — Breakfast, lunch, dinner, snack
- `description` — Free text (e.g., "Chicken, rice, vegetables")
- `contains_cornstarch` — Boolean
- `timestamp` — When eaten

**Behavior:**
- If `contains_cornstarch=false`: Creates 2-hour coverage course
- If `contains_cornstarch=true`: No course created (use cornstarch endpoint instead)
- Can resolve active alarms

**Rationale:**
Meals without cornstarch provide ~2h of coverage from carbohydrates. Meals with cornstarch should be logged separately to track exact cornstarch grams.

### Symptoms
Track GSD1A-related symptoms for pattern detection.

**Fields:**
- `symptom_type` — Hypoglycemia, hyperglycemia, fatigue, dizziness, headache, nausea, other
- `severity` — 1-10 scale
- `notes` — Optional context
- `timestamp` — When occurred

**Behavior:**
- Does NOT create coverage course
- Used for intelligence layer pattern detection
- Severity helps prioritize alerts

**Medical Context:**
Hypoglycemia symptoms (shakiness, sweating, confusion) indicate urgent glucose need. Tracking these helps identify timing patterns and coverage gaps.

---

## Coverage Tracking

### Course Model
The core abstraction for GSD1A timing management.

**A coverage course represents:**
- A period of glucose protection
- Started by a cornstarch dose or qualifying meal
- Expected end time based on duration
- Current status in state machine

**Duration Constants:**
```python
CORNSTARCH_DURATION_MINUTES = 309  # 5.15 hours
MEAL_DURATION_MINUTES = 120        # 2 hours
```

### State Machine
```
active → warning_sent → expired → alarmed → escalated → resolved
   ↓           ↓           ↓          ↓           ↓
superseded  closed      closed     closed      closed
```

**States:**
- `active` — Coverage in progress, no alert needed
- `warning_sent` — 15 min warning fired (coverage ending soon)
- `expired` — Expected end time reached
- `alarmed` — Patient hasn't responded, alarm fired
- `escalated` — Caregivers notified after delay
- `resolved` — Patient logged qualifying event
- `superseded` — New course started before expiry
- `closed` — Manually closed or resolved

### Chain Linking
Courses automatically link to previous active courses.

**Benefits:**
- Track coverage continuity
- Detect gaps (dangerous)
- Detect overlaps (inefficient but safe)
- Calculate timing patterns over time

**Gap Detection:**
If new course starts after previous expected end:
```
gap_minutes = new_course.started_at - previous_course.expected_end_at
```

Gaps > 15 minutes flagged for clinical review.

**Overlap Detection:**
If new course starts before previous ends:
```
overlap_minutes = previous_course.expected_end_at - new_course.started_at
```

Overlaps noted but not alarmed (patient is covered).

### Active Course Display
Mobile app shows current coverage status.

**Visual Elements:**
- Coverage type icon (🌙 for bedtime cornstarch, ☀️ for meal)
- Time remaining (countdown)
- Progress bar (percentage complete)
- Next dose time
- Color coding: blue (safe), amber (<25%), red (<10%)

---

## Night Safety System

### Alarm Daemon
Background process monitoring all patients.

**Specifications:**
- Tick interval: 60 seconds
- Deterministic logic (no ML)
- Stateless (reads from database each tick)
- Idempotent (safe to restart)

**Algorithm:**
```python
for each active alarm:
    if status == active and now >= warning_time:
        transition_to_warning()
    
    if status == warning_sent and now >= expiry_time:
        transition_to_expired()
    
    if status == expired and now >= alarm_time:
        transition_to_alarmed()
    
    if status == alarmed and now >= escalation_time:
        transition_to_escalated()
```

### Timing Constants
```python
WARNING_LEAD_MINUTES = 15      # Warning before expiry
ALARM_DELAY_MINUTES = 0        # Alarm at expiry
ESCALATION_DELAY_MINUTES = 5   # Escalate 5 min after alarm
```

### Notification Channels
**Primary:**
- Telegram bot (instant, reliable)
- Push notifications (APNs/FCM)

**Future:**
- SMS (fallback for critical escalation)
- Phone call (final escalation)

### Escalation Chain
**Stage 1 - Warning:**
- Recipients: All caregivers with `notify_warning=true`
- Message: "Coverage ending in 15 minutes"
- Channels: Push + Telegram

**Stage 2 - Expired:**
- Internal state change
- No external notification (patient may still respond)

**Stage 3 - Alarm:**
- Recipients: All caregivers with `notify_alarm=true`
- Message: "Coverage expired. Immediate action required."
- Channels: Push + Telegram
- Sound: Alarm tone (if app in foreground)

**Stage 4 - Escalation:**
- Recipients: All caregivers with `notify_escalation=true`
- Message: "ALERT: Patient unresponsive. Check immediately."
- Channels: Push + Telegram
- Escalation order respected

### Resolution
Alarms resolve automatically when patient logs:
- Cornstarch dose
- Meal (if no cornstarch)
- Explicit alarm acknowledgement

**Resolution Types:**
- `patient_logged` — Normal resolution
- `caregiver_checked` — Manual verification
- `false_alarm` — Marked as incorrect
- `timeout` — Auto-close after extended period

### Audit Trail
Every notification logged:
```
notification_log:
  - id, patient_id, notification_type
  - channel, recipient_id, recipient_address
  - message_text, status (pending/sent/delivered/failed)
  - sent_at, delivered_at
```

---

## Mobile App Features

### Architecture
**Offline-First PWA:**
- All data saved locally first (Dexie.js/IndexedDB)
- API sync happens in background
- No blocking network calls
- Works in airplane mode

**Sync Strategy:**
```
User action → Local save (immediate) → Queue for sync → Background API call
```

### 5-Tab Navigation

#### 1. Now (Intelligence Home)
- Active coverage card (countdown + progress)
- Quick log buttons
- Recent activity feed
- Today's summary

#### 2. Trends
*Phase 2:*
- Glucose charts (24h, 7d, 30d)
- Coverage gaps timeline
- Pattern highlights

#### 3. Watch
*Phase 3:*
- Research updates
- Clinical trial alerts
- Community signals

#### 4. Actions
- Log glucose
- Log cornstarch
- Log meal
- Log symptom

#### 5. Profile
- Sync status
- Notification permissions
- Settings
- About

### Entry Forms
All forms follow offline-first pattern:

**Validation:**
- Client-side before save
- Server-side on sync
- Visual error messages
- Duplicate submission prevention

**Sync Status Indicators:**
- ⏳ Pending
- 🔄 Syncing
- ✅ Synced
- ❌ Failed (with retry)

### Error Handling
**Global Error Boundary:**
- Catches React crashes
- Shows friendly fallback UI
- Preserves local data
- Reload option

**Network Errors:**
- Silent retry (exponential backoff)
- Visual indicator in Profile
- Manual sync button

---

## Intelligence Layer (Week 5+)

*Coming in Phase 2.*

### Baseline Computation
Compute patient norms from history:
- Overnight average glucose
- Overnight glucose variability (CV)
- Low glucose frequency (< 70 mg/dL)
- Bedtime-to-next-event interval

### Pattern Detection
Identify concerning patterns:
- **Late bedtime dosing** — 2+ nights past threshold
- **Overnight low clusters** — 2+ lows within 2 hours
- **Recent instability** — CV increase > 30% vs prior week

### Risk Scoring
```
Risk = f(pattern_severity, frequency, recency, baseline_deviation)
```

**Outputs:**
- Risk level (low/medium/high/critical)
- Confidence score
- Supporting events
- Recommended action

### Daily Brief
Structured morning summary:

```json
{
  "what_changed": ["3 overnight lows vs baseline of 1"],
  "what_matters": ["Coverage gap detected 2:30-2:45 AM"],
  "recommended_attention": ["Consider earlier bedtime dose"],
  "confidence": 0.81,
  "supporting_events": ["evt-003", "evt-008", "evt-012"]
}
```

### Confidence Scoring
Deterministic formula based on:
- Sample size (more data = higher confidence)
- Pattern strength (deviation from baseline)
- Recency (recent patterns weighted higher)

---

## Research Watch (Future)

*Coming in Phase 3.*

### Monitored Sources
- PubMed (GSD1A publications)
- ClinicalTrials.gov
- Patient advocacy organizations
- Pharmaceutical sponsors

### Claim Extraction
- LLM-based claim decomposition
- Trust tier ranking
- Patient relevance scoring
- Narrative change detection

### Watch Screen
- Daily research briefing
- Tracked trials list
- New publication alerts
- Change summaries

---

## Safety Considerations

### What Pippen Does NOT Do
- ❌ Replace medical care
- ❌ Provide dosing recommendations
- ❌ Diagnose conditions
- ❌ Guarantee safety

### What Pippen DOES Do
- ✅ Track data patient provides
- ✅ Alert on coverage expiration
- ✅ Escalate to configured contacts
- ✅ Surface patterns for review
- ✅ Maintain audit trail

### Emergency Protocol
If alarm escalates:
1. Caregivers notified via all channels
2. If no response: continue escalation chain
3. Final escalation: emergency services (if configured)
4. All actions logged for review

**Important:** Pippen is a tool. Clinical judgment always prevails.

---

*Last updated: 2026-04-11 — Week 4 Complete*
