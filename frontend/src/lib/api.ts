import { apiRoutes } from "@/lib/api-routes";
import type { AuthResponse } from "@/lib/api-types";

const API_PROXY_BASE = "/api/backend";
const ACCESS_TOKEN_KEY = "ftc.accessToken";
const REFRESH_TOKEN_KEY = "ftc.refreshToken";
const AUTH_ROLE_KEY = "ftc.authRole";
const LEGACY_ACCESS_TOKEN_KEY = "authToken";

export type AuthRole = "admin" | "cidadao";
type ApiResponseBody = Record<string, unknown> | string | null;

export class ApiError extends Error {
  status: number;
  body: ApiResponseBody;

  constructor(message: string, status: number, body: ApiResponseBody) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

function normalizePath(path: string) {
  return path.startsWith("/") ? path : `/${path}`;
}

function browserStorage() {
  return typeof window === "undefined" ? null : window.localStorage;
}

function authToken() {
  const storage = browserStorage();
  return storage?.getItem(ACCESS_TOKEN_KEY) ?? storage?.getItem(LEGACY_ACCESS_TOKEN_KEY);
}

function refreshToken() {
  return browserStorage()?.getItem(REFRESH_TOKEN_KEY) ?? null;
}

export function getAuthRole(): AuthRole | null {
  const role = browserStorage()?.getItem(AUTH_ROLE_KEY);
  return role === "admin" || role === "cidadao" ? role : null;
}

export function hasAuthSession(role?: AuthRole) {
  const currentRole = getAuthRole();
  return Boolean(authToken() && refreshToken() && (!role || currentRole === role));
}

export function saveAuthSession<TUser>(
  response: AuthResponse<TUser>,
  role: AuthRole,
) {
  if (!response.access || !response.refresh) {
    throw new Error("O servidor não retornou uma sessão completa.");
  }

  const storage = browserStorage();
  storage?.setItem(ACCESS_TOKEN_KEY, response.access);
  storage?.setItem(REFRESH_TOKEN_KEY, response.refresh);
  storage?.setItem(AUTH_ROLE_KEY, role);
  storage?.removeItem(LEGACY_ACCESS_TOKEN_KEY);
}

export function clearAuthSession() {
  const storage = browserStorage();
  storage?.removeItem(ACCESS_TOKEN_KEY);
  storage?.removeItem(REFRESH_TOKEN_KEY);
  storage?.removeItem(AUTH_ROLE_KEY);
  storage?.removeItem(LEGACY_ACCESS_TOKEN_KEY);
}

function bodyMessage(body: ApiResponseBody, fallback: string) {
  if (!body) return fallback;

  if (typeof body === "string") {
    if (/<!doctype html|<html[\s>]/i.test(body)) return fallback;
    return body || fallback;
  }

  const candidates = ["detail", "message", "error", "non_field_errors"];
  for (const key of candidates) {
    const value = body[key];
    if (typeof value === "string") return value;
    if (Array.isArray(value) && value.length > 0) return value.join(" ");
  }

  const firstValue = Object.values(body).find(
    (value) => typeof value === "string" || Array.isArray(value),
  );
  if (typeof firstValue === "string") return firstValue;
  if (Array.isArray(firstValue)) return firstValue.join(" ");
  return fallback;
}

async function readBody(response: Response): Promise<ApiResponseBody> {
  if (response.status === 204) return null;
  const contentType = response.headers.get("content-type") ?? "";
  if (contentType.includes("application/json")) return response.json();
  const text = await response.text();
  return text || null;
}

function requestHeaders(options: RequestInit) {
  const headers = new Headers(options.headers);
  const token = authToken();
  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  return headers;
}

function request(path: string, options: RequestInit) {
  return fetch(`${API_PROXY_BASE}${normalizePath(path)}`, {
    ...options,
    headers: requestHeaders(options),
    credentials: "omit",
  });
}

let refreshPromise: Promise<boolean> | null = null;

async function refreshAccessToken() {
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    const role = getAuthRole();
    const storedRefresh = refreshToken();
    if (!role || !storedRefresh) return false;

    const refreshPath =
      role === "admin" ? apiRoutes.adminRefresh : apiRoutes.cidadaoRefresh;
    const response = await fetch(`${API_PROXY_BASE}${refreshPath}`, {
      method: "POST",
      credentials: "omit",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh: storedRefresh }),
    });

    if (!response.ok) {
      clearAuthSession();
      return false;
    }

    const body = (await response.json()) as {
      access?: string;
      refresh?: string;
    };
    if (!body.access) {
      clearAuthSession();
      return false;
    }

    const storage = browserStorage();
    storage?.setItem(ACCESS_TOKEN_KEY, body.access);
    if (body.refresh) storage?.setItem(REFRESH_TOKEN_KEY, body.refresh);
    return true;
  })().finally(() => {
    refreshPromise = null;
  });

  return refreshPromise;
}

function canRefresh(path: string) {
  return !path.includes("/login/") &&
    !path.includes("/refresh/") &&
    !path.includes("/logout/");
}

export async function apiFetch<TResponse>(
  path: string,
  options: RequestInit = {},
) {
  let response = await request(path, options);

  if (response.status === 401 && authToken() && canRefresh(path)) {
    const refreshed = await refreshAccessToken();
    if (refreshed) response = await request(path, options);
  }

  const body = await readBody(response);
  if (!response.ok) {
    throw new ApiError(
      bodyMessage(body, "Não foi possível concluir a solicitação."),
      response.status,
      body,
    );
  }
  return body as TResponse;
}

export async function logout(path: string) {
  try {
    let storedRefresh = refreshToken();
    if (!storedRefresh) return;

    try {
      await apiFetch<null>(path, {
        method: "POST",
        body: JSON.stringify({ refresh: storedRefresh }),
      });
    } catch (error) {
      if (!(error instanceof ApiError) || error.status !== 401) throw error;

      const refreshed = await refreshAccessToken();
      storedRefresh = refreshToken();
      if (!refreshed || !storedRefresh) throw error;

      await apiFetch<null>(path, {
        method: "POST",
        body: JSON.stringify({ refresh: storedRefresh }),
      });
    }
  } finally {
    clearAuthSession();
  }
}

export function onlyDigits(value: string) {
  return value.replace(/\D/g, "");
}
