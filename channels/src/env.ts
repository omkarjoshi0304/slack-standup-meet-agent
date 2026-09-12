export function required(name: string): string {
  const value = process.env[name];
  if (!value) {
    throw new Error(
      `Missing required environment variable: ${name}. Add it to the root .env file.`,
    );
  }
  return value;
}

export function optional(name: string, fallback: string): string {
  return process.env[name] ?? fallback;
}
