/**
 * LOAD TEST
 * ─────────
 * Purpose : Evaluate normal expected traffic.
 * Pattern : Ramp up → hold steady → ramp down.
 * Duration: ~8 minutes total.
 *
 * Run:
 *   k6 run -e BASE_URL=https://api.worldofapps.bar -e AUTH_TOKEN=<token> load.ts
 */

import { sleep } from "k6";
import { commonThresholds } from "./config.ts";
import { ensureTestUser, runAllScenarios, errorRate } from "./helpers.ts";

export const options = {
  stages: [
    { duration: "1m", target: 20 }, // ramp up to 20 VUs
    { duration: "3m", target: 20 }, // hold at 20 VUs
    { duration: "1m", target: 50 }, // ramp up to 50 VUs
    { duration: "2m", target: 50 }, // hold at 50 VUs
    { duration: "1m", target: 0 }, // ramp down
  ],
  thresholds: {
    ...commonThresholds,
    custom_error_rate: ["rate<0.02"], // <2% custom errors
  },
};

export function setup() {
  return ensureTestUser();
}

export default function (data: { token: string }) {
  runAllScenarios(data);
  sleep(Math.random() * 2 + 1); // 1–3s think time between iterations
}
