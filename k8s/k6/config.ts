/**
 * Shared configuration for all k6 tests.
 * Override via environment variables when running:
 *   k6 run -e BASE_URL=https://api.worldofapps.bar -e AUTH_TOKEN=xxx load.ts
 */

// Base URL of the backend API
export const BASE_URL = __ENV.BASE_URL || "https://api.worldofapps.bar";

// Pre-provisioned auth token (Bearer)
// Generate one via: POST /auth/login/ { username, password }
export const AUTH_TOKEN = __ENV.AUTH_TOKEN || "";

// Test user credentials (used by setup functions to auto-login)
export const TEST_USERNAME = __ENV.TEST_USERNAME || "k6_loadtest";
export const TEST_PASSWORD = __ENV.TEST_PASSWORD || "k6_loadtest_password_2026";

// Common HTTP params
export const authHeaders = () => ({
  headers: {
    "Content-Type": "application/json",
    Authorization: `Bearer ${AUTH_TOKEN}`,
  },
});

// Thresholds reusable across test types
export const commonThresholds = {
  http_req_failed: ["rate<0.01"], // <1% errors
  http_req_duration: ["p(95)<500", "p(99)<1500"], // p95 < 500ms, p99 < 1500ms
};

export const relaxedThresholds = {
  http_req_failed: ["rate<0.05"], // <5% errors for stress/spike
  http_req_duration: ["p(95)<2000", "p(99)<5000"],
};
