/**
 * Nadini — App Configuration
 *
 * API_MODE:
 *   "demo"  → Simulierte API-Calls, kein Backend nötig (Default für file://)
 *   "live"  → Echte API-Calls an AUTH_API_BASE
 *
 * Automatische Erkennung:
 *   - file:// → demo
 *   - localhost:3000 (Docker) → live (Nginx proxied /auth/* → auth-service)
 *   - nadini.ai → live
 */
const NADINI_CONFIG = (function () {
  const host = window.location.hostname;
  const port = window.location.port;
  const protocol = window.location.protocol;

  // file:// = always demo
  if (protocol === "file:") {
    return { API_MODE: "demo", AUTH_API_BASE: "" };
  }

  // Docker dev: nginx on port 3000 proxies /auth/* to auth-service
  if (host === "localhost" && port === "3000") {
    return { API_MODE: "live", AUTH_API_BASE: "" };
  }

  // Production: same-origin proxy
  if (host.includes("nadini.ai")) {
    return { API_MODE: "live", AUTH_API_BASE: "" };
  }

  // Direct auth-service access (dev without Docker)
  if (host === "localhost" && port === "8001") {
    return { API_MODE: "live", AUTH_API_BASE: "http://localhost:8001" };
  }

  // Default: demo mode
  return { API_MODE: "demo", AUTH_API_BASE: "" };
})();
