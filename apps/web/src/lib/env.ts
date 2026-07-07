type FrontendEnv = {
  appEnv: string;
  appUrl: string;
  apiUrl: string;
};

const requiredEnv = (key: string, fallback?: string): string => {
  const value = process.env[key] ?? fallback;

  if (!value) {
    throw new Error(`Missing required frontend environment variable: ${key}`);
  }

  return value;
};

export const env: FrontendEnv = {
  appEnv: requiredEnv("NEXT_PUBLIC_APP_ENV", "development"),
  appUrl: requiredEnv("NEXT_PUBLIC_APP_URL", "http://localhost:3000"),
  apiUrl: requiredEnv("NEXT_PUBLIC_API_URL", "http://localhost:8000"),
};
