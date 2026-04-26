/**
 * Nadini — App Configuration
 *
 * API_MODE:
 *   "demo"  → Simulierte API-Calls, kein Backend nötig (Default für file://)
 *   "live"  → Echte API-Calls (Nginx proxied /auth/*, /meetings/*)
 *
 * Automatische Erkennung:
 *   - file:// → demo
 *   - localhost:3000/3001 (Docker) → live
 *   - nadini.ai → live
 */
const NADINI_CONFIG = (function () {
  const host = window.location.hostname;
  const port = window.location.port;
  const protocol = window.location.protocol;
  const isSecure = protocol === "https:";
  const wsProtocol = isSecure ? "wss:" : "ws:";

  // file:// = always demo
  if (protocol === "file:") {
    return { API_MODE: "demo", AUTH_API_BASE: "", MEETING_API_BASE: "", WS_BASE: "" };
  }

  // Docker dev or production: nginx proxies everything
  if ((host === "localhost" && (port === "3000" || port === "3001")) || host.includes("nadini.ai")) {
    return {
      API_MODE: "live",
      AUTH_API_BASE: "",
      MEETING_API_BASE: "",
      WS_BASE: `${wsProtocol}//${host}${port ? ":" + port : ""}`,
      AUDIO_WS_BASE: `${wsProtocol}//${host}${port ? ":" + port : ""}`,
    };
  }

  // Direct service access (dev without Docker)
  if (host === "localhost" && port === "8001") {
    return {
      API_MODE: "live",
      AUTH_API_BASE: "http://localhost:8001",
      MEETING_API_BASE: "http://localhost:8002",
      WS_BASE: "ws://localhost:8002",
    };
  }

  // Default: demo mode
  return { API_MODE: "demo", AUTH_API_BASE: "", MEETING_API_BASE: "", WS_BASE: "" };
})();
