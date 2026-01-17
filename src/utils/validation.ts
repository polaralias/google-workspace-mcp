/**
 * Validates and sanitizes an email address
 * @param email - The email to validate
 * @returns Sanitized email or null if invalid
 */
export function validateEmail(email: string | undefined | null): string | null {
  if (!email) {
    return null;
  }

  const normalized = email.trim().toLowerCase();
  if (!normalized) {
    return null;
  }

  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(normalized)) {
    return null;
  }

  return normalized;
}
