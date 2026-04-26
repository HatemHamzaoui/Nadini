/**
 * Nadini — Shared logic for sidebar pages (Transcripts, Meetings, Settings)
 */
(function () {
  "use strict";

  // ── Service Worker ──
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("../sw.js").catch(() => {});
  }

  // ── Auth Guard ──
  if (!localStorage.getItem("nadini-access-token")) {
    window.location.href = "login.html";
    return;
  }

  // ── User Info + Role ──
  const email = localStorage.getItem("nadini-user-email") || "user@example.com";
  const userRole = localStorage.getItem("nadini-user-role") || "user";
  const avatarEl = document.getElementById("userAvatar");
  const emailEl = document.getElementById("userEmail");
  const roleEl = document.querySelector(".user-role");
  if (emailEl) emailEl.textContent = email;
  if (avatarEl) avatarEl.textContent = email.charAt(0).toUpperCase();

  // Display dynamic role
  const roleLabels = { admin: "🛡️ Admin", tenant_admin: "🏢 Tenant Admin", moderator: "👑 Moderator", interpreter: "🎙️ Dolmetscher", user: "Benutzer", guest: "Gast" };
  if (roleEl) roleEl.textContent = roleLabels[userRole] || userRole;

  // Hide admin-only elements for non-admins
  document.querySelectorAll("[data-require-role]").forEach(el => {
    const requiredRole = el.dataset.requireRole;
    const allowed = requiredRole === "admin" ? userRole === "admin"
      : requiredRole === "tenant_admin" ? ["admin", "tenant_admin"].includes(userRole)
      : requiredRole === "moderator" ? ["admin", "tenant_admin", "moderator"].includes(userRole)
      : true;
    if (!allowed) el.style.display = "none";
  });

  // ── Theme ──
  const themeToggle = document.getElementById("themeToggle");
  const savedTheme = localStorage.getItem("nadini-theme");
  if (savedTheme) document.documentElement.dataset.theme = savedTheme;
  if (themeToggle) {
    themeToggle.addEventListener("click", () => {
      const next = (document.documentElement.dataset.theme || "dark") === "dark" ? "light" : "dark";
      document.documentElement.dataset.theme = next;
      localStorage.setItem("nadini-theme", next);
    });
  }

  // ── Sidebar Toggle (Mobile) ──
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

  // ── Filter Chips ──
  document.querySelectorAll(".filter-chip").forEach(chip => {
    chip.addEventListener("click", () => {
      document.querySelectorAll(".filter-chip").forEach(c => c.classList.remove("filter-active"));
      chip.classList.add("filter-active");
    });
  });

  // ── Search (demo filter) ──
  const searchInput = document.getElementById("searchInput");
  if (searchInput) {
    searchInput.addEventListener("input", () => {
      const q = searchInput.value.toLowerCase();
      document.querySelectorAll(".transcript-card").forEach(card => {
        const text = card.textContent.toLowerCase();
        card.style.display = text.includes(q) ? "" : "none";
      });
    });
  }
})();
