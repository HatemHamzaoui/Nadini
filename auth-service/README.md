# Nadini Auth Service

Magic-Link-Authentifizierung mit AI-Act-Compliance-Hooks für die KI-Dolmetsch-Plattform Nadini.

- **Stack:** Python 3.12, FastAPI, SQLAlchemy 2 (async), Alembic, PostgreSQL 16, Redis 7, Resend
- **Auth-Verfahren:** Magic Link (passwortlos, 5-Minuten-TTL, Single-Use)
- **JWT:** RS256 (Access 15 min, Refresh 30 Tage, Rotation bei jedem `/refresh`)
- **AI Act:** Hybrid-Risk-Tier-Modell (Standard / High-Risk-Ready / High-Risk-Certified)

---

## Quickstart

```bash
# 1. JWT-Schlüsselpaar erzeugen
./scripts/generate_keys.sh

# 2. Stack starten (Postgres + Redis + Auth-Service mit auto-migrate)
docker compose up --build

# 3. Health-Check
curl http://localhost:8001/health
# → {"status":"ok"}

# 4. Magic Link anfordern (Console-Mailer schreibt den Link in den Container-Log)
curl -X POST http://localhost:8001/auth/magic-link \
    -H "Content-Type: application/json" \
    -d '{"email":"alice@example.com","ui_language":"de"}'

# 5. Link aus dem Log fischen (Console-Mailer)
docker compose logs auth-service | grep "magic_link_email_console"

# 6. Token verifizieren → JWT-Paar erhalten
curl -X POST http://localhost:8001/auth/verify-magic \
    -H "Content-Type: application/json" \
    -d '{"token":"<token-aus-log>"}'
```

Für Resend-Versand: `MAILER_DRIVER=resend` und `RESEND_API_KEY` setzen, dann `docker compose up`.

---

## API-Übersicht

| Methode | Endpoint | Auth | Beschreibung |
|---|---|---|---|
| POST | `/auth/magic-link` | — | Magic Link anfordern. Antwortet immer 202. |
| POST | `/auth/verify-magic` | — | Token einlösen → JWT-Paar + Compliance-Status. |
| POST | `/auth/refresh` | — | Refresh-Rotation: alter Token wird revoziert, neues Paar ausgegeben. |
| POST | `/auth/logout` | Bearer | Logout (Audit-Eintrag). |
| GET  | `/auth/me` | Bearer | Aktueller User + AI-Disclosure-Status. |
| GET  | `/auth/ai-disclosure?locale=de` | — | AI-Disclosure-Text (Art. 50 AI Act). |
| GET  | `/auth/ai-disclosure/locales` | — | Verfügbare Sprachen. |
| POST | `/auth/ai-disclosure/acknowledge` | Bearer | Bestätigung persistieren (permanente Aufbewahrung). |
| GET  | `/health` | — | Liveness. |
| GET  | `/.well-known/jwks.json` | — | Public Key für JWT-Verifikation. |

OpenAPI/Swagger: `http://localhost:8001/docs`

---

## Login-Flow im Detail

```
[Mobile App]                  [Auth Service]                [Resend]      [User Inbox]
     │                               │                           │              │
     │ POST /auth/magic-link         │                           │              │
     ├──────────────────────────────▶│                           │              │
     │                               │ user upsert, token-hash   │              │
     │                               │ in DB, mail an Resend     │              │
     │                               ├──────────────────────────▶│              │
     │ 202 Accepted                  │                           ├─────────────▶│
     │◀──────────────────────────────┤                           │              │
     │                                                                          │
     │ User klickt Link                                                         │
     │◀─────────────────────────────────────────────────────────────────────────┤
     │                                                                          │
     │ App empfängt Universal Link → POST /auth/verify-magic                    │
     ├──────────────────────────────▶│                                          │
     │                               │ atomar: UPDATE ... RETURNING             │
     │                               │ JWT-Pair + Disclosure-Flag               │
     │ 200 + access/refresh/         │                                          │
     │  compliance.disclosure_required◀─                                        │
     │◀──────────────────────────────┤                                          │
     │                                                                          │
     │ Falls disclosure_required:                                               │
     │ POST /auth/ai-disclosure/acknowledge                                     │
     ├──────────────────────────────▶│                                          │
     │ 201                           │                                          │
     │◀──────────────────────────────┤                                          │
```

---

## AI-Act-Compliance-Status

Das System ist auf den **Hybrid-Pfad** ausgelegt: Standard-Tenants sind unter Art. 50 AI Act compliant, Hochrisiko-Tenants können später aktiviert werden, ohne Architekturbruch.

| Pflicht | AI-Act-Artikel | Status MVP | Bemerkung |
|---|---|---|---|
| Information über KI-Interaktion | Art. 50(1) | ✅ implementiert | Disclosure-Endpunkt, Pflicht-Bestätigung vor erster Nutzung |
| Klare, zugängliche Information | Art. 50(5) | ✅ implementiert | Mehrsprachig (DE/EN/FR), versioniert, persistiert mit Locale |
| Beweispflicht der Information | Art. 50 + DSGVO | ✅ implementiert | `ai_disclosure_acknowledgments`-Tabelle mit IP/UA/Zeit/Locale |
| Maschinenlesbare Output-Kennzeichnung | Art. 50(2) | ⏳ Compliance-Service | Provenance-Signing in separatem Service (nächster Sprint) |
| Sichtbares UI-Label "KI aktiv" | Art. 50(5) | ⏳ Frontend | `short_label` wird vom API geliefert, Frontend muss es einbinden |
| Audit-Logging mit Kategorien | Art. 12 + 26 | ✅ implementiert | `audit_logs.event_category`, `retention_class` |
| Erweitertes Logging für Hochrisiko | Art. 12 | ✅ vorbereitet | `requires_extended_logging()` schaltet `extended_compliance` |
| KI-Kompetenz im Team | Art. 4 | ⏳ Prozess | Schulungsnachweise via `ai_literacy_records` (separater Service) |
| Tenant-Vertragsmanagement | Art. 25 | ✅ vorbereitet | `tenants.contract_signed_at`, `aup_version_accepted` |
| FRIA für Hochrisiko-Tenants | Art. 27 | ✅ vorbereitet | `tenants.fria_completed_at` |
| Schwerwiegende Vorfälle melden | Art. 73 | ⏳ Compliance-Service | Eigene Tabelle + Workflow im nächsten Service |
| Datenexport (DSGVO + Art. 86) | DSGVO Art. 15 | ⏳ nächster Sprint | `/auth/data-export` |

**Disclosure-Versionierung:** Bei jeder inhaltlichen Änderung des Disclosure-Texts in `app/compliance/disclosure.py` MUSS `CURRENT_DISCLOSURE_VERSION` erhöht werden — dann werden alle User beim nächsten Login zur erneuten Bestätigung aufgefordert.

---

## Datenbank-Schema

```
tenants
├── tenant_id (UUID)
├── risk_tier ('standard'|'high_risk_ready'|'high_risk_certified')
├── use_case_category, use_case_description
├── contract_signed_at, aup_version_accepted
├── high_risk_assessment_completed, fria_completed_at
└── created_at, updated_at

users
├── user_id (UUID)
├── email (unique), email_verified
├── ui_language
├── tenant_id → tenants
└── created_at, updated_at, last_login_at

magic_link_tokens
├── token_id (UUID)
├── token_hash (BYTEA[32], SHA-256, unique, indexiert)
├── email, user_id → users, purpose
├── ip_requested, user_agent
├── expires_at, used_at
└── partieller Index auf (expires_at) WHERE used_at IS NULL

refresh_tokens
├── token_jti_hash (BYTEA[32], PRIMARY KEY)
├── user_id → users
├── expires_at, revoked_at
└── user_agent, ip_address

ai_disclosure_acknowledgments        ← AI Act Art. 50(1)+(5) Beweispflicht
├── (user_id, disclosure_version) PRIMARY KEY
├── acknowledged_at, ip_address, user_agent, locale

audit_logs                          ← AI Act Art. 12 + 26
├── log_id (BIGSERIAL)
├── event_category ('auth'|'ai_interaction'|'compliance'|'admin'|'data_subject_request')
├── user_id, tenant_id, action, detail
├── ai_model_used, extra_data (JSONB)
├── retention_class ('standard'|'extended_compliance'|'permanent')
└── ip_address, user_agent, created_at
```

---

## Sicherheitsentscheidungen

| Maßnahme | Begründung |
|---|---|
| Token: 32 Bytes Random + Base64URL | 256 bit Entropie, brute-force-resistent |
| Nur SHA-256-Hash in DB | Klartext nicht wiederherstellbar |
| TTL 5 Minuten + Single-Use | Spec-Vorgabe + Replay-Schutz |
| Atomarer Konsum via `UPDATE ... RETURNING` | Keine TOCTOU-Race-Condition |
| Antwort immer 202 | Verhindert User-Enumeration |
| Sliding-Window-Rate-Limit (Redis ZSET) | Robust gegen Burst-Attacken |
| Pydantic-Längenvalidierung vor DB-Hit | Reduziert Last + frühe Fehlerantwort |
| RS256 statt HS256 | Public-Key-Verteilung über JWKS möglich |
| Refresh-Token-Rotation | Stolen-Token-Detection durch Doppel-Use |
| `event_category` + `retention_class` | AI-Act-konforme Audit-Differenzierung |

---

## Tests

```bash
pip install -e ".[dev]"
pytest -v
```

Tests benötigen Docker für `testcontainers` (Postgres + Redis werden automatisch hochgefahren).

**Test-Kategorien:**
- `test_magic_link_flow.py` — Roundtrip, Token-Konsum, Rate-Limit, Audit-Log
- `test_disclosure_flow.py` — AI-Disclosure-Endpunkt, Idempotenz, permanente Retention

---

## Vertragstemplates (Stichpunkte für Ihre Anwaltskanzlei)

Diese Liste ersetzt keine Rechtsberatung — sie ist ein Inhalts-Skelett zur Vorlage.

### Provider-Deployer-Vereinbarung (AI Act Art. 25)
- Verantwortlichkeitszuordnung: wer ist Provider, wer Deployer
- Pflicht des Deployers, das System gemäß Provider-Anweisungen zu verwenden
- Verbot der „wesentlichen Änderung" durch den Deployer (sonst wird er selbst zum Provider)
- Auskunftspflichten zwischen den Parteien (z. B. Vorfälle, Drift)
- Pflicht zur menschlichen Aufsicht (Art. 14)
- Logging-Pflichten (Art. 12) — wer speichert was, wie lange
- Meldung schwerwiegender Vorfälle (Art. 73) — Eskalationspfad
- Risk-Tier-Wechsel: wann wird Standard zu High-Risk
- Beendigung und Datenrückgabe

### Acceptable Use Policy (AUP)
- Erlaubte Use Cases (allgemeine Business-Meetings, Konferenzen, Bildung)
- **Ausgeschlossene Use Cases im Standard-Tier**:
  - Asyl-, Migrations- und Grenzkontrollverfahren (Anhang III Nr. 7)
  - Strafverfolgung, Polizeivernehmungen (Anhang III Nr. 6)
  - Gerichtsverfahren, Justizdolmetschen (Anhang III Nr. 8)
  - Bildungs-Prüfungen mit verbindlicher Bewertung (Anhang III Nr. 3)
  - Medizinische Diagnose-Gespräche (separate Regelung)
  - Sicherheitskritische Live-Übersetzung (Notfall, Luftverkehr, etc.)
- Verbotene Anwendungen:
  - Emotionserkennung am Arbeitsplatz (Art. 5)
  - Social Scoring
  - Manipulative Praktiken
- Migration zum Enterprise-Tier (High-Risk-Certified): wenn Hochrisiko-Use-Case beabsichtigt
- Rechte des Anbieters bei Verstoß (Sperrung, Datenlöschung, vertragliche Folgen)

### Auftragsverarbeitungsvereinbarung (AVV) nach DSGVO Art. 28
- Gegenstand und Dauer der Verarbeitung
- Art und Zweck der Verarbeitung (Audio-Verarbeitung, Übersetzungserzeugung)
- Art der personenbezogenen Daten (Audio-Aufnahmen, Übersetzungstexte, Metadaten)
- Kategorien betroffener Personen (Meeting-Teilnehmer)
- Subunternehmer (Mistral/Voxtral, ggf. ByteDance/Seed) — explizit benennen
- Technische und organisatorische Maßnahmen (TOM)
- Datenort: Standardmäßig EU; alternative Wahl USA muss explizit getroffen werden
- Löschfristen (Standard: 90 Tage, Compliance-Logs länger)
- Pflichten bei Datenschutzvorfällen (72h-Meldepflicht)
- Audit-Rechte des Verantwortlichen
- Datenrückgabe bei Vertragsende

### Sub-Auftragsverarbeitungsvereinbarungen
- Mit Mistral AI (Voxtral): EU-Anbieter, Standard-EU-Vertragsklauseln nicht nötig
- Mit ByteDance (Seed): Drittlandsübermittlung in die VR China — **Standardvertragsklauseln + Transfer-Impact-Assessment erforderlich**, ggf. ist diese Quelle aus DSGVO-Sicht nicht haltbar
- Mit Self-Hosted-Modellen (Hibiki, SimulStreaming): Sie selbst sind dann „Provider" im Sinne des AI Act → eigene technische Dokumentation nach Anhang XI

---

## Nächste Implementierungsschritte

1. **Compliance-Service** — eigener Microservice für:
   - Provenance-Signing (Ed25519) für Übersetzungssegmente
   - Watermarking (Text + Audio)
   - Schwerwiegende-Vorfälle-Workflow (Art. 73)
   - Datenexport-Endpunkt (DSGVO Art. 15 + AI Act Art. 86)
2. **Tenant-Service** — B2B-Onboarding mit Risk-Tier-Workflow:
   - Use-Case-Klassifizierung
   - Eskalation an Compliance-Team bei Hochrisiko-Verdacht
   - FRIA-Workflow (Fundamental Rights Impact Assessment)
3. **Meeting-Service** — bindet AI-Disclosure-Status ein (Block bei nicht bestätigter Disclosure)
4. **Routing-Engine + KI-Adapter** — bereits in der Spec definiert
5. **Audio-Streaming-Gateway** — WebSocket-basiert

---

## Lizenz

Proprietary — MeetPlatform GmbH

---

## Kontakt / Hinweise

Diese Implementierung deckt die im AI Act Art. 50 vorgeschriebenen Transparenzpflichten technisch ab.
**Sie ersetzt keine Rechtsberatung.** Insbesondere die Risikoklassifizierung Ihrer konkreten B2B-Kundenfälle, der Wortlaut der AGB/AVV und das Vorgehen bei der Hochrisiko-Zertifizierung (Notified Body, FRIA, EU-Datenbank-Eintrag) gehören in die Hand einer auf KI-Recht spezialisierten Kanzlei.
