import type { paths } from "@/lib/api/schema";
import { clearToken, getToken } from "@/lib/auth";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public body?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** Runtime Page envelope from paginated list endpoints (schema may still show bare arrays). */
export type PageEnvelope<T> = {
  items: T[];
  total: number;
  offset: number;
  limit: number;
};

export async function unwrapPageItems<T>(response: Promise<unknown>): Promise<T[]> {
  const page = (await response) as PageEnvelope<T>;
  return page.items;
}

type HttpMethod = "get" | "post" | "put" | "patch" | "delete";

type PathKey = keyof paths;

type Operation<P extends PathKey, M extends HttpMethod> = M extends keyof paths[P]
  ? paths[P][M]
  : never;

type JsonBody<Op> = Op extends {
  requestBody: { content: { "application/json": infer B } };
}
  ? B
  : undefined;

type SuccessJson<Op> = Op extends {
  responses: { 200: { content: { "application/json": infer R } } };
}
  ? R
  : Op extends {
        responses: { 201: { content: { "application/json": infer R } } };
      }
    ? R
    : unknown;

function interpolatePath(
  path: string,
  pathParams?: Record<string, string | number>,
): string {
  if (!pathParams) return path;
  let result = path;
  for (const [key, value] of Object.entries(pathParams)) {
    result = result.replace(`{${key}}`, encodeURIComponent(String(value)));
  }
  return result;
}

function parseErrorDetail(data: unknown, status: number): string {
  if (typeof data === "object" && data !== null && "detail" in data) {
    const detail = (data as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((item) =>
          typeof item === "object" && item !== null && "msg" in item
            ? String((item as { msg: unknown }).msg)
            : JSON.stringify(item),
        )
        .join("; ");
    }
  }
  return `Erro HTTP ${status}`;
}

async function handleResponse<T>(response: Response, useAuth: boolean): Promise<T> {
  if (response.status === 401 && useAuth) {
    clearToken();
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const text = await response.text();
  let data: unknown = undefined;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }

  if (!response.ok) {
    throw new ApiError(parseErrorDetail(data, response.status), response.status, data);
  }

  return data as T;
}

export async function apiFetch<P extends PathKey, M extends HttpMethod>(
  path: P,
  options: {
    method: M;
    body?: JsonBody<Operation<P, M>>;
    query?: Record<string, string | number | boolean | null | undefined>;
    pathParams?: Record<string, string | number>;
    auth?: boolean;
  },
): Promise<SuccessJson<Operation<P, M>>> {
  const resolvedPath = interpolatePath(path, options.pathParams);
  const url = new URL(`${API_BASE_URL}${resolvedPath}`);
  if (options.query) {
    for (const [key, value] of Object.entries(options.query)) {
      if (value === undefined || value === null) continue;
      url.searchParams.set(key, String(value));
    }
  }

  const headers: HeadersInit = {
    Accept: "application/json",
  };

  if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  const useAuth = options.auth !== false;
  if (useAuth) {
    const token = getToken();
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
  }

  const response = await fetch(url.toString(), {
    method: options.method.toUpperCase(),
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });

  return handleResponse(response, useAuth);
}

/** Upload multipart (ex.: XML de NF-e). */
export async function apiUpload<T>(
  path: string,
  file: File,
  fieldName = "file",
): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  const form = new FormData();
  form.append(fieldName, file);

  const headers: HeadersInit = { Accept: "application/json" };
  const token = getToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(url, {
    method: "POST",
    headers,
    body: form,
  });

  return handleResponse<T>(response, true);
}
