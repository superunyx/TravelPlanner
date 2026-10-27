import { supabase } from "./supabase";

const API_BASE_URL: string =
  import.meta.env.VITE_API_URL ||
  import.meta.env.VITE_API_BASE_URL ||
  "http://localhost:8000";

export interface ApiErrorPayload {
  error: {
    code: string;
    message: string;
  };
}

export class ApiClientError extends Error {
  public readonly status: number;
  public readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
    this.code = code;
  }
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const {
    data: { session },
  } = await supabase.auth.getSession();

  const headers = new Headers(options.headers);
  if (!headers.has("Content-Type") && options.body !== undefined) {
    headers.set("Content-Type", "application/json");
  }
  if (session?.access_token) {
    headers.set("Authorization", `Bearer ${session.access_token}`);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorCode = `HTTP_${response.status}`;
    let errorMessage = response.statusText || "Request failed";

    try {
      const payload = (await response.json()) as Partial<ApiErrorPayload>;
      if (payload.error?.code && payload.error?.message) {
        errorCode = payload.error.code;
        errorMessage = payload.error.message;
      }
    } catch {
      // Fallback to default HTTP status error
    }

    throw new ApiClientError(response.status, errorCode, errorMessage);
  }

  return (await response.json()) as T;
}
