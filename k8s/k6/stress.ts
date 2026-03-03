/**
 * STRESS TEST
 * ───────────
 * Purpose : Push the system beyond normal capacity to find the sweet spot
 *           where performance starts to degrade.
 * Pattern : Progressive ramp-up through increasing stages.
 * Duration: ~16 minutes total.
 *
 * Run:
 *   k6 run -e BASE_URL=https://api.worldofapps.bar -e AUTH_TOKEN=<token> stress.ts
 */

import { sleep } from "k6";
import { relaxedThresholds } from "./config.ts";
import { ensureTestUser, runAllScenarios, errorRate } from "./helpers.ts";

export const options = {
  stages: [
    { duration: "1m", target: 20 }, // warm up
    { duration: "2m", target: 50 }, // moderate load
    { duration: "2m", target: 100 }, // high load
    { duration: "2m", target: 150 }, // very high load
    { duration: "2m", target: 200 }, // extreme load
    { duration: "2m", target: 250 }, // → beyond expected capacity
    { duration: "2m", target: 300 }, // → stress ceiling
    { duration: "3m", target: 0 }, // ramp down & recovery
  ],
  thresholds: {
    ...relaxedThresholds,
    custom_error_rate: ["rate<0.15"], // up to 15% under extreme stress
  },
};

export function setup() {
  return ensureTestUser();
}

export default function (data: { token: string }) {
  runAllScenarios(data);
  sleep(Math.random() + 0.5); // 0.5–1.5s think time
}
