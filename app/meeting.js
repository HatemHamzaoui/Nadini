/**
 * Nadini — Meeting Room Logic
 * Demo-Simulation: Transkript, Audio-Visualizer, Timer, Controls
 */
(function () {
  "use strict";

  // ── Service Worker ──
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("../sw.js").catch(() => {});
  }

  // ── Config ──
  const cfg = typeof NADINI_CONFIG !== "undefined" ? NADINI_CONFIG : { API_MODE: "demo" };
  const isLive = cfg.API_MODE === "live";
  const params = new URLSearchParams(window.location.search);
  const meetingId = params.get("id");
  let ws = null;

  // ── Timer ──
  let seconds = 0;
  const timerEl = document.getElementById("meetingTimer");
  setInterval(() => {
    seconds++;
    const m = String(Math.floor(seconds / 60)).padStart(2, "0");
    const s = String(seconds % 60).padStart(2, "0");
    timerEl.textContent = `${m}:${s}`;
  }, 1000);

  // ── Audio Visualizer (simulated) ──
  const bars = document.querySelectorAll(".audio-bar");
  let micActive = true;
  const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function animateBars() {
    if (prefersReducedMotion) { bars.forEach(b => b.style.height = "12px"); return; }
    bars.forEach(bar => {
      const h = micActive ? Math.random() * 28 + 4 : 4;
      bar.style.height = h + "px";
    });
    requestAnimationFrame(() => setTimeout(animateBars, 80));
  }
  animateBars();

  // ── Mic Toggle ──
  const micMainBtn = document.getElementById("micMainBtn");
  const micBtn = document.getElementById("micBtn");

  function toggleMic() {
    micActive = !micActive;
    [micMainBtn, micBtn].forEach(btn => {
      if (btn) btn.classList.toggle("active", micActive);
    });
    // Send status to WebSocket
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "status_update", status: micActive ? "speaking" : "muted" }));
    }
    if (micMainBtn) {
      micMainBtn.querySelector(".mic-on").classList.toggle("hidden", !micActive);
      micMainBtn.querySelector(".mic-off").classList.toggle("hidden", micActive);
    }
  }
  if (micMainBtn) micMainBtn.addEventListener("click", toggleMic);
  if (micBtn) micBtn.addEventListener("click", toggleMic);

  // ── Channel Selection ──
  document.querySelectorAll(".channel-item").forEach(ch => {
    ch.addEventListener("click", () => {
      document.querySelectorAll(".channel-item").forEach(c => c.classList.remove("channel-active"));
      ch.classList.add("channel-active");
    });
  });

  // ── End Meeting ──
  const endBtn = document.getElementById("endBtn");
  const endMeetingBtn = document.getElementById("endMeetingBtn");
  async function endMeeting() {
    if (!confirm("Meeting beenden?")) return;
    if (isLive && meetingId) {
      try {
        const token = localStorage.getItem("nadini-access-token");
        await fetch(`${cfg.MEETING_API_BASE}/meetings/${meetingId}/end`, {
          method: "POST",
          headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
          body: "{}",
        });
      } catch (e) { /* proceed anyway */ }
    }
    if (ws) ws.close();
    window.location.href = "dashboard.html";
  }
  if (endBtn) endBtn.addEventListener("click", endMeeting);
  if (endMeetingBtn) endMeetingBtn.addEventListener("click", endMeeting);

  // ── Captions Toggle ──
  const captionBtn = document.getElementById("captionBtn");
  const captionsOverlay = document.getElementById("captionsOverlay");
  let captionsOn = false;

  if (captionBtn && captionsOverlay) {
    captionBtn.addEventListener("click", () => {
      captionsOn = !captionsOn;
      captionsOverlay.classList.toggle("hidden", !captionsOn);
      captionBtn.classList.toggle("ctrl-btn-active", captionsOn);
    });
  }

  function updateCaptions(entry) {
    if (!captionsOn || !captionsOverlay) return;
    const origText = captionsOverlay.querySelector("#captionOriginal .caption-text");
    const origLang = captionsOverlay.querySelector("#captionOriginal .caption-lang");
    const transText = captionsOverlay.querySelector("#captionTranslated .caption-text");
    const transLang = captionsOverlay.querySelector("#captionTranslated .caption-lang");

    origLang.textContent = entry.lang;
    origText.textContent = entry.text;

    if (entry.translations && entry.translations.length > 0) {
      const t = entry.translations[0];
      transLang.textContent = t.flag === "🇬🇧" ? "EN" : t.flag === "🇫🇷" ? "FR" : t.flag === "🇩🇪" ? "DE" : "AI";
      transText.textContent = t.text;
      document.getElementById("captionTranslated").style.display = "";
    } else {
      document.getElementById("captionTranslated").style.display = "none";
    }
  }

  // ── Theme ──
  const savedTheme = localStorage.getItem("nadini-theme");
  if (savedTheme) document.documentElement.dataset.theme = savedTheme;

  // ── Demo Transcript ──
  const container = document.getElementById("transcriptContainer");
  let autoScroll = true;

  const demoTranscript = [
    {
      speaker: "Alice",
      time: "00:05",
      lang: "DE",
      text: "Guten Morgen zusammen! Können wir mit dem Product Review starten?",
      translations: [
        { flag: "🇬🇧", text: "Good morning everyone! Can we start with the product review?" },
        { flag: "🇫🇷", text: "Bonjour à tous ! On peut commencer la revue produit ?" },
      ],
    },
    {
      speaker: "Bob",
      time: "00:12",
      lang: "EN",
      text: "Sure, I've prepared the Q2 metrics. Let me share my screen.",
      translations: [
        { flag: "🇩🇪", text: "Klar, ich habe die Q2-Kennzahlen vorbereitet. Lass mich meinen Bildschirm teilen." },
        { flag: "🇫🇷", text: "Bien sûr, j'ai préparé les métriques du T2. Je partage mon écran." },
      ],
    },
    {
      speaker: "Claire",
      time: "00:25",
      lang: "FR",
      text: "Parfait. J'aimerais aussi aborder la question du nouveau marché DACH.",
      translations: [
        { flag: "🇩🇪", text: "Perfekt. Ich möchte auch die Frage des neuen DACH-Marktes ansprechen." },
        { flag: "🇬🇧", text: "Perfect. I'd also like to address the question of the new DACH market." },
      ],
    },
    {
      speaker: "Alice",
      time: "00:38",
      lang: "DE",
      text: "Guter Punkt, Claire. Die Expansion nach Österreich und Schweiz ist für Q3 geplant.",
      translations: [
        { flag: "🇬🇧", text: "Good point, Claire. The expansion to Austria and Switzerland is planned for Q3." },
        { flag: "🇫🇷", text: "Bon point, Claire. L'expansion vers l'Autriche et la Suisse est prévue pour le T3." },
      ],
    },
    {
      speaker: "Bob",
      time: "00:52",
      lang: "EN",
      text: "The conversion rate improved by 18% since we launched the real-time translation feature.",
      translations: [
        { flag: "🇩🇪", text: "Die Conversion-Rate hat sich seit dem Launch der Echtzeit-Übersetzung um 18% verbessert." },
        { flag: "🇫🇷", text: "Le taux de conversion a augmenté de 18% depuis le lancement de la traduction en temps réel." },
      ],
    },
    {
      speaker: "Claire",
      time: "01:08",
      lang: "FR",
      text: "Impressionnant ! Est-ce que les clients francophones ont donné des retours spécifiques ?",
      translations: [
        { flag: "🇩🇪", text: "Beeindruckend! Haben die französischsprachigen Kunden spezifisches Feedback gegeben?" },
        { flag: "🇬🇧", text: "Impressive! Have the French-speaking customers given specific feedback?" },
      ],
    },
    {
      speaker: "Alice",
      time: "01:22",
      lang: "DE",
      text: "Ja, besonders die niedrige Latenz wird gelobt. Unter 200 Millisekunden ist ein Gamechanger.",
      translations: [
        { flag: "🇬🇧", text: "Yes, the low latency is especially praised. Under 200 milliseconds is a game changer." },
        { flag: "🇫🇷", text: "Oui, la faible latence est particulièrement saluée. Moins de 200 millisecondes, c'est un changement majeur." },
      ],
    },
    {
      speaker: "Daisuke",
      time: "01:40",
      lang: "EN",
      text: "I can confirm that from the Japan market — our clients there are very happy with the quality.",
      translations: [
        { flag: "🇩🇪", text: "Das kann ich vom japanischen Markt bestätigen — unsere Kunden dort sind sehr zufrieden mit der Qualität." },
        { flag: "🇫🇷", text: "Je confirme depuis le marché japonais — nos clients là-bas sont très satisfaits de la qualité." },
      ],
    },
  ];

  function createTranscriptEntry(entry) {
    const el = document.createElement("div");
    el.className = "transcript-entry";

    const isOriginal = entry.lang === "DE";
    const langTag = isOriginal ? "Original" : "AI";
    const tagClass = isOriginal ? "tag-original" : "tag-translated";

    let translationsHTML = "";
    if (entry.translations && entry.translations.length > 0) {
      translationsHTML = `
        <div class="transcript-translations">
          ${entry.translations.map(t => `
            <div class="transcript-translation">
              <span class="translation-flag">${t.flag}</span>
              <span class="translation-text">${t.text}</span>
            </div>
          `).join("")}
        </div>
      `;
    }

    el.innerHTML = `
      <div class="transcript-header">
        <span class="transcript-speaker">${entry.speaker}</span>
        <span class="transcript-time">${entry.time}</span>
        <span class="transcript-lang-tag ${tagClass}">${entry.lang} · ${langTag}</span>
      </div>
      <p class="transcript-text">${entry.text}</p>
      ${translationsHTML}
    `;

    return el;
  }

  // Show typing indicator
  function showTyping() {
    const el = document.createElement("div");
    el.className = "transcript-typing";
    el.id = "typingIndicator";
    el.innerHTML = '<span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span>';
    container.appendChild(el);
    if (autoScroll) container.scrollTop = container.scrollHeight;
  }

  function removeTyping() {
    const el = document.getElementById("typingIndicator");
    if (el) el.remove();
  }

  // Stream entries with delay
  let entryIndex = 0;
  function streamNextEntry() {
    if (entryIndex >= demoTranscript.length) {
      // Loop back after a pause
      setTimeout(() => {
        entryIndex = 0;
        seconds = 0;
        container.innerHTML = "";
        streamNextEntry();
      }, 5000);
      return;
    }

    showTyping();

    setTimeout(() => {
      removeTyping();
      const entry = demoTranscript[entryIndex];
      container.appendChild(createTranscriptEntry(entry));
      updateCaptions(entry);
      if (autoScroll) container.scrollTop = container.scrollHeight;
      entryIndex++;
      streamNextEntry();
    }, 1800 + Math.random() * 2000);
  }

  // ── WebSocket Client (Live Mode) ──
  if (isLive && meetingId && cfg.WS_BASE) {
    const token = localStorage.getItem("nadini-access-token");
    const wsUrl = `${cfg.WS_BASE}/meetings/${meetingId}/ws?token=${encodeURIComponent(token)}`;

    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      if (typeof toast !== "undefined") toast.info("Verbunden");
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);

        if (msg.type === "transcript") {
          container.appendChild(createTranscriptEntry(msg));
          updateCaptions(msg);
          if (autoScroll) container.scrollTop = container.scrollHeight;
        } else if (msg.type === "participant_joined") {
          if (typeof toast !== "undefined") toast.info(`${msg.name} beigetreten`);
        } else if (msg.type === "participant_left") {
          if (typeof toast !== "undefined") toast.info(`${msg.name} hat verlassen`);
        } else if (msg.type === "meeting_ended") {
          if (typeof toast !== "undefined") toast.info("Meeting beendet");
          setTimeout(() => { window.location.href = "dashboard.html"; }, 2000);
        }
      } catch (e) { /* ignore parse errors */ }
    };

    ws.onclose = () => {
      if (typeof toast !== "undefined") toast.error("Verbindung getrennt");
    };

    // Send status updates on mic toggle
    const origToggleMic = toggleMic;
    // Mic status is sent via ws in the keyboard shortcuts section

    // Ping keepalive
    setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "ping" }));
      }
    }, 25000);
  } else {
    // Demo mode: start streaming hardcoded transcript
    setTimeout(streamNextEntry, 1000);
  }

  // Auto-scroll toggle
  const autoScrollBtn = document.getElementById("autoScrollBtn");
  if (autoScrollBtn) {
    autoScrollBtn.addEventListener("click", () => {
      autoScroll = !autoScroll;
      autoScrollBtn.style.color = autoScroll ? "var(--lx-gold)" : "";
      autoScrollBtn.style.borderColor = autoScroll ? "var(--lx-gold-border)" : "";
    });
  }

  // ── Download Transcript ──
  const downloadBtn = document.getElementById("downloadBtn");
  if (downloadBtn) {
    downloadBtn.addEventListener("click", () => {
      const lines = ["═══ NADINI — Live-Transkript ═══\n"];
      container.querySelectorAll(".transcript-entry").forEach(entry => {
        const speaker = entry.querySelector(".transcript-speaker")?.textContent || "";
        const time = entry.querySelector(".transcript-time")?.textContent || "";
        const text = entry.querySelector(".transcript-text")?.textContent || "";
        lines.push(`[${time}] ${speaker}: ${text}`);
        entry.querySelectorAll(".transcript-translation").forEach(t => {
          const flag = t.querySelector(".translation-flag")?.textContent || "";
          const tText = t.querySelector(".translation-text")?.textContent || "";
          lines.push(`  ${flag} ${tText}`);
        });
        lines.push("");
      });
      lines.push("── Exportiert von Nadini — nadini.ai ──");

      const blob = new Blob([lines.join("\n")], { type: "text/plain;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "nadini-live-transkript.txt";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      if (typeof toast !== "undefined") toast.success("Transkript heruntergeladen");
    });
  }

  // ── Keyboard Shortcuts ──
  document.addEventListener("keydown", (e) => {
    // Don't trigger when typing in inputs
    if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA" || e.target.tagName === "SELECT") return;

    switch (e.key.toLowerCase()) {
      case "m": // Toggle mic
        e.preventDefault();
        toggleMic();
        break;
      case "c": // Toggle captions
        e.preventDefault();
        if (captionBtn) captionBtn.click();
        break;
      case "d": // Download transcript
        e.preventDefault();
        if (downloadBtn) downloadBtn.click();
        break;
      case "i": // Open invite
        e.preventDefault();
        if (document.getElementById("inviteModal")) {
          document.getElementById("inviteModal").classList.remove("hidden");
        }
        break;
      case "escape": // Close modals
        if (document.getElementById("inviteModal")) {
          document.getElementById("inviteModal").classList.add("hidden");
        }
        break;
    }
  });

  // ── Invite Modal ──
  const inviteBtn = document.getElementById("inviteBtn");
  const inviteModal = document.getElementById("inviteModal");
  const inviteClose = document.getElementById("inviteClose");
  const copyLinkBtn = document.getElementById("copyLinkBtn");
  const sendInviteBtn = document.getElementById("sendInviteBtn");

  if (inviteBtn && inviteModal) {
    inviteBtn.addEventListener("click", () => inviteModal.classList.remove("hidden"));
    inviteClose.addEventListener("click", () => inviteModal.classList.add("hidden"));
    inviteModal.addEventListener("click", (e) => {
      if (e.target === inviteModal) inviteModal.classList.add("hidden");
    });

    // Copy link
    copyLinkBtn.addEventListener("click", () => {
      const input = document.getElementById("inviteLinkInput");
      navigator.clipboard.writeText(input.value).catch(() => {});
      if (typeof toast !== "undefined") toast.success("Meeting-Link kopiert");
    });

    // Send invite (demo)
    sendInviteBtn.addEventListener("click", () => {
      const emails = document.getElementById("inviteEmails").value.trim();
      if (!emails) return;
      sendInviteBtn.disabled = true;
      setTimeout(() => { sendInviteBtn.disabled = false; }, 800);
      document.getElementById("inviteEmails").value = "";
      if (typeof toast !== "undefined") toast.success("Einladung gesendet");
    });
  }
})();
