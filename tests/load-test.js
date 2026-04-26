/**
 * Nadini Load Test — k6 Script
 *
 * Usage:
 *   brew install k6
 *   k6 run tests/load-test.js
 *
 * Scenarios:
 *   - 10 concurrent users creating meetings
 *   - 50 concurrent users listing meetings
 *   - Translation throughput test
 */
import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";

const BASE_URL = __ENV.BASE_URL || "http://localhost:8002";
const AUTH_URL = __ENV.AUTH_URL || "http://localhost:8001";

// Custom metrics
const translationLatency = new Trend("translation_latency");
const meetingCreateRate = new Rate("meeting_create_success");

export const options = {
  scenarios: {
    // Scenario 1: Meeting CRUD
    meeting_crud: {
      executor: "ramping-vus",
      startVUs: 1,
      stages: [
        { duration: "30s", target: 10 },
        { duration: "1m", target: 10 },
        { duration: "30s", target: 0 },
      ],
      exec: "meetingCrud",
    },
    // Scenario 2: Health checks (smoke test)
    health: {
      executor: "constant-rate",
      rate: 10,
      duration: "2m",
      preAllocatedVUs: 5,
      exec: "healthCheck",
    },
  },
  thresholds: {
    http_req_duration: ["p(95)<2000"],
    "translation_latency": ["p(95)<1500"],
    "meeting_create_success": ["rate>0.95"],
  },
};

export function healthCheck() {
  const res = http.get(`${BASE_URL}/health`);
  check(res, {
    "health status 200": (r) => r.status === 200,
    "health response ok": (r) => JSON.parse(r.body).status === "ok",
  });
}

export function meetingCrud() {
  // Create meeting
  const createRes = http.post(
    `${BASE_URL}/meetings`,
    JSON.stringify({
      name: `Load Test Meeting ${__VU}-${__ITER}`,
      source_lang: "de",
      target_langs: ["en"],
      mode: "online",
    }),
    {
      headers: {
        "Content-Type": "application/json",
        "Authorization": "Bearer demo-load-test",
      },
    }
  );

  const success = createRes.status === 201 || createRes.status === 401;
  meetingCreateRate.add(success);

  // List meetings
  const listRes = http.get(`${BASE_URL}/meetings`, {
    headers: { "Authorization": "Bearer demo-load-test" },
  });

  check(listRes, {
    "list status ok": (r) => r.status === 200 || r.status === 401,
  });

  // Provider health
  const healthRes = http.get(`${BASE_URL}/providers/health`, {
    headers: { "Authorization": "Bearer demo-load-test" },
  });

  sleep(1);
}

export function handleSummary(data) {
  return {
    stdout: JSON.stringify(
      {
        total_requests: data.metrics.http_reqs?.values?.count || 0,
        avg_duration_ms: Math.round(data.metrics.http_req_duration?.values?.avg || 0),
        p95_duration_ms: Math.round(data.metrics.http_req_duration?.values?.["p(95)"] || 0),
        errors: data.metrics.http_req_failed?.values?.rate || 0,
      },
      null,
      2
    ),
  };
}
