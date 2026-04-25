/**
 * Nadini Landing Page — Interaktivität
 */
(function () {
  "use strict";

  // ── Language Switcher ──
  document.querySelectorAll(".lang-btn").forEach(btn => {
    btn.addEventListener("click", () => setLanguage(btn.dataset.lang));
  });

  // ── Theme Toggle ──
  const toggle = document.getElementById("themeToggle");
  const saved = localStorage.getItem("nadini-theme");
  if (saved) document.documentElement.dataset.theme = saved;

  toggle.addEventListener("click", () => {
    const current = document.documentElement.dataset.theme || "dark";
    const next = current === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    localStorage.setItem("nadini-theme", next);
  });

  // ── Mobile Nav ──
  const hamburger = document.getElementById("navHamburger");
  const navLinks = document.getElementById("navLinks");

  hamburger.addEventListener("click", () => {
    navLinks.classList.toggle("open");
  });

  // Close mobile nav on link click
  navLinks.querySelectorAll("a").forEach(link => {
    link.addEventListener("click", () => navLinks.classList.remove("open"));
  });

  // ── CTA Form ──
  const form = document.getElementById("ctaForm");
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const email = form.querySelector(".cta-input").value;
    if (!email) return;

    const btn = form.querySelector("button");
    btn.textContent = "✓";
    btn.style.background = "var(--lx-green)";
    btn.disabled = true;

    // Redirect to login with email pre-filled
    setTimeout(() => {
      window.location.href = "../app/login.html?email=" + encodeURIComponent(email);
    }, 800);
  });

  // ── Navbar scroll effect ──
  const nav = document.querySelector(".nav");
  let ticking = false;

  window.addEventListener("scroll", () => {
    if (!ticking) {
      requestAnimationFrame(() => {
        nav.style.borderBottomColor = window.scrollY > 20
          ? "var(--lx-border)"
          : "var(--lx-border-light)";
        ticking = false;
      });
      ticking = true;
    }
  });

  // ── Smooth reveal on scroll ──
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.style.opacity = "1";
        entry.target.style.transform = "translateY(0)";
      }
    });
  }, { threshold: 0.1 });

  document.querySelectorAll(".feature-card, .compliance-card, .pricing-card, .step").forEach(el => {
    el.style.opacity = "0";
    el.style.transform = "translateY(20px)";
    el.style.transition = "opacity 0.5s ease, transform 0.5s ease";
    observer.observe(el);
  });
})();
