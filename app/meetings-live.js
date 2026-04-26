/**
 * Nadini — Meetings Page: Live API Integration
 * Fetches real meeting data, handles scheduled/active/ended states.
 */
(function () {
  "use strict";

  const cfg = typeof NADINI_CONFIG !== "undefined" ? NADINI_CONFIG : { API_MODE: "demo" };
  if (cfg.API_MODE !== "live") return;

  const token = localStorage.getItem("nadini-access-token");
  if (!token || token === "demo-access-token") return;

  const lang = localStorage.getItem("nadini-lang") || "de";
  const L = {
    de: { scheduled: "Geplant", active: "Live", ended: "Abgeschlossen", join: "Beitreten", transcript: "Transkript", participants: "Teilnehmer", in_: "in", ago: "vor", min: "min", h: "Std.", d: "Tagen" },
    en: { scheduled: "Scheduled", active: "Live", ended: "Completed", join: "Join", transcript: "Transcript", participants: "participants", in_: "in", ago: "ago", min: "min", h: "hrs", d: "days" },
    fr: { scheduled: "Planifié", active: "En direct", ended: "Terminé", join: "Rejoindre", transcript: "Transcription", participants: "participants", in_: "dans", ago: "il y a", min: "min", h: "h", d: "jours" },
  }[lang] || { scheduled: "Geplant", active: "Live", ended: "Abgeschlossen", join: "Beitreten", transcript: "Transkript", participants: "Teilnehmer", in_: "in", ago: "vor", min: "min", h: "Std.", d: "Tagen" };

  function timeUntil(dateStr) {
    const diff = new Date(dateStr) - new Date();
    if (diff < 0) return null;
    const mins = Math.round(diff / 60000);
    if (mins < 60) return `${L.in_} ${mins} ${L.min}`;
    const hrs = Math.round(mins / 60);
    if (hrs < 24) return `${L.in_} ${hrs} ${L.h}`;
    return `${L.in_} ${Math.round(hrs / 24)} ${L.d}`;
  }

  function formatDate(dateStr) {
    return new Date(dateStr).toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
  }

  async function loadMeetings() {
    try {
      const res = await fetch(`${cfg.MEETING_API_BASE}/meetings`, {
        headers: { "Authorization": `Bearer ${token}` },
      });
      if (!res.ok) return;
      const meetings = await res.json();

      const upcoming = meetings.filter(m => m.status === "scheduled" || m.status === "active" || m.status === "waiting");
      const ended = meetings.filter(m => m.status === "ended");

      renderSection(".meetings-section:first-of-type .meetings-list", upcoming, "upcoming");
      renderSection(".meetings-section:last-of-type .meetings-list", ended, "done");
    } catch (e) { /* keep static HTML */ }
  }

  function renderSection(selector, items, type) {
    const el = document.querySelector(selector);
    if (!el) return;
    if (items.length === 0) {
      el.innerHTML = `<p style="color:var(--lx-text-dimmed);font-size:13px;padding:12px 0;">—</p>`;
      return;
    }
    el.innerHTML = items.map(m => meetingRow(m, type)).join("");
  }

  function meetingRow(m, type) {
    const targets = m.target_langs.map(l => l.toUpperCase()).join(", ");
    const langPair = `${m.source_lang.toUpperCase()} → ${targets}`;

    let dateLine, badge, action, icon;

    if (m.status === "scheduled") {
      const schedDate = formatDate(m.scheduled_at);
      const countdown = timeUntil(m.scheduled_at);
      dateLine = `${schedDate}${countdown ? ` (${countdown})` : ""}`;
      badge = `<span class="badge badge-gold">${L.scheduled}</span>`;
      action = `<button class="btn btn-primary btn-sm" onclick="window.location.href='meeting.html?id=${m.meeting_id}&lang=${m.source_lang}'">${L.join}</button>`;
      icon = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>`;
    } else if (m.status === "active" || m.status === "waiting") {
      dateLine = new Date(m.created_at).toLocaleDateString("de-DE");
      badge = `<span class="badge badge-green" style="background:rgba(239,68,68,0.12);color:var(--lx-red);border-color:rgba(239,68,68,0.25);">${L.active}</span>`;
      action = `<button class="btn btn-primary btn-sm" onclick="window.location.href='meeting.html?id=${m.meeting_id}&lang=${m.source_lang}'">${L.join}</button>`;
      icon = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M10 8l6 4-6 4V8z"/></svg>`;
    } else {
      const dur = m.duration_seconds ? `${Math.round(m.duration_seconds / 60)} min` : "—";
      dateLine = `${new Date(m.created_at).toLocaleDateString("de-DE")} · ${dur}`;
      badge = `<span class="badge badge-green">${L.ended}</span>`;
      action = `<a href="transcript-view.html?id=${m.meeting_id}" class="btn btn-secondary btn-sm">${L.transcript}</a>`;
      icon = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m5 12 5 5L20 7"/></svg>`;
    }

    const escDesc = (m.description || "").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    const desc = escDesc ? `<span class="meeting-row-desc">${escDesc}</span>` : "";
    const iconClass = type === "upcoming" ? "meeting-row-icon-upcoming" : "meeting-row-icon-done";

    return `
      <div class="meeting-row">
        <div class="meeting-row-left">
          <div class="meeting-row-icon ${iconClass}">${icon}</div>
          <div class="meeting-row-info">
            <h3>${m.name} ${m.mode === "live" ? '<span class="mode-badge-live">🎙️ Live</span>' : ''}</h3>
            ${desc}
            <div class="meeting-row-meta">
              <span>${dateLine}</span><span class="meta-sep">&middot;</span>
              <span>${m.participant_count || 0} ${L.participants}</span><span class="meta-sep">&middot;</span>
              <span>${langPair}</span>
            </div>
          </div>
        </div>
        <div class="meeting-row-right">${badge}${action}</div>
      </div>`;
  }

  loadMeetings();
})();
