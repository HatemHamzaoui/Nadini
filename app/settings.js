/**
 * Nadini — Settings Page Logic
 */
(function () {
  "use strict";

  // ── Auth Guard ──
  if (!localStorage.getItem("nadini-access-token")) {
    window.location.href = "login.html";
    return;
  }

  // ── User Info ──
  const email = localStorage.getItem("nadini-user-email") || "user@example.com";
  const avatarEl = document.getElementById("userAvatar");
  const emailEl = document.getElementById("userEmail");
  const settingsEmail = document.getElementById("settingsEmail");
  if (emailEl) emailEl.textContent = email;
  if (avatarEl) avatarEl.textContent = email.charAt(0).toUpperCase();
  if (settingsEmail) settingsEmail.value = email;

  // ── Theme ──
  const themeToggle = document.getElementById("themeToggle");
  const savedTheme = localStorage.getItem("nadini-theme");
  if (savedTheme) document.documentElement.dataset.theme = savedTheme;
  if (themeToggle) {
    themeToggle.addEventListener("click", () => {
      const next = (document.documentElement.dataset.theme || "dark") === "dark" ? "light" : "dark";
      document.documentElement.dataset.theme = next;
      localStorage.setItem("nadini-theme", next);
      updateThemeCards();
    });
  }

  // ── Sidebar Toggle ──
  const sidebarToggle = document.getElementById("sidebarToggle");
  const sidebar = document.getElementById("sidebar");
  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener("click", () => sidebar.classList.toggle("open"));
    document.addEventListener("click", (e) => {
      if (sidebar.classList.contains("open") && !sidebar.contains(e.target) && e.target !== sidebarToggle) {
        sidebar.classList.remove("open");
      }
    });
  }

  // ── Logout ──
  const logoutBtn = document.getElementById("logoutBtn");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", () => {
      localStorage.removeItem("nadini-access-token");
      localStorage.removeItem("nadini-refresh-token");
      localStorage.removeItem("nadini-user-email");
      window.location.href = "login.html";
    });
  }

  // ── Theme Cards ──
  function updateThemeCards() {
    const current = document.documentElement.dataset.theme || "dark";
    document.querySelectorAll(".theme-card").forEach(card => {
      card.classList.toggle("theme-card-active", card.dataset.setTheme === current);
    });
  }
  updateThemeCards();

  document.querySelectorAll(".theme-card").forEach(card => {
    card.addEventListener("click", () => {
      document.documentElement.dataset.theme = card.dataset.setTheme;
      localStorage.setItem("nadini-theme", card.dataset.setTheme);
      updateThemeCards();
    });
  });

  // ── Toggle Switches ──
  document.querySelectorAll(".toggle-switch").forEach(toggle => {
    function flip() {
      toggle.classList.toggle("active");
      toggle.setAttribute("aria-checked", toggle.classList.contains("active"));
    }
    toggle.addEventListener("click", flip);
    toggle.addEventListener("keydown", (e) => {
      if (e.key === " " || e.key === "Enter") { e.preventDefault(); flip(); }
    });
  });

  // ── Save Buttons ──
  const cfg = typeof NADINI_CONFIG !== "undefined" ? NADINI_CONFIG : { API_MODE: "demo" };
  const isLive = cfg.API_MODE === "live" && token && token !== "demo-access-token";

  document.querySelectorAll("[id^='save']").forEach(btn => {
    btn.addEventListener("click", async () => {
      btn.disabled = true;

      if (isLive && btn.id === "saveProfileBtn") {
        try {
          const uiLangVal = document.getElementById("uiLang")?.value;
          await fetch(`${cfg.AUTH_API_BASE}/auth/me`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
            body: JSON.stringify({ ui_language: uiLangVal }),
          });
        } catch (e) { /* silent */ }
      }

      setTimeout(() => { btn.disabled = false; }, 800);
      if (typeof toast !== "undefined") toast.success("Einstellungen gespeichert");
    });
  });

  // ── UI Language Sync ──
  const uiLang = document.getElementById("uiLang");
  if (uiLang) {
    uiLang.value = localStorage.getItem("nadini-lang") || "de";
    uiLang.addEventListener("change", () => {
      if (typeof setLanguage === "function") setLanguage(uiLang.value);
    });
  }

  // ── API Key Toggle ──
  const apiField = document.getElementById("apiKeyField");
  const toggleKey = document.getElementById("toggleApiKey");
  if (toggleKey && apiField) {
    toggleKey.addEventListener("click", () => {
      apiField.type = apiField.type === "password" ? "text" : "password";
    });
  }

  const copyKey = document.getElementById("copyApiKey");
  if (copyKey && apiField) {
    copyKey.addEventListener("click", () => {
      navigator.clipboard.writeText(apiField.value).catch(() => {});
      if (typeof toast !== "undefined") toast.success("API-Schlüssel kopiert");
    });
  }
})();
