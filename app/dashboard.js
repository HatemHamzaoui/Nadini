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

  // ── New Meeting Form ──
  const meetingForm = document.getElementById("meetingForm");
  if (meetingForm) {
    meetingForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const name = document.getElementById("meetingName").value || "Neues Meeting";
      const source = document.getElementById("sourceLang").value;
      const targets = Array.from(document.getElementById("targetLangs").selectedOptions).map(o => o.value);

      const btn = meetingForm.querySelector("button[type=submit]");
      btn.disabled = true;
      if (typeof toast !== "undefined") toast.success("Meeting \"" + name + "\" wird gestartet…");

      setTimeout(() => {
        window.location.href = "meeting.html";
      }, 1000);
    });
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
