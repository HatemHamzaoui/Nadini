/**
 * Nadini — Audio Capture Module
 *
 * Encapsulates:
 *   1. Real microphone capture via getUserMedia + AnalyserNode (visualizer)
 *   2. Speech recognition via Web Speech API (text extraction)
 *
 * Upgrade hook for server-side Whisper (Option B):
 *   The onResult callback interface stays the same — only the internal
 *   recognition source changes.
 */
const AudioCapture = (function () {
  "use strict";

  // BCP-47 locale mapping
  const LANG_MAP = {
    de: "de-DE", en: "en-US", fr: "fr-FR", es: "es-ES", it: "it-IT",
    ar: "ar-SA", zh: "zh-CN", ja: "ja-JP", ko: "ko-KR", pt: "pt-BR",
    ru: "ru-RU", tr: "tr-TR", nl: "nl-NL", pl: "pl-PL", sv: "sv-SE", hi: "hi-IN",
  };

  let audioCtx = null;
  let analyser = null;
  let mediaStream = null;
  let recognition = null;
  let isRunning = false;
  let resultCallback = null;
  let vizCallback = null;
  let vizAnimId = null;
  let participantLang = "de";
  let autoRestart = true;

  // ── Feature Detection ──
  function isSupported() {
    return {
      visualizer: !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia),
      speechRecognition: !!((window.SpeechRecognition || window.webkitSpeechRecognition)),
    };
  }

  // ── Initialize ──
  async function init(options = {}) {
    participantLang = options.lang || "de";

    // Request microphone
    try {
      mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      // AudioContext + AnalyserNode for visualizer
      audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const source = audioCtx.createMediaStreamSource(mediaStream);
      analyser = audioCtx.createAnalyser();
      analyser.fftSize = 64;
      analyser.smoothingTimeConstant = 0.8;
      source.connect(analyser);

      // Mute the stream initially (don't start ASR yet)
      mediaStream.getAudioTracks().forEach(t => { t.enabled = false; });

    } catch (err) {
      console.warn("AudioCapture: getUserMedia failed:", err.message);
      mediaStream = null;
    }

    // Setup SpeechRecognition
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRec) {
      recognition = new SpeechRec();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = LANG_MAP[participantLang] || "de-DE";
      recognition.maxAlternatives = 1;

      recognition.onresult = (event) => {
        if (!resultCallback) return;
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const result = event.results[i];
          resultCallback({
            text: result[0].transcript,
            lang: participantLang,
            isFinal: result.isFinal,
            confidence: result[0].confidence || 0,
          });
        }
      };

      recognition.onerror = (event) => {
        if (event.error === "no-speech" || event.error === "aborted") return;
        console.warn("AudioCapture: SpeechRecognition error:", event.error);
      };

      // Auto-restart if recognition stops unexpectedly
      recognition.onend = () => {
        if (isRunning && autoRestart) {
          setTimeout(() => {
            try { recognition.start(); } catch (e) { /* already running */ }
          }, 300);
        }
      };
    }

    return {
      hasMic: !!mediaStream,
      hasASR: !!recognition,
    };
  }

  // ── Start (mic on, recognition on) ──
  function start() {
    isRunning = true;

    // Enable mic tracks
    if (mediaStream) {
      mediaStream.getAudioTracks().forEach(t => { t.enabled = true; });
    }

    // Resume AudioContext (required after user gesture)
    if (audioCtx && audioCtx.state === "suspended") {
      audioCtx.resume();
    }

    // Start recognition
    if (recognition) {
      try { recognition.start(); } catch (e) { /* already running */ }
    }

    // Start visualizer loop
    if (analyser && vizCallback && !vizAnimId) {
      const freqData = new Uint8Array(analyser.frequencyBinCount);
      function loop() {
        analyser.getByteFrequencyData(freqData);
        vizCallback(freqData);
        vizAnimId = requestAnimationFrame(loop);
      }
      loop();
    }
  }

  // ── Stop (mic off, recognition off) ──
  function stop() {
    isRunning = false;

    // Mute mic tracks
    if (mediaStream) {
      mediaStream.getAudioTracks().forEach(t => { t.enabled = false; });
    }

    // Stop recognition
    if (recognition) {
      try { recognition.stop(); } catch (e) { /* not running */ }
    }

    // Stop visualizer
    if (vizAnimId) {
      cancelAnimationFrame(vizAnimId);
      vizAnimId = null;
    }
    // Zero out bars
    if (vizCallback) {
      vizCallback(new Uint8Array(32));
    }
  }

  // ── Callbacks ──
  function onResult(cb) { resultCallback = cb; }
  function onVisualizerData(cb) { vizCallback = cb; }

  // ── Cleanup ──
  function destroy() {
    autoRestart = false;
    stop();
    if (recognition) { try { recognition.abort(); } catch (e) {} }
    if (mediaStream) { mediaStream.getTracks().forEach(t => t.stop()); }
    if (audioCtx) { audioCtx.close(); }
    recognition = null;
    mediaStream = null;
    audioCtx = null;
    analyser = null;
  }

  return { init, start, stop, onResult, onVisualizerData, isSupported, destroy };
})();
