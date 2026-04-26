/**
 * Nadini — Dashboard Logic
 */
(function () {
  "use strict";

  // ── Service Worker ──
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("../sw.js").catch(() => {});
  }

  // ── Auth Guard ──
  const token = localStorage.getItem("nadini-access-token");
  if (!token) {
    window.location.href = "login.html";
    return;
  }

  // ── User Info ──
  const email = localStorage.getItem("nadini-user-email") || "user@example.com";
  const avatarEl = document.getElementById("userAvatar");
  const emailEl = document.getElementById("userEmail");
  if (emailEl) emailEl.textContent = email;
  if (avatarEl) avatarEl.textContent = email.charAt(0).toUpperCase();

  // ── Sidebar Toggle (Mobile) ──
  const sidebarToggle = document.getElementById("sidebarToggle");
  const sidebar = document.getElementById("sidebar");
  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener("click", () => sidebar.classList.toggle("open"));

    // Close on outside click
    document.addEventListener("click", (e) => {
      if (sidebar.classList.contains("open") && !sidebar.contains(e.target) && e.target !== sidebarToggle) {
        sidebar.classList.remove("open");
      }
    });
  }

  // ── Logout ──
  const logoutBtn = document.getElementById("logoutBtn");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", async () => {
      // In production: POST /auth/logout with Bearer token
      localStorage.removeItem("nadini-access-token");
      localStorage.removeItem("nadini-refresh-token");
      localStorage.removeItem("nadini-user-email");
      window.location.href = "login.html";
    });
  }

  // ── API Helper ──
  const cfg = typeof NADINI_CONFIG !== "undefined" ? NADINI_CONFIG : { API_MODE: "demo" };
  const isLive = cfg.API_MODE === "live";

  async function apiPost(base, path, body) {
    const res = await fetch(`${base}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`API ${res.status}`);
    return res.json();
  }

  async function apiGet(base, path) {
    const res = await fetch(`${base}${path}`, {
      headers: { "Authorization": `Bearer ${token}` },
    });
    if (!res.ok) throw new Error(`API ${res.status}`);
    return res.json();
  }

  // ── New Meeting Form ──
  const meetingForm = document.getElementById("meetingForm");
  if (meetingForm) {
    meetingForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const name = document.getElementById("meetingName").value || "Neues Meeting";
      const source = document.getElementById("sourceLang").value;
      const targets = Array.from(document.getElementById("targetLangs").selectedOptions).map(o => o.value);
      const scheduleVal = document.getElementById("meetingSchedule")?.value;
      const descVal = document.getElementById("meetingDesc")?.value?.trim() || null;
      const invitesVal = document.getElementById("meetingInvites")?.value?.trim();
      const invitedEmails = invitesVal ? invitesVal.split(",").map(e => e.trim()).filter(Boolean) : null;
      const scheduledAt = scheduleVal ? new Date(scheduleVal).toISOString() : null;
      const isScheduled = !!scheduledAt;

      const btn = meetingForm.querySelector("button[type=submit]");
      btn.disabled = true;

      try {
        if (isLive) {
          const meeting = await apiPost(cfg.MEETING_API_BASE, "/meetings", {
            name, source_lang: source, target_langs: targets,
            scheduled_at: scheduledAt, description: descVal, invited_emails: invitedEmails,
          });

          if (isScheduled) {
            if (typeof toast !== "undefined") toast.success(`Meeting "${name}" geplant`);
            btn.disabled = false;
            meetingForm.reset();
            // Reload meeting list
            setTimeout(() => window.location.reload(), 800);
          } else {
            const displayName = email.split("@")[0];
            await apiPost(cfg.MEETING_API_BASE, `/meetings/${meeting.meeting_id}/join`, {
              display_name: displayName, language: source,
            });
            if (typeof toast !== "undefined") toast.success(`Meeting "${name}" gestartet`);
            localStorage.setItem("nadini-meeting-lang", source);
            setTimeout(() => { window.location.href = `meeting.html?id=${meeting.meeting_id}&lang=${source}`; }, 600);
          }
        } else {
          if (typeof toast !== "undefined") toast.success(isScheduled ? `Meeting "${name}" geplant` : `Meeting "${name}" wird gestartet…`);
          if (isScheduled) { btn.disabled = false; meetingForm.reset(); }
          else { setTimeout(() => { window.location.href = "meeting.html"; }, 800); }
        }
      } catch (err) {
        btn.disabled = false;
        if (typeof toast !== "undefined") toast.error("Fehler beim Erstellen des Meetings");
      }
    });
  }

  // ── Load Stats + Recent Meetings (Live Mode) ──
  if (isLive) {
    // Stats
    (async () => {
      try {
        const stats = await apiGet(cfg.MEETING_API_BASE, "/meetings/stats");
        const s = document.getElementById("statMeetings");
        const h = document.getElementById("statHours");
        const l = document.getElementById("statLangs");
        const p = document.getElementById("statParticipants");
        if (s) s.textContent = stats.meetings;
        if (h) h.textContent = stats.hours + "h";
        if (l) l.textContent = stats.languages_used;
        if (p) p.textContent = stats.participants;
      } catch (e) { /* keep demo data */ }
    })();

    // Recent Meetings
    (async () => {
      try {
        const meetings = await apiGet(cfg.MEETING_API_BASE, "/meetings");
        const statEl = document.getElementById("statMeetings"); // fallback if stats failed
        if (statEl && statEl.textContent === "12") statEl.textContent = meetings.length;

        // Update recent meetings list
        const list = document.querySelector(".meeting-list");
        if (list && meetings.length > 0) {
          list.innerHTML = "";
          meetings.slice(0, 5).forEach(m => {
            const lang = localStorage.getItem("nadini-lang") || "de";
            const statusText = m.status === "ended" ? (lang === "de" ? "Abgeschlossen" : lang === "fr" ? "Terminé" : "Completed") : "Live";
            const date = new Date(m.created_at).toLocaleDateString("de-DE");
            const dur = m.duration_seconds ? `${Math.round(m.duration_seconds / 60)} min` : "—";
            const targets = m.target_langs.join(", ").toUpperCase();

            list.innerHTML += `
              <div class="meeting-item">
                <div class="meeting-info">
                  <span class="meeting-name">${m.name}</span>
                  <span class="meeting-meta">${date} · ${dur} · ${m.source_lang.toUpperCase()} → ${targets}</span>
                </div>
                <div class="meeting-badges">
                  <span class="badge badge-green">${statusText}</span>
                </div>
              </div>`;
          });
        }
      } catch (err) { /* silent — demo data stays */ }
    })();
  }

  // ── Theme Toggle ──
  const themeToggle = document.getElementById("themeToggle");
  if (themeToggle) {
    const savedTheme = localStorage.getItem("nadini-theme");
    if (savedTheme) document.documentElement.dataset.theme = savedTheme;

    themeToggle.addEventListener("click", () => {
      const next = (document.documentElement.dataset.theme || "dark") === "dark" ? "light" : "dark";
      document.documentElement.dataset.theme = next;
      localStorage.setItem("nadini-theme", next);
    });
  }
})();
