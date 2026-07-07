import { env } from "@/lib/env";

type ApiClientOptions = RequestInit & {
  token?: string;
};

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly payload: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

const buildUrl = (path: string): string => {
  const baseUrl = env.apiUrl.endsWith("/") ? env.apiUrl : `${env.apiUrl}/`;
  return new URL(path.replace(/^\//, ""), baseUrl).toString();
};

export const apiClient = async <T>(
  path: string,
  { headers, token, ...options }: ApiClientOptions = {},
): Promise<T> => {
  const response = await fetch(buildUrl(path), {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
  });

  const contentType = response.headers.get("content-type");
  const payload = contentType?.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    throw new ApiError("Life Pilot API request failed", response.status, payload);
  }

  return payload as T;
};
