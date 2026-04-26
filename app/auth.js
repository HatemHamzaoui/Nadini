/**
 * Nadini — Auth Logic (Magic Link Flow)
 *
 * Uses NADINI_CONFIG (from config.js) to decide between demo and live mode.
 * Live mode: API calls via Nginx proxy (/auth/*) or direct to auth-service.
 * Demo mode: Simulated responses, no backend required.
 */
(function () {
  "use strict";

  // ── Service Worker ──
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("../sw.js").catch(() => {});
  }

  const cfg = typeof NADINI_CONFIG !== "undefined" ? NADINI_CONFIG : { API_MODE: "demo", AUTH_API_BASE: "" };
  const isLive = cfg.API_MODE === "live";
  const apiBase = cfg.AUTH_API_BASE;
  const params = new URLSearchParams(window.location.search);

  // ── API Helper ──
  async function apiPost(path, body) {
    const res = await fetch(`${apiBase}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok && res.status !== 202) {
      const err = new Error(`API ${res.status}`);
      err.status = res.status;
      throw err;
    }
    if (res.status === 204 || res.status === 202) return {};
    return res.json();
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

  // ── Login Page Logic ──
  const emailForm = document.getElementById("emailForm");
  if (emailForm) {
    const stepEmail = document.getElementById("stepEmail");
    const stepInbox = document.getElementById("stepInbox");
    const stepVerify = document.getElementById("stepVerify");
    const stepError = document.getElementById("stepError");
    const sentEmail = document.getElementById("sentEmail");
    const emailInput = document.getElementById("email");
    const emailSubmit = document.getElementById("emailSubmit");
    const emailError = document.getElementById("emailError");
    const resendBtn = document.getElementById("resendBtn");
    const resendTimer = document.getElementById("resendTimer");
    const changeEmail = document.getElementById("changeEmail");
    const retryBtn = document.getElementById("retryBtn");
    const demoBtn = document.getElementById("demoBtn");

    function showStep(step) {
      [stepEmail, stepInbox, stepVerify, stepError].forEach(s => s.classList.add("hidden"));
      step.classList.remove("hidden");
    }

    // Pre-fill email from URL (coming from landing page CTA)
    const prefillEmail = params.get("email");
    if (prefillEmail && emailInput) {
      emailInput.value = prefillEmail;
    }

    // Submit email → request magic link
    emailForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const email = emailInput.value.trim();
      if (!email) return;

      emailSubmit.disabled = true;
      emailError.classList.add("hidden");

      try {
        if (isLive) {
          await apiPost("/auth/magic-link", { email, ui_language: document.documentElement.lang });
        } else {
          await new Promise(r => setTimeout(r, 800));
        }

        sentEmail.textContent = email;
        showStep(stepInbox);
        startResendCountdown();
      } catch (err) {
        if (err.status === 429) {
          emailError.textContent = "Zu viele Anfragen. Bitte warten Sie einen Moment.";
        } else {
          emailError.textContent = "Fehler beim Senden. Bitte versuchen Sie es erneut.";
        }
        emailError.classList.remove("hidden");
      } finally {
        emailSubmit.disabled = false;
      }
    });

    // Resend countdown
    function startResendCountdown() {
      let seconds = 60;
      resendBtn.disabled = true;
      resendTimer.textContent = `(${seconds}s)`;

      const interval = setInterval(() => {
        seconds--;
        resendTimer.textContent = `(${seconds}s)`;
        if (seconds <= 0) {
          clearInterval(interval);
          resendBtn.disabled = false;
          resendTimer.textContent = "";
        }
      }, 1000);
    }

    // Resend
    resendBtn.addEventListener("click", async () => {
      resendBtn.disabled = true;
      const email = sentEmail.textContent;
      try {
        if (isLive) {
          await apiPost("/auth/magic-link", { email, ui_language: document.documentElement.lang });
        } else {
          await new Promise(r => setTimeout(r, 500));
        }
        startResendCountdown();
      } catch (err) {
        resendBtn.disabled = false;
      }
    });

    // Change email
    changeEmail.addEventListener("click", () => {
      showStep(stepEmail);
      emailInput.focus();
    });

    // Retry
    retryBtn.addEventListener("click", () => {
      showStep(stepEmail);
      emailInput.focus();
    });

    // Demo mode button — skip auth, go straight to app
    if (demoBtn) {
      demoBtn.addEventListener("click", () => {
        const email = emailInput.value.trim() || "demo@nadini.ai";
        demoBtn.disabled = true;
        demoBtn.textContent = "…";

        localStorage.setItem("nadini-access-token", "demo-access-token");
        localStorage.setItem("nadini-refresh-token", "demo-refresh-token");
        localStorage.setItem("nadini-user-email", email);

        setTimeout(() => {
          if (!localStorage.getItem("nadini-disclosure-ack")) {
            window.location.href = "disclosure.html";
          } else {
            window.location.href = "dashboard.html";
          }
        }, 500);
      });
    }

    // Auto-start demo if ?demo=1
    if (params.get("demo") === "1" && demoBtn) {
      setTimeout(() => demoBtn.click(), 300);
    }

    // Check for magic link token in URL (verification step)
    const token = params.get("token");
    if (token) {
      showStep(stepVerify);
      verifyMagicLink(token);
    }

    async function verifyMagicLink(token) {
      try {
        if (isLive) {
          const data = await apiPost("/auth/verify-magic", { token });

          localStorage.setItem("nadini-access-token", data.access_token);
          localStorage.setItem("nadini-refresh-token", data.refresh_token);
          localStorage.setItem("nadini-user-email", data.user?.email || "");
          localStorage.setItem("nadini-user-role", data.user?.role || "user");

          if (data.compliance?.ai_disclosure_required) {
            window.location.href = "disclosure.html";
          } else {
            localStorage.setItem("nadini-disclosure-ack", data.compliance?.ai_disclosure_version || "done");
            window.location.href = "dashboard.html";
          }
        } else {
          // Demo: simulate verification
          await new Promise(r => setTimeout(r, 1200));

          localStorage.setItem("nadini-access-token", "demo-access-token");
          localStorage.setItem("nadini-refresh-token", "demo-refresh-token");
          localStorage.setItem("nadini-user-email", "alice@example.com");

          if (!localStorage.getItem("nadini-disclosure-ack")) {
            window.location.href = "disclosure.html";
          } else {
            window.location.href = "dashboard.html";
          }
        }
      } catch (err) {
        showStep(stepError);
      }
    }
  }
})();
