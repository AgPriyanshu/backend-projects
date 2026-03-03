/**
 * SOAK TEST (Endurance)
 * ─────────────────────
 * Purpose : Find memory leaks, connection pool exhaustion, or degradation over time.
 * Pattern : Ramp up → hold at moderate load for a long period → ramp down.
 * Duration: ~35 minutes total (increase for real endurance runs).
 *
 * Run:
 *   k6 run -e BASE_URL=https://api.worldofapps.bar -e AUTH_TOKEN=<token> soak.ts
 */

import { sleep } from "k6";
import { commonThresholds } from "./config.ts";
import { ensureTestUser, runAllScenarios, errorRate } from "./helpers.ts";

export const options = {
  stages: [
    { duration: "2m", target: 30 }, // ramp up
    { duration: "30m", target: 30 }, // soak at 30 VUs for 30 min
    { duration: "3m", target: 0 }, // ramp down
  ],
  thresholds: {
    ...commonThresholds,
    custom_error_rate: ["rate<0.01"], // very strict — must survive long
    // Watch for latency creep (sign of resource leak)
    http_req_duration: ["p(95)<500", "p(99)<1500", "avg<300"],
  },
};

export function setup() {
  return ensureTestUser();
}

export default function (data: { token: string }) {
  runAllScenarios(data);
  sleep(Math.random() * 3 + 2); // 2–5s think time (lower intensity for endurance)
}
