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

  // ── Audio Capture (real mic + ASR) ──
  const bars = document.querySelectorAll(".audio-bar");
  let micActive = true;
  const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const meetingLang = params.get("lang") || localStorage.getItem("nadini-meeting-lang") || "de";
  let audioReady = false;

  // Initialize real audio capture
  if (typeof AudioCapture !== "undefined" && AudioCapture.isSupported().visualizer) {
    AudioCapture.init({ lang: meetingLang }).then((status) => {
      audioReady = true;

      // Show ASR badge
      const asrBadge = document.getElementById("asrBadge");
      if (asrBadge && status.hasASR) {
        asrBadge.classList.remove("hidden");
      }

      // Real visualizer data → bars
      AudioCapture.onVisualizerData((freqData) => {
        if (prefersReducedMotion) return;
        const binCount = Math.min(freqData.length, bars.length);
        for (let i = 0; i < bars.length; i++) {
          const val = i < binCount ? freqData[i] : 0;
          bars[i].style.height = Math.max(4, (val / 255) * 32) + "px";
        }
      });

      // Speech recognition results → WebSocket or local transcript
      AudioCapture.onResult(({ text, lang, isFinal, confidence }) => {
        // Update interim captions
        if (captionsOn && captionsOverlay) {
          const origText = captionsOverlay.querySelector("#captionOriginal .caption-text");
          const origLang = captionsOverlay.querySelector("#captionOriginal .caption-lang");
          if (origText && origLang) {
            origLang.textContent = lang.toUpperCase();
            origText.textContent = text;
            document.getElementById("captionOriginal").classList.toggle("caption-interim", !isFinal);
          }
        }

        // On final result → send transcript
        if (isFinal && text.trim()) {
          const entry = {
            type: "transcript_submit",
            text: text.trim(),
            lang: lang,
            translations: [],
          };

          if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify(entry));
          } else {
            // Demo mode: render locally
            const fakeEntry = {
              speaker: localStorage.getItem("nadini-user-email")?.split("@")[0] || "Du",
              time: timerEl.textContent,
              lang: lang.toUpperCase(),
              text: text.trim(),
              translations: [],
            };
            container.appendChild(createTranscriptEntry(fakeEntry));
            setSpeaker(fakeEntry.speaker);
            if (autoScroll) container.scrollTop = container.scrollHeight;
          }
        }
      });

      // Start with mic active
      AudioCapture.start();

      if (typeof toast !== "undefined" && status.hasASR) {
        toast.info("Spracherkennung aktiv");
      } else if (typeof toast !== "undefined" && !status.hasASR) {
        toast.info("Spracherkennung nicht verfügbar — Demo-Modus");
      }
    }).catch(() => {
      // Fallback: simulated bars
      startSimulatedBars();
    });
  } else {
    startSimulatedBars();
  }

  // Simulated bars fallback
  function startSimulatedBars() {
    function animateBars() {
      if (prefersReducedMotion) { bars.forEach(b => b.style.height = "12px"); return; }
      bars.forEach(bar => {
        const h = micActive ? Math.random() * 28 + 4 : 4;
        bar.style.height = h + "px";
      });
      requestAnimationFrame(() => setTimeout(animateBars, 80));
    }
    animateBars();
  }

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
    // Toggle real audio capture
    if (audioReady && typeof AudioCapture !== "undefined") {
      if (micActive) AudioCapture.start();
      else AudioCapture.stop();
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
    if (isRecording) stopRecording();
    if (camActive) toggleCam();
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
      setSpeaker(entry.speaker);
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
          setSpeaker(msg.speaker);
          if (autoScroll) container.scrollTop = container.scrollHeight;
        } else if (msg.type === "participant_joined") {
          if (typeof toast !== "undefined") toast.info(`${msg.name} beigetreten`);
        } else if (msg.type === "participant_left") {
          if (typeof toast !== "undefined") toast.info(`${msg.name} hat verlassen`);
        } else if (msg.type === "notes_update") {
          handleNotesUpdate(msg);
        } else if (msg.type === "reaction") {
          handleReaction(msg);
        } else if (msg.type === "chat") {
          handleChatMessage(msg);
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

  // ── Chat ──
  const chatForm = document.getElementById("chatForm");
  const chatInput = document.getElementById("chatInput");
  const chatMessages = document.getElementById("chatMessages");
  const chatUnread = document.getElementById("chatUnread");
  const myName = localStorage.getItem("nadini-user-email")?.split("@")[0] || "Du";
  let unreadCount = 0;

  function addChatMessage(name, text, time, isOwn) {
    const el = document.createElement("div");
    el.className = `chat-msg${isOwn ? " chat-msg-own" : ""}`;
    el.innerHTML = `
      <div class="chat-msg-header">
        <span class="chat-msg-name">${name}</span>
        <span class="chat-msg-time">${time}</span>
      </div>
      <div class="chat-msg-text">${text.replace(/</g, "&lt;").replace(/>/g, "&gt;")}</div>
    `;
    chatMessages.appendChild(el);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  if (chatForm) {
    chatForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const text = chatInput.value.trim();
      if (!text) return;

      const time = timerEl.textContent;

      // Send via WebSocket
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "chat", text, name: myName }));
      }

      // Show locally
      addChatMessage(myName, text, time, true);
      chatInput.value = "";
    });
  }

  // Handle incoming chat (added to WS message handler below)
  function handleChatMessage(msg) {
    const time = timerEl.textContent;
    addChatMessage(msg.name || "?", msg.text || "", time, false);

    // Unread badge
    unreadCount++;
    if (chatUnread) {
      chatUnread.textContent = unreadCount;
      chatUnread.classList.remove("hidden");
    }
  }

  // Clear unread when chat is visible
  if (chatMessages) {
    chatMessages.addEventListener("click", () => {
      unreadCount = 0;
      if (chatUnread) chatUnread.classList.add("hidden");
    });
  }

  // ── Speaker Highlighting + Speaking Time ──
  const speakStatsBars = document.getElementById("speakStatsBars");
  const speakTimes = {}; // {name: seconds}
  let currentSpeaker = null;
  let speakerInterval = null;

  const speakerColors = ["var(--lx-gold)", "var(--lx-blue)", "var(--lx-green)", "var(--lx-purple)", "var(--lx-red)"];
  let colorIndex = 0;
  const speakerColorMap = {};

  function getSpeakerColor(name) {
    if (!speakerColorMap[name]) {
      speakerColorMap[name] = speakerColors[colorIndex % speakerColors.length];
      colorIndex++;
    }
    return speakerColorMap[name];
  }

  function setSpeaker(name) {
    if (currentSpeaker === name) return;
    currentSpeaker = name;

    // Highlight participant in list
    document.querySelectorAll(".participant-item").forEach(el => {
      const nameEl = el.querySelector(".participant-name");
      el.classList.toggle("speaking", nameEl && nameEl.textContent.includes(name));
    });

    // Highlight latest transcript entry
    document.querySelectorAll(".transcript-entry").forEach(el => el.classList.remove("highlight-speaker"));
    const entries = container.querySelectorAll(".transcript-entry");
    if (entries.length > 0) {
      const last = entries[entries.length - 1];
      const speaker = last.querySelector(".transcript-speaker");
      if (speaker && speaker.textContent === name) {
        last.classList.add("highlight-speaker");
      }
    }
  }

  function trackSpeakTime(name) {
    if (!speakTimes[name]) speakTimes[name] = 0;
    speakTimes[name]++;
    updateSpeakStats();
  }

  function updateSpeakStats() {
    if (!speakStatsBars) return;
    const total = Object.values(speakTimes).reduce((a, b) => a + b, 0) || 1;
    const sorted = Object.entries(speakTimes).sort((a, b) => b[1] - a[1]);

    speakStatsBars.innerHTML = sorted.map(([name, secs]) => {
      const pct = Math.round((secs / total) * 100);
      const mins = Math.floor(secs / 60);
      const s = secs % 60;
      const timeStr = mins > 0 ? `${mins}m${String(s).padStart(2, "0")}s` : `${s}s`;
      const color = getSpeakerColor(name);
      return `<div class="speak-stat-row">
        <span class="speak-stat-name">${name}</span>
        <div class="speak-stat-bar-wrap"><div class="speak-stat-bar" style="width:${pct}%;background:${color}"></div></div>
        <span class="speak-stat-time">${timeStr}</span>
      </div>`;
    }).join("");
  }

  // Track speaking time every second when someone is speaking
  speakerInterval = setInterval(() => {
    if (currentSpeaker) trackSpeakTime(currentSpeaker);
  }, 1000);

  // ── Shared Notes ──
  const notesEditor = document.getElementById("notesEditor");
  const notesSaved = document.getElementById("notesSaved");
  const downloadNotesBtn = document.getElementById("downloadNotesBtn");
  let notesTimer = null;
  let isRemoteNoteUpdate = false;

  if (notesEditor) {
    // Load saved notes from localStorage
    const savedNotes = localStorage.getItem(`nadini-notes-${meetingId || "demo"}`);
    if (savedNotes) notesEditor.value = savedNotes;

    // Debounced sync on input
    notesEditor.addEventListener("input", () => {
      if (isRemoteNoteUpdate) return;
      clearTimeout(notesTimer);
      notesTimer = setTimeout(() => {
        const text = notesEditor.value;
        localStorage.setItem(`nadini-notes-${meetingId || "demo"}`, text);

        // Broadcast to other participants
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "notes_update", text }));
        }

        // Show "saved" indicator
        if (notesSaved) {
          notesSaved.classList.add("show");
          notesSaved.classList.remove("hidden");
          setTimeout(() => notesSaved.classList.remove("show"), 1500);
        }
      }, 500);
    });
  }

  function handleNotesUpdate(msg) {
    if (!notesEditor) return;
    isRemoteNoteUpdate = true;
    const cursorPos = notesEditor.selectionStart;
    notesEditor.value = msg.text || "";
    notesEditor.selectionStart = notesEditor.selectionEnd = cursorPos;
    localStorage.setItem(`nadini-notes-${meetingId || "demo"}`, msg.text || "");
    isRemoteNoteUpdate = false;
  }

  // Download notes
  if (downloadNotesBtn && notesEditor) {
    downloadNotesBtn.addEventListener("click", () => {
      const text = notesEditor.value.trim();
      if (!text) { if (typeof toast !== "undefined") toast.info("Keine Notizen vorhanden"); return; }

      const name = document.querySelector(".meeting-room-title")?.textContent || "meeting";
      const blob = new Blob([`Nadini Meeting-Notizen: ${name}\n${"=".repeat(40)}\n\n${text}\n`], { type: "text/plain;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `nadini-notizen-${name.replace(/\s+/g, "-").toLowerCase()}.txt`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      if (typeof toast !== "undefined") toast.success("Notizen exportiert");
    });
  }

  // ── Emoji Reactions ──
  const reactionBubbles = document.getElementById("reactionBubbles");

  function showReactionBubble(emoji) {
    if (!reactionBubbles) return;
    const el = document.createElement("span");
    el.className = "reaction-bubble";
    el.textContent = emoji;
    el.style.left = (20 + Math.random() * 60) + "%";
    el.style.bottom = "0";
    reactionBubbles.appendChild(el);
    el.addEventListener("animationend", () => el.remove());
  }

  document.querySelectorAll(".reaction-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const emoji = btn.dataset.emoji;

      // Show locally
      showReactionBubble(emoji);

      // Send via WebSocket
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "reaction", emoji }));
      }
    });
  });

  function handleReaction(msg) {
    showReactionBubble(msg.emoji || "👍");
  }

  // ── Video (Webcam) ──
  const camToggleBtn = document.getElementById("camToggleBtn");
  const selfVideo = document.getElementById("selfVideo");
  const selfVideoOff = document.getElementById("selfVideoOff");
  const selfVideoName = document.getElementById("selfVideoName");
  const selfVideoAvatar = document.getElementById("selfVideoAvatar");
  let camStream = null;
  let camActive = false;

  if (selfVideoName) selfVideoName.textContent = myName;
  if (selfVideoAvatar) selfVideoAvatar.textContent = myName.charAt(0).toUpperCase();

  async function toggleCam() {
    if (camActive) {
      // Turn off
      if (camStream) {
        camStream.getTracks().forEach(t => t.stop());
        camStream = null;
      }
      if (selfVideo) selfVideo.srcObject = null;
      if (selfVideoOff) selfVideoOff.classList.remove("hidden");
      if (camToggleBtn) camToggleBtn.classList.remove("ctrl-btn-active");
      camActive = false;
    } else {
      // Turn on
      try {
        camStream = await navigator.mediaDevices.getUserMedia({
          video: { width: 320, height: 180, facingMode: "user" },
          audio: false,
        });
        if (selfVideo) selfVideo.srcObject = camStream;
        if (selfVideoOff) selfVideoOff.classList.add("hidden");
        if (camToggleBtn) camToggleBtn.classList.add("ctrl-btn-active");
        camActive = true;
      } catch (e) {
        if (typeof toast !== "undefined") toast.error("Kamera-Zugriff verweigert");
      }
    }
  }

  if (camToggleBtn) camToggleBtn.addEventListener("click", toggleCam);

  // ── Recording ──
  const recordBtn = document.getElementById("recordBtn");
  let mediaRecorder = null;
  let recordedChunks = [];
  let isRecording = false;

  async function toggleRecording() {
    if (isRecording) {
      stopRecording();
      return;
    }

    // Use the existing mic stream from AudioCapture, or request new one
    let stream = null;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (e) {
      if (typeof toast !== "undefined") toast.error("Mikrofon-Zugriff für Aufnahme nötig");
      return;
    }

    recordedChunks = [];
    const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
      ? "audio/webm;codecs=opus"
      : "audio/webm";

    try {
      mediaRecorder = new MediaRecorder(stream, { mimeType });
    } catch (e) {
      if (typeof toast !== "undefined") toast.error("Aufnahme nicht unterstützt");
      return;
    }

    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) recordedChunks.push(e.data);
    };

    mediaRecorder.onstop = () => {
      const blob = new Blob(recordedChunks, { type: mimeType });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      const name = document.querySelector(".meeting-room-title")?.textContent || "meeting";
      const date = new Date().toISOString().slice(0, 10);
      a.href = url;
      a.download = `nadini-recording-${name.replace(/\s+/g, "-").toLowerCase()}-${date}.webm`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      if (typeof toast !== "undefined") toast.success("Aufnahme heruntergeladen");
      stream.getTracks().forEach(t => t.stop());
    };

    mediaRecorder.start(1000); // 1s chunks
    isRecording = true;
    if (recordBtn) recordBtn.classList.add("ctrl-btn-recording");
    if (typeof toast !== "undefined") toast.info("Aufnahme gestartet");
  }

  function stopRecording() {
    if (mediaRecorder && mediaRecorder.state !== "inactive") {
      mediaRecorder.stop();
    }
    isRecording = false;
    if (recordBtn) recordBtn.classList.remove("ctrl-btn-recording");
  }

  if (recordBtn) recordBtn.addEventListener("click", toggleRecording);

  // ── Screen Sharing ──
  const shareBtn = document.getElementById("shareBtn");
  const stopShareBtn = document.getElementById("stopShareBtn");
  const screenContainer = document.getElementById("screenShareContainer");
  const screenVideo = document.getElementById("screenShareVideo");
  let screenStream = null;

  async function toggleScreenShare() {
    if (screenStream) {
      stopScreenShare();
      return;
    }
    try {
      screenStream = await navigator.mediaDevices.getDisplayMedia({
        video: { cursor: "always" },
        audio: false,
      });
      screenVideo.srcObject = screenStream;
      screenContainer.classList.remove("hidden");
      shareBtn.classList.add("ctrl-btn-active");

      // Track ended (user clicks browser "Stop sharing")
      screenStream.getVideoTracks()[0].onended = () => stopScreenShare();

      if (typeof toast !== "undefined") toast.info("Bildschirmfreigabe aktiv");

      // Notify participants via WebSocket
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "status_update", status: "sharing" }));
      }
    } catch (err) {
      if (err.name !== "NotAllowedError") {
        if (typeof toast !== "undefined") toast.error("Bildschirmfreigabe fehlgeschlagen");
      }
    }
  }

  function stopScreenShare() {
    if (screenStream) {
      screenStream.getTracks().forEach(t => t.stop());
      screenStream = null;
    }
    screenVideo.srcObject = null;
    screenContainer.classList.add("hidden");
    shareBtn.classList.remove("ctrl-btn-active");
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "status_update", status: "speaking" }));
    }
  }

  if (shareBtn) shareBtn.addEventListener("click", toggleScreenShare);
  if (stopShareBtn) stopShareBtn.addEventListener("click", stopScreenShare);

  // ── Keyboard Shortcuts ──
  document.addEventListener("keydown", (e) => {
    if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA" || e.target.tagName === "SELECT") return;

    switch (e.key.toLowerCase()) {
      case "m":
        e.preventDefault();
        toggleMic();
        break;
      case "c":
        e.preventDefault();
        if (captionBtn) captionBtn.click();
        break;
      case "s":
        e.preventDefault();
        toggleScreenShare();
        break;
      case "r":
        e.preventDefault();
        toggleRecording();
        break;
      case "v":
        e.preventDefault();
        toggleCam();
        break;
      case "d":
        e.preventDefault();
        if (downloadBtn) downloadBtn.click();
        break;
      case "i":
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
