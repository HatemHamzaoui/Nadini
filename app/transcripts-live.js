/**
 * Nadini — Transcripts Page: Live API Integration
 * Fetches ended meetings and renders transcript cards dynamically.
 */
(function () {
  "use strict";

  const cfg = typeof NADINI_CONFIG !== "undefined" ? NADINI_CONFIG : { API_MODE: "demo" };
  if (cfg.API_MODE !== "live") return;

  const token = localStorage.getItem("nadini-access-token");
  if (!token || token === "demo-access-token") return;

  const lang = localStorage.getItem("nadini-lang") || "de";
  const L = {
    de: { words: "Wörter", participants: "Teilnehmer", view: "Anzeigen" },
    en: { words: "words", participants: "participants", view: "View" },
    fr: { words: "mots", participants: "participants", view: "Afficher" },
  }[lang] || { words: "Wörter", participants: "Teilnehmer", view: "Anzeigen" };

  async function loadTranscripts() {
    try {
      const res = await fetch(`${cfg.MEETING_API_BASE}/meetings`, {
        headers: { "Authorization": `Bearer ${token}` },
      });
      if (!res.ok) return;
      const meetings = await res.json();
      const ended = meetings.filter(m => m.status === "ended");

      const list = document.getElementById("transcriptList");
      if (!list || ended.length === 0) return;

      list.innerHTML = ended.map(m => {
        const date = new Date(m.created_at).toLocaleDateString("de-DE");
        const dur = m.duration_seconds ? `${Math.round(m.duration_seconds / 60)} min` : "—";
        const targets = m.target_langs.map(l => l.toUpperCase()).join(", ");

        return `
          <div class="transcript-card">
            <div class="transcript-card-left">
              <div class="transcript-card-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/></svg>
              </div>
              <div class="transcript-card-info">
                <h3>${m.name}</h3>
                <div class="transcript-card-meta">
                  <span>${date}</span><span class="meta-sep">&middot;</span>
                  <span>${dur}</span><span class="meta-sep">&middot;</span>
                  <span>${m.participant_count || 0} ${L.participants}</span><span class="meta-sep">&middot;</span>
                  <span>${m.source_lang.toUpperCase()} → ${targets}</span>
                </div>
              </div>
            </div>
            <div class="transcript-card-right">
              <a href="transcript-view.html?id=${m.meeting_id}" class="btn btn-secondary btn-sm">${L.view}</a>
            </div>
          </div>`;
      }).join("");
    } catch (e) { /* silent */ }
  }

  loadTranscripts();
})();
