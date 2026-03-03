/**
 * SPIKE TEST
 * ──────────
 * Purpose : Test how the system handles sudden, extreme bursts of traffic.
 *           Validates HPA response time, pod startup, and recovery.
 * Pattern : Low baseline → sudden spike → back to baseline → repeat → ramp down.
 * Duration: ~12 minutes total.
 *
 * Run:
 *   k6 run -e BASE_URL=https://api.worldofapps.bar -e AUTH_TOKEN=<token> spike.ts
 */

import { sleep } from "k6";
import { relaxedThresholds } from "./config.ts";
import { ensureTestUser, runAllScenarios, errorRate } from "./helpers.ts";

export const options = {
  stages: [
    { duration: "1m", target: 10 }, // baseline
    { duration: "15s", target: 150 }, // 🚀 spike to 150 VUs
    { duration: "2m", target: 150 }, // hold spike
    { duration: "15s", target: 10 }, // rapid drop back to baseline
    { duration: "2m", target: 10 }, // recovery period
    { duration: "15s", target: 200 }, // 🚀 second spike — even higher
    { duration: "2m", target: 200 }, // hold
    { duration: "30s", target: 10 }, // cool down
    { duration: "2m", target: 10 }, // recovery observation
    { duration: "1m", target: 0 }, // ramp down
  ],
  thresholds: {
    ...relaxedThresholds,
    custom_error_rate: ["rate<0.10"], // allow up to 10% during spikes
  },
};

export function setup() {
  return ensureTestUser();
}

export default function (data: { token: string }) {
  runAllScenarios(data);
  sleep(Math.random() * 1.5 + 0.5); // 0.5–2s think time (fast during spikes)
}
