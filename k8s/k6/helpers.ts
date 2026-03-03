/**
 * Shared helper functions for k6 test scenarios.
 * Provides reusable API call patterns for each backend app.
 */

import http from "k6/http";
import { check, group, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";
import {
  BASE_URL,
  AUTH_TOKEN,
  TEST_USERNAME,
  TEST_PASSWORD,
  authHeaders,
} from "./config.ts";

// ── Custom Metrics ──────────────────────────────────────────────────────
export const errorRate = new Rate("custom_error_rate");
export const authDuration = new Trend("auth_duration", true);
export const apiDuration = new Trend("api_duration", true);

// ── Auth Helpers ────────────────────────────────────────────────────────

/** Register a new user (idempotent — server returns error if exists). */
export function registerUser(username: string, password: string) {
  const res = http.post(
    `${BASE_URL}/auth/register/`,
    JSON.stringify({ username, password, is_staff: false }),
    { headers: { "Content-Type": "application/json" } },
  );
  return res;
}

/** Login and return the auth token string. */
export function loginUser(username: string, password: string): string {
  const res = http.post(
    `${BASE_URL}/auth/login/`,
    JSON.stringify({ username, password }),
    { headers: { "Content-Type": "application/json" } },
  );
  authDuration.add(res.timings.duration);

  const body = res.json() as { data?: { token?: string } };
  const token = body?.data?.token || "";

  check(res, {
    "login succeeded": (r) => r.status === 200,
    "token returned": () => token.length > 0,
  });

  return token;
}

/**
 * Setup function that ensures a test user exists and returns an auth token.
 * Use in the k6 `setup()` lifecycle hook.
 */
export function ensureTestUser(): { token: string } {
  // If a token was passed via env, use it directly
  if (AUTH_TOKEN) {
    return { token: AUTH_TOKEN };
  }

  // Otherwise, register + login
  registerUser(TEST_USERNAME, TEST_PASSWORD);
  const token = loginUser(TEST_USERNAME, TEST_PASSWORD);
  return { token };
}

/** Build auth headers from setup data. */
export function headersFrom(data: { token: string }) {
  return {
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${data.token}`,
    },
  };
}

// ── Scenario Functions (one per app) ────────────────────────────────────

/** Health-check — unauthenticated. */
export function scenarioPing() {
  group("Health Check", () => {
    const res = http.get(`${BASE_URL}/ping/`);
    const ok = check(res, { "ping: status 200": (r) => r.status === 200 });
    errorRate.add(!ok);
    apiDuration.add(res.timings.duration);
  });
}

/** Todo App — CRUD cycle. */
export function scenarioTasks(params: object) {
  group("Todo App", () => {
    // List tasks
    const listRes = http.get(`${BASE_URL}/tasks/`, params);
    check(listRes, { "tasks: list 200": (r) => r.status === 200 });
    errorRate.add(listRes.status !== 200);
    apiDuration.add(listRes.timings.duration);

    // Create a task
    const createRes = http.post(
      `${BASE_URL}/tasks/`,
      JSON.stringify({ description: `k6-task-${Date.now()}` }),
      params,
    );
    check(createRes, {
      "tasks: create 2xx": (r) => r.status >= 200 && r.status < 300,
    });
    errorRate.add(createRes.status < 200 || createRes.status >= 300);
    apiDuration.add(createRes.timings.duration);

    // If created, try to read & delete
    if (createRes.status >= 200 && createRes.status < 300) {
      const body = createRes.json() as { data?: { id?: number } };
      const id = body?.data?.id;
      if (id) {
        const getRes = http.get(`${BASE_URL}/tasks/${id}/`, params);
        check(getRes, { "tasks: get 200": (r) => r.status === 200 });
        apiDuration.add(getRes.timings.duration);

        const delRes = http.del(`${BASE_URL}/tasks/${id}/`, null, params);
        check(delRes, {
          "tasks: delete 2xx": (r) => r.status >= 200 && r.status < 300,
        });
        apiDuration.add(delRes.timings.duration);
      }
    }
  });
}

/** Blogs App — list + create. */
export function scenarioBlogs(params: object) {
  group("Blogs App", () => {
    const listRes = http.get(`${BASE_URL}/blogs/`, params);
    check(listRes, { "blogs: list 200": (r) => r.status === 200 });
    errorRate.add(listRes.status !== 200);
    apiDuration.add(listRes.timings.duration);

    const createRes = http.post(
      `${BASE_URL}/blogs/`,
      JSON.stringify({
        title: `k6-blog-${Date.now()}`,
        content: "Load test blog content",
      }),
      params,
    );
    check(createRes, {
      "blogs: create 2xx": (r) => r.status >= 200 && r.status < 300,
    });
    errorRate.add(createRes.status < 200 || createRes.status >= 300);
    apiDuration.add(createRes.timings.duration);
  });
}

/** Expense Tracker — list + create. */
export function scenarioExpenses(params: object) {
  group("Expense Tracker", () => {
    const listRes = http.get(`${BASE_URL}/expenses/`, params);
    check(listRes, { "expenses: list 200": (r) => r.status === 200 });
    errorRate.add(listRes.status !== 200);
    apiDuration.add(listRes.timings.duration);

    const createRes = http.post(
      `${BASE_URL}/expenses/`,
      JSON.stringify({
        description: `k6-expense-${Date.now()}`,
        amount: Math.floor(Math.random() * 10000),
      }),
      params,
    );
    check(createRes, {
      "expenses: create 2xx": (r) => r.status >= 200 && r.status < 300,
    });
    errorRate.add(createRes.status < 200 || createRes.status >= 300);
    apiDuration.add(createRes.timings.duration);
  });
}

/** Notes App — list + create. */
export function scenarioNotes(params: object) {
  group("Notes App", () => {
    const listRes = http.get(`${BASE_URL}/notes/`, params);
    check(listRes, { "notes: list 200": (r) => r.status === 200 });
    errorRate.add(listRes.status !== 200);
    apiDuration.add(listRes.timings.duration);

    const createRes = http.post(
      `${BASE_URL}/notes/`,
      JSON.stringify({
        title: `k6-note-${Date.now()}`,
        content: "# Load Test\nMarkdown content from k6 load test.",
      }),
      params,
    );
    check(createRes, {
      "notes: create 2xx": (r) => r.status >= 200 && r.status < 300,
    });
    errorRate.add(createRes.status < 200 || createRes.status >= 300);
    apiDuration.add(createRes.timings.duration);
  });
}

/** Ecommerce — browse products, categories, cart. */
export function scenarioEcommerce(params: object) {
  group("Ecommerce", () => {
    // List products
    const productsRes = http.get(`${BASE_URL}/ecom/products/`, params);
    check(productsRes, { "ecom: products 200": (r) => r.status === 200 });
    errorRate.add(productsRes.status !== 200);
    apiDuration.add(productsRes.timings.duration);

    // List categories
    const categoriesRes = http.get(`${BASE_URL}/ecom/categories/`, params);
    check(categoriesRes, { "ecom: categories 200": (r) => r.status === 200 });
    errorRate.add(categoriesRes.status !== 200);
    apiDuration.add(categoriesRes.timings.duration);

    // List cart items
    const cartRes = http.get(`${BASE_URL}/ecom/carts/`, params);
    check(cartRes, { "ecom: cart 200": (r) => r.status === 200 });
    errorRate.add(cartRes.status !== 200);
    apiDuration.add(cartRes.timings.duration);
  });
}

/** Web GIS — list datasets and layers. */
export function scenarioWebGis(params: object) {
  group("Web GIS", () => {
    const datasetsRes = http.get(`${BASE_URL}/web-gis/datasets/`, params);
    check(datasetsRes, { "gis: datasets 200": (r) => r.status === 200 });
    errorRate.add(datasetsRes.status !== 200);
    apiDuration.add(datasetsRes.timings.duration);

    const layersRes = http.get(`${BASE_URL}/web-gis/layers/`, params);
    check(layersRes, { "gis: layers 200": (r) => r.status === 200 });
    errorRate.add(layersRes.status !== 200);
    apiDuration.add(layersRes.timings.duration);
  });
}

/** Notifications — list. */
export function scenarioNotifications(params: object) {
  group("Notifications", () => {
    const res = http.get(`${BASE_URL}/notifications/`, params);
    check(res, { "notifications: list 200": (r) => r.status === 200 });
    errorRate.add(res.status !== 200);
    apiDuration.add(res.timings.duration);
  });
}

/**
 * Run all scenarios in sequence (simulates a real user session).
 * Includes a small sleep between groups.
 */
export function runAllScenarios(data: { token: string }) {
  const params = headersFrom(data);

  scenarioPing();
  sleep(0.5);

  scenarioTasks(params);
  sleep(0.5);

  scenarioBlogs(params);
  sleep(0.5);

  scenarioExpenses(params);
  sleep(0.5);

  scenarioNotes(params);
  sleep(0.5);

  scenarioEcommerce(params);
  sleep(0.5);

  scenarioWebGis(params);
  sleep(0.5);

  scenarioNotifications(params);
  sleep(1);
}
