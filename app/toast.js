/**
 * Nadini — Toast Notification System
 * Usage: toast.success("Gespeichert"), toast.error("Fehler"), toast.info("Hinweis")
 */
const toast = (function () {
  "use strict";

  let container = null;

  function getContainer() {
    if (container) return container;
    container = document.createElement("div");
    container.className = "toast-container";
    container.setAttribute("aria-live", "polite");
    container.setAttribute("role", "status");
    document.body.appendChild(container);
    return container;
  }

  function show(message, type, duration) {
    const el = document.createElement("div");
    el.className = `toast toast-${type}`;
    el.innerHTML = `
      <span class="toast-icon">${type === "success" ? "&#10003;" : type === "error" ? "&#10007;" : "&#8505;"}</span>
      <span class="toast-message">${message}</span>
      <button class="toast-dismiss" aria-label="Schließen">&times;</button>
    `;

    el.querySelector(".toast-dismiss").addEventListener("click", () => dismiss(el));
    getContainer().appendChild(el);

    // Trigger animation
    requestAnimationFrame(() => el.classList.add("toast-visible"));

    // Auto dismiss
    const timer = setTimeout(() => dismiss(el), duration);
    el._timer = timer;

    return el;
  }

  function dismiss(el) {
    if (!el || !el.parentNode) return;
    clearTimeout(el._timer);
    el.classList.remove("toast-visible");
    el.classList.add("toast-exit");
    el.addEventListener("animationend", () => el.remove(), { once: true });
    // Fallback removal
    setTimeout(() => { if (el.parentNode) el.remove(); }, 400);
  }

  return {
    success: (msg, ms) => show(msg, "success", ms || 3000),
    error: (msg, ms) => show(msg, "error", ms || 4000),
    info: (msg, ms) => show(msg, "info", ms || 3000),
  };
})();
