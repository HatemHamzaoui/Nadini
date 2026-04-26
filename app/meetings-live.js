/**
 * Nadini — Meetings Page: Live API Integration
 * Fetches real meeting data in live mode, keeps static HTML as demo fallback.
 */
(function () {
  "use strict";

  const cfg = typeof NADINI_CONFIG !== "undefined" ? NADINI_CONFIG : { API_MODE: "demo" };
  if (cfg.API_MODE !== "live") return;

  const token = localStorage.getItem("nadini-access-token");
  if (!token || token === "demo-access-token") return;

  const lang = localStorage.getItem("nadini-lang") || "de";
  const labels = {
    de: { scheduled: "Geplant", ended: "Abgeschlossen", join: "Beitreten", transcript: "Transkript", participants: "Teilnehmer", invited: "eingeladen" },
    en: { scheduled: "Scheduled", ended: "Completed", join: "Join", transcript: "Transcript", participants: "participants", invited: "invited" },
    fr: { scheduled: "Planifié", ended: "Terminé", join: "Rejoindre", transcript: "Transcription", participants: "participants", invited: "invités" },
  };
  const L = labels[lang] || labels.de;

  async function loadMeetings() {
    try {
      const res = await fetch(`${cfg.MEETING_API_BASE}/meetings`, {
        headers: { "Authorization": `Bearer ${token}` },
      });
      if (!res.ok) return;
      const meetings = await res.json();

      const active = meetings.filter(m => m.status !== "ended");
      const ended = meetings.filter(m => m.status === "ended");

      // Render upcoming
      const upcomingSection = document.querySelector(".meetings-section:first-of-type .meetings-list");
      if (upcomingSection) {
        if (active.length === 0) {
          upcomingSection.innerHTML = `<p style="color:var(--lx-text-dimmed);font-size:13px;padding:12px 0;">—</p>`;
        } else {
          upcomingSection.innerHTML = active.map(m => meetingRow(m, "upcoming")).join("");
        }
      }

      // Render past
      const pastSection = document.querySelector(".meetings-section:last-of-type .meetings-list");
      if (pastSection) {
        if (ended.length === 0) {
          pastSection.innerHTML = `<p style="color:var(--lx-text-dimmed);font-size:13px;padding:12px 0;">—</p>`;
        } else {
          pastSection.innerHTML = ended.map(m => meetingRow(m, "done")).join("");
        }
      }
    } catch (e) { /* silent — keep static HTML */ }
  }

  function meetingRow(m, type) {
    const date = new Date(m.created_at).toLocaleDateString("de-DE");
    const dur = m.duration_seconds ? `${Math.round(m.duration_seconds / 60)} min` : "—";
    const targets = m.target_langs.map(l => l.toUpperCase()).join(", ");
    const langPair = `${m.source_lang.toUpperCase()} → ${targets}`;

    const icon = type === "upcoming"
      ? `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>`
      : `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m5 12 5 5L20 7"/></svg>`;

    const badge = type === "upcoming"
      ? `<span class="badge badge-gold">${L.scheduled}</span>`
      : `<span class="badge badge-green">${L.ended}</span>`;

    const action = type === "upcoming"
      ? `<button class="btn btn-primary btn-sm" onclick="window.location.href='meeting.html?id=${m.meeting_id}'">${L.join}</button>`
      : `<a href="transcript-view.html?id=${m.meeting_id}" class="btn btn-secondary btn-sm">${L.transcript}</a>`;

    return `
      <div class="meeting-row">
        <div class="meeting-row-left">
          <div class="meeting-row-icon meeting-row-icon-${type === "upcoming" ? "upcoming" : "done"}">${icon}</div>
          <div class="meeting-row-info">
            <h3>${m.name}</h3>
            <div class="meeting-row-meta">
              <span>${date}</span><span class="meta-sep">&middot;</span>
              <span>${dur}</span><span class="meta-sep">&middot;</span>
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
