# Nadini — KI-Echtzeit-Dolmetschplattform

**nadini.ai** — Real-time AI interpreting for meetings, conferences, and business communication.

DSGVO-konform. AI-Act-ready. Mehrsprachig (DE / EN / FR). Open-Source-Übersetzung.

[![CI](https://github.com/HatemHamzaoui/Nadini/actions/workflows/ci.yml/badge.svg)](https://github.com/HatemHamzaoui/Nadini/actions/workflows/ci.yml)

---

## Quickstart

No build tools, no dependencies. Just open in a browser:

```bash
# Clone
git clone <repo-url> && cd Lisan

# Open landing page
open index.html
# or
open landing/index.html

# Open app directly (demo mode)
open app/login.html?demo=1
```

### Full Stack (Docker) — empfohlen

```bash
make up          # Startet alles (Keys + Build + 5 Container)
make logs        # Logs aller Services
make test-e2e    # Smoke-Test (Health-Checks)
make ps          # Container-Status
make down        # Stoppen
make help        # Alle Befehle
```

Oder manuell:

```bash
# 1. JWT-Schlüssel generieren
cd auth-service && bash scripts/generate_keys.sh && cd ..

# 2. Stack starten (Postgres + Redis + Auth-Service + Meeting-Service + Nginx)
docker compose up --build

# 3. Öffnen
open http://localhost:3000
```

Frontend auf `localhost:3000`, Auth-API auf `localhost:8001`.
Nginx proxied `/auth/*` automatisch zum Auth-Service.

Der Console-Mailer schreibt Magic-Links in die Docker-Logs:
```bash
docker compose logs auth-service | grep "magic_link_email_console"
```

### Deploy to Netlify

```bash
# Drag & drop the project folder to netlify.com/drop
# or use the CLI:
netlify deploy --dir=. --prod
```

`_redirects` is already configured for clean URLs.

---

## Project Structure

```
nadini/
├── index.html              Root redirect → Landing Page
├── manifest.json           PWA manifest
├── sw.js                   Service Worker (cache-first assets, network-first HTML)
├── _redirects              Netlify routing
├── 404.html                Error page (DE/EN/FR)
│
├── assets/
│   ├── favicon.svg         Favicon (teal + gold ن)
│   ├── icon-192.svg        PWA icon 192px
│   └── icon-512.svg        PWA icon 512px
│
├── landing/                Landing Page (nadini.ai)
│   ├── index.html          Hero, Features, Pricing, CTA
│   ├── style.css           Landing styles (LexAdQ Design System)
│   ├── i18n.js             Translations DE/EN/FR
│   └── app.js              Interactions (theme, nav, scroll)
│
└── app/                    Web Application
    ├── login.html          Magic Link login + Demo mode
    ├── disclosure.html     AI Act Art. 50 disclosure (mandatory)
    ├── dashboard.html      Stats, quick meeting, recent meetings
    ├── meetings.html       Scheduled + past meetings
    ├── meeting.html        Live meeting room
    ├── join.html           Meeting join page (invite link target)
    ├── transcripts.html    Transcript archive
    ├── transcript-view.html  Transcript detail + export
    ├── languages.html      16 supported languages + usage stats
    ├── settings.html       Profile, defaults, theme, compliance, API
    ├── style.css           App styles (LexAdQ Design System)
    ├── meeting.css         Meeting room styles
    ├── i18n-app.js         App translations DE/EN/FR (~200 keys)
    ├── auth.js             Magic Link auth flow + demo mode
    ├── dashboard.js        Dashboard logic
    ├── meeting.js          Meeting room (transcript, captions, shortcuts)
    ├── settings.js         Settings logic
    └── page-common.js      Shared logic (auth guard, sidebar, theme)
```

---

## User Flow

```
Landing Page
  ├─ "Kostenlos testen"     → Login (email pre-filled)
  ├─ "Demo ansehen"         → Login (auto-demo)
  └─ "Jetzt starten"        → Login
         │
         ├─ Magic Link        → Postfach → Token verify → App
         └─ Demo-Button       → Disclosure → Dashboard
                                    │
           ┌────────────────────────┤
           ▼                        ▼
      Dashboard ──────────► Meeting Room
        │  │                   │  │  │
        │  └─► Meetings        │  │  └─► Captions Overlay
        │      │               │  └────► Invite Modal
        │      └─► Join Page ◄─┘           │
        │                                  ▼
        ├─► Transcripts ──► Transcript Viewer (TXT/PDF Export)
        ├─► Languages (16 Sprachen + Statistik)
        └─► Settings (Profil, Theme, Compliance, API)
```

---

## Features

### Landing Page
- Responsive Hero mit Live-Demo-Vorschau
- Features, Pricing (3 Tiers), Compliance-Sektion
- CTA mit E-Mail-Eingabe → Login
- Scroll-Animationen, Logo-Section

### Authentication
- **Magic Link** — passwortlos per E-Mail
- **Demo-Modus** — sofort testen ohne Anmeldung
- Token-Handling (Access + Refresh in localStorage)
- Auth Guard auf allen geschützten Seiten

### AI Act Compliance (Art. 50)
- Pflicht-Disclosure vor erster Nutzung
- Versionierte Texte (DE/EN/FR)
- Permanent gespeicherte Bestätigung
- Provenance-Hinweis auf allen Transkripten

### Meeting Room
- **Echtzeit-Spracherkennung** via Web Speech API (Browser ASR)
- **Echtzeit-Übersetzung** via argostranslate (offline, open-source)
- **Echte Audio-Bars** via getUserMedia + AnalyserNode
- **Live-Untertitel** mit Interim-Results (Toggle `C`)
- **Screen-Sharing** via getDisplayMedia (Toggle `S`)
- **Audio-Recording** via MediaRecorder → WebM Download (Toggle `R`)
- **Webcam-Video** als Self-Preview (Toggle `V`)
- **Text-Chat** parallel zum Transkript (WebSocket)
- **Emoji-Reaktionen** (👍🎉❤️😂🙏👏) — animierte Bubbles
- **Einladungs-Modal** (Link kopieren + E-Mail-Einladung)
- **3 Sprachkanäle** (Original + AI-Übersetzungen)
- **Transkript-Download** als TXT
- **Keyboard-Shortcuts**: `M` Mic, `C` Captions, `S` Screen, `R` Record, `V` Video, `D` Download, `I` Invite, `Esc` Close

### Meeting Scheduling
- **Datum/Uhrzeit-Picker** für geplante Meetings
- **Beschreibung + E-Mail-Einladungen** bei Erstellung
- **Einladungs-E-Mails** (DE/EN/FR) mit Termin + Join-Link
- **Live-Countdown** auf dem Dashboard ("2h 14m 38s")
- **Status**: scheduled → active → ended

### Dashboard Widgets
- **Nächstes Meeting**: Live-Countdown mit Name + Datum
- **Aktivitäts-Bars**: 7-Tage-Übersicht
- **Quick Actions**: Links zu allen Hauptseiten

### Transcript Viewer
- Vollständiger Gesprächsverlauf mit Übersetzungen
- **Sprachfilter** (Alle / DE / EN / FR)
- **TXT-Export** (formatiert mit Header + Provenance)
- **PDF-Export** (Browser Print-Dialog)
- Teilnehmer-Sidebar + Meeting-Details

### Settings
- Profil (E-Mail, Anzeigename, UI-Sprache)
- Meeting-Voreinstellungen (Quell-/Zielsprachen, Auto-Transkript)
- Theme-Auswahl (Dark/Light mit Vorschau-Cards)
- Compliance-Status (Disclosure, Datenexport, Konto löschen)
- API-Zugang (Key mit Show/Copy, JWKS-Endpoint)

---

## Tech Stack

| Layer | Technologie |
|---|---|
| Frontend | Vanilla HTML, CSS, JavaScript |
| Design System | LexAdQ v1.0 (CSS Custom Properties) |
| Icons | Inline SVG (kein Icon-Font) |
| i18n | Custom JS (DOM data-attributes) |
| Auth | Magic Link (Demo: localStorage) |
| PWA | manifest.json + Service Worker |
| Deployment | Netlify (`_redirects`) |
| Auth Backend | Python 3.12, FastAPI, SQLAlchemy 2, PostgreSQL 16, Redis 7 |
| Meeting Backend | Python 3.12, FastAPI, WebSocket, argostranslate |
| Translation | argostranslate (offline, open-source, DE↔EN↔FR↔ES) |
| ASR | Web Speech API (Browser), Whisper-ready (Option B) |

### Design System — LexAdQ

- **Dark Mode**: Teal Background (#0e4243), Navy Accents
- **Light Mode**: White/Gray mit gleichen Akzenten
- **Brand-Farbe**: Amber/Gold (#E8820C)
- **Typografie**: Segoe UI / System Font Stack
- **Spacing**: 4px–32px Scale
- **Komponenten**: Cards, Buttons, Badges, Inputs, Tables, Modals, Toasts

---

## Internationalisierung (i18n)

Drei Sprachen mit ~200 Keys pro Sprache:

| Sprache | Code | Landing | App |
|---|---|---|---|
| Deutsch | `de` | Vollständig | Vollständig |
| English | `en` | Vollständig | Vollständig |
| Français | `fr` | Vollständig | Vollständig |

Sprache wird erkannt via:
1. `localStorage` (nadini-lang)
2. `navigator.language`
3. Fallback: Deutsch

---

## Accessibility (WCAG)

- Skip-Navigation auf allen Seiten
- `aria-label` auf Icon-Only-Buttons
- `aria-current="page"` auf aktiver Navigation
- `role="dialog"` + `aria-modal` auf Modals
- `role="switch"` + Keyboard-Support auf Toggles
- `aria-live="polite"` auf Live-Captions
- `:focus-visible` Styles (Keyboard-Only-Fokusring)
- `prefers-reduced-motion` (CSS + JS)
- Korrekte Label-Input-Verknüpfung (`for`-Attribute)

---

## Unterstützte Sprachen (Übersetzung)

12 aktiv + 4 geplant:

| Aktiv | Geplant |
|---|---|
| DE, EN, FR, ES, IT, PT | NL, PL |
| AR, ZH, JA, KO, RU, TR | SV, HI |

---

## Backend (Auth Service)

Der Auth-Service ist als Python/FastAPI-Microservice spezifiziert:

- **Magic Link**: SHA-256 Hash, 5-Min TTL, Single-Use, Atomic Consume
- **JWT**: RS256, Access 15min, Refresh 30d, Rotation
- **AI Act**: Disclosure-Versionierung, Audit-Logs, Risk-Tier
- **Rate Limiting**: Redis ZSET Sliding Window
- **Stack**: Python 3.12, FastAPI, SQLAlchemy 2, PostgreSQL 16, Redis 7

Siehe `meetplatform-auth-service.tar.gz` für die vollständige Implementierung.

---

## Deployment

### Netlify (empfohlen)

1. Repository verbinden oder Drag & Drop
2. Build-Command: (keiner nötig)
3. Publish Directory: `.`
4. `_redirects` konfiguriert automatisch Routing

### Statischer Server

```bash
# Python
python3 -m http.server 3000

# Node
npx serve .

# Dann öffnen:
open http://localhost:3000
```

### PWA-Installation

Nach dem ersten Besuch erscheint auf unterstützten Browsern die Option "Zum Startbildschirm hinzufügen". Die App funktioniert dann offline mit gecachten Assets.

---

## Lizenz

Proprietary — LexAdQ GmbH, Braunschweig

---

## Kontakt

**Nadini** — LexAdQ GmbH
Bruchtorwall 6, 38100 Braunschweig
https://nadini.ai
