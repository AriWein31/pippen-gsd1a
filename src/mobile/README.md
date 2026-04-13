# Pippen Mobile App

Patient-facing PWA for glycogen storage disease (GSD) management.

## Features

- 📊 **Active Course Display** - Real-time coverage countdown
- 📝 **Offline-First Entry Forms** - Log glucose, cornstarch, meals, and symptoms without internet
- 🔄 **Background Sync** - Automatically syncs when back online
- 📱 **PWA Installable** - Works as a native app on iOS/Android
- 🎨 **Design System** - Intelligence Blue (#315BFF) theme

## Tech Stack

- **React 18** + **TypeScript** (strict mode)
- **Vite** - Build tooling
- **Dexie.js** - IndexedDB wrapper for offline storage
- **React Router** - Navigation
- **Tailwind CSS** - Styling
- **PWA** - Service worker for offline support

## Project Structure

```
src/
├── api/           # API client and sync logic
│   ├── client.ts  # REST API calls
│   └── sync.ts    # Background sync worker
├── components/    # Reusable UI components
│   ├── forms/     # Entry form components
│   └── ...
├── db/            # Dexie database
│   └── database.ts
├── hooks/         # Custom React hooks
├── pages/         # Route pages
├── types/         # TypeScript interfaces
└── utils/         # Helper functions
```

## Setup

### Prerequisites

- Node.js 18+
- npm or yarn

### Installation

```bash
cd src/mobile
npm install
```

### Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Edit `.env`:
- `VITE_API_BASE` - Backend API URL
- `VITE_PATIENT_ID` - Patient identifier **(required — no fallback; must be set for intelligence and sync to function)**

### Development

```bash
npm run dev
```

Open http://localhost:5173 in your browser.

### Build

```bash
npm run build
```

Production build outputs to `dist/`.

### Preview Production Build

```bash
npm run preview
```

## Offline-First Architecture

All entry forms work offline:

1. **Immediate Local Save** - Data saved to IndexedDB via Dexie.js
2. **Background Sync** - Queued for API sync when online
3. **Sync Status** - Visual indicator shows pending/synced state

### Database Tables

- `glucoseEntries` - Glucose readings
- `cornstarchEntries` - Cornstarch logs
- `mealEntries` - Meal records
- `symptomEntries` - Symptom logs
- `syncQueue` - Pending API calls
- `activeCourse` - Cached coverage data

## Navigation

5-tab bottom navigation:

1. **Now** - Active course + quick log
2. **Trends** - Glucose patterns (coming soon)
3. **Watch** - Research/education (coming soon)
4. **Actions** - Entry forms
5. **Profile** - Settings + sync status

## API Integration

The app integrates with these backend endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/patients/{id}/glucose` | POST | Log glucose |
| `/patients/{id}/cornstarch` | POST | Log cornstarch |
| `/patients/{id}/meals` | POST | Log meal |
| `/patients/{id}/symptoms` | POST | Log symptom |
| `/patients/{id}/active-course` | GET | Get active coverage |
| `/patients/{id}/risk` | GET | Overnight risk score |
| `/patients/{id}/baselines` | GET | Baseline glucose metrics |
| `/patients/{id}/patterns` | GET | Detected glucose patterns |
| `/patients/{id}/daily-brief` | GET | Daily intelligence brief |

## Design System

| Token | Value | Usage |
|-------|-------|-------|
| Primary | #315BFF | Buttons, active states |
| Background | #F6F7F9 | Page background |
| Surface | #FFFFFF | Cards, inputs |
| Text Primary | #1A1D21 | Headlines |
| Text Secondary | #8A8E97 | Body, captions |
| Border | #E5E7EB | Dividers, outlines |

Typography: System fonts (SF Pro on iOS, Roboto on Android)

## Quality Standards

- ✅ TypeScript strict mode
- ✅ All functions typed
- ✅ Error handling for async operations
- ✅ 44px minimum touch targets
- ✅ Offline-first (no blocking network calls)

## Git Workflow

```bash
# Create feature branch
git checkout -b feature/week3-mobile-shell

# Commit changes
git add .
git commit -m "feat: add glucose logging form"

# Push to remote
git push origin feature/week3-mobile-shell
```

## License

Proprietary - Internal use only
