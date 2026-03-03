/**
 * BREAKPOINT TEST
 * ───────────────
 * Purpose : Find the absolute maximum capacity of the deployment.
 *           Ramps up indefinitely until failure thresholds are breached.
 * Pattern : Continuous, aggressive ramp-up. k6 aborts when thresholds fail.
 * Duration: Variable (aborts on threshold breach).
 *
 * ⚠️  WARNING: This test is destructive by nature — it WILL push your
 *    cluster to its limits. Run only in staging or with monitoring ready.
 *
 * Run:
 *   k6 run -e BASE_URL=https://api.worldofapps.bar -e AUTH_TOKEN=<token> breakpoint.ts
 */

import { sleep } from "k6";
import { ensureTestUser, runAllScenarios, errorRate } from "./helpers.ts";

export const options = {
  // Use executor with ramping-arrival-rate for consistent request pressure
  scenarios: {
    breakpoint: {
      executor: "ramping-arrival-rate",
      startRate: 10, // start at 10 iterations/sec
      timeUnit: "1s",
      preAllocatedVUs: 50,
      maxVUs: 1000, // allow up to 1000 VUs
      stages: [
        { duration: "2m", target: 30 }, // 30 req/s
        { duration: "2m", target: 60 }, // 60 req/s
        { duration: "2m", target: 100 }, // 100 req/s
        { duration: "2m", target: 150 }, // 150 req/s
        { duration: "2m", target: 200 }, // 200 req/s
        { duration: "2m", target: 300 }, // 300 req/s
        { duration: "2m", target: 500 }, // 500 req/s — likely failure zone
      ],
    },
  },
  thresholds: {
    // Abort as soon as these breach
    http_req_failed: [
      { threshold: "rate<0.30", abortOnFail: true, delayAbortEval: "30s" },
    ],
    http_req_duration: [
      { threshold: "p(95)<10000", abortOnFail: true, delayAbortEval: "30s" },
    ],
  },
};

export function setup() {
  return ensureTestUser();
}

export default function (data: { token: string }) {
  runAllScenarios(data);
  // Minimal sleep — we want maximum pressure
  sleep(0.2);
}
