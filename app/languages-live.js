/**
 * Nadini — Languages Page: Live Usage Stats
 */
(function () {
  "use strict";

  const cfg = typeof NADINI_CONFIG !== "undefined" ? NADINI_CONFIG : { API_MODE: "demo" };
  if (cfg.API_MODE !== "live") return;

  const token = localStorage.getItem("nadini-access-token");
  if (!token || token === "demo-access-token") return;

  const lang = localStorage.getItem("nadini-lang") || "de";
  const L = {
    de: { pair: "Sprachpaar", meetings: "Meetings", hours: "Stunden" },
    en: { pair: "Language pair", meetings: "Meetings", hours: "Hours" },
    fr: { pair: "Paire de langues", meetings: "Réunions", hours: "Heures" },
  }[lang] || { pair: "Sprachpaar", meetings: "Meetings", hours: "Stunden" };

  (async () => {
    try {
      const res = await fetch(`${cfg.MEETING_API_BASE}/meetings/stats`, {
        headers: { "Authorization": `Bearer ${token}` },
      });
      if (!res.ok) return;
      const stats = await res.json();

      if (!stats.language_pairs || stats.language_pairs.length === 0) return;

      const tbody = document.querySelector(".usage-table tbody");
      if (!tbody) return;

      tbody.innerHTML = stats.language_pairs.map(p => `
        <tr>
          <td>${p.pair}</td>
          <td>${p.meetings}</td>
          <td>${p.hours}h</td>
          <td>—</td>
          <td>—</td>
        </tr>
      `).join("");
    } catch (e) { /* keep demo data */ }
  })();
})();
