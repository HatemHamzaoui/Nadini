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

  // ── Provider Dashboard (Live Mode) ──
  if (isLive) {
    (async () => {
      try {
        // Load providers
        const res = await fetch(`${cfg.MEETING_API_BASE}/providers`, {
          headers: { "Authorization": `Bearer ${token}` },
        });
        if (!res.ok) return;
        const providers = await res.json();

        const dash = document.getElementById("providerDashboard");
        if (dash) {
          const statusIcon = { green: "🟢", yellow: "🟡", red: "🔴", unknown: "⚪" };
          dash.innerHTML = `<table class="usage-table"><thead><tr>
            <th>Provider</th><th>Typ</th><th>Status</th><th>Latenz</th><th>API-Key</th><th>Aktiv</th>
          </tr></thead><tbody>${providers.map(p => {
            const h = p.health || {};
            const icon = statusIcon[h.status] || "⚪";
            const hasKey = p.has_key ? "✓ gesetzt" : "—";
            return `<tr>
              <td><strong>${p.name}</strong></td>
              <td>${p.provider_type}</td>
              <td>${icon} ${h.status || "?"}</td>
              <td>${h.avg_latency_ms ? Math.round(h.avg_latency_ms) + "ms" : "—"}</td>
              <td>
                <input type="password" class="form-input" style="width:120px;font-size:11px;padding:3px 6px;"
                  placeholder="API-Key" data-provider-id="${p.provider_id}" data-field="api_key"
                  value="${p.has_key ? '••••••••' : ''}">
                <button class="btn-icon-sm" style="margin-left:4px;" onclick="saveProviderKey('${p.provider_id}', this)"
                  title="Speichern">💾</button>
              </td>
              <td>
                <input type="checkbox" ${p.enabled ? "checked" : ""}
                  onchange="toggleProvider('${p.provider_id}', this.checked)">
              </td>
            </tr>`;
          }).join("")}</tbody></table>`;

          // Global functions for inline handlers
          window.saveProviderKey = async (id, btn) => {
            const input = btn.previousElementSibling;
            const key = input.value.trim();
            if (!key || key === "••••••••") return;
            try {
              await fetch(\`\${cfg.MEETING_API_BASE}/providers/\${id}\`, {
                method: "PUT",
                headers: { "Content-Type": "application/json", "Authorization": \`Bearer \${token}\` },
                body: JSON.stringify({ api_key: key }),
              });
              if (typeof toast !== "undefined") toast.success("API-Key gespeichert");
              input.value = "••••••••";
            } catch (e) { if (typeof toast !== "undefined") toast.error("Fehler"); }
          };

          window.toggleProvider = async (id, enabled) => {
            try {
              await fetch(\`\${cfg.MEETING_API_BASE}/providers/\${id}\`, {
                method: "PUT",
                headers: { "Content-Type": "application/json", "Authorization": \`Bearer \${token}\` },
                body: JSON.stringify({ enabled }),
              });
              if (typeof toast !== "undefined") toast.success(enabled ? "Provider aktiviert" : "Provider deaktiviert");
            } catch (e) { if (typeof toast !== "undefined") toast.error("Fehler"); }
          };
        }

        // Load routes
        const routeRes = await fetch(`${cfg.MEETING_API_BASE}/providers/routes`, {
          headers: { "Authorization": `Bearer ${token}` },
        });
        if (!routeRes.ok) return;
        const routes = await routeRes.json();

        const routeList = document.getElementById("routeList");
        if (routeList) {
          const statusDot = { green: "🟢", yellow: "🟡", red: "🔴" };
          routeList.innerHTML = routes.map(r => {
            const pH = r.primary?.health || {};
            const bH = r.backup?.health || {};
            return `<div style="display:flex;gap:12px;align-items:center;padding:6px 0;border-bottom:1px solid var(--lx-border-light);font-size:12px;">
              <span style="font-weight:600;width:60px;">${r.source_lang.toUpperCase()} → ${r.target_lang.toUpperCase()}</span>
              <span>Primary: ${statusDot[pH.status] || "⚪"} ${r.primary?.name || "?"}</span>
              <span>Backup: ${statusDot[bH.status] || "⚪"} ${r.backup?.name || "?"}</span>
            </div>`;
          }).join("");
        }
      } catch (e) { /* silent */ }
    })();
  }
})();
