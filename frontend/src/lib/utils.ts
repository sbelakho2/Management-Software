import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(date: Date | string, options?: Intl.DateTimeFormatOptions): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  if (Number.isNaN(d.getTime())) {
    return '-';
  }
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    ...options,
  }).format(d);
}

export function formatDateTime(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  if (Number.isNaN(d.getTime())) {
    return '-';
  }
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(d);
}

export function formatRelativeTime(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  if (Number.isNaN(d.getTime())) {
    return '-';
  }
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return formatDate(d);
}

export function formatCurrency(
  amount: number,
  currency: string = 'MAD',
  locale: string = 'fr-MA'
): string {
  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
  }).format(amount);
}

export function formatNumber(
  value: number,
  options?: Intl.NumberFormatOptions
): string {
  return new Intl.NumberFormat('en-US', options).format(value);
}

export function formatPercentage(value: number, decimals: number = 0): string {
  return `${value.toFixed(decimals)}%`;
}

export function truncate(str: string, length: number): string {
  if (str.length <= length) return str;
  return `${str.slice(0, length)}...`;
}

export function capitalize(str: string): string {
  return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
}

export function slugify(str: string): string {
  return str
    .toLowerCase()
    .replace(/[^\w\s-]/g, '')
    .replace(/[\s_-]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

export function debounce<T extends (...args: Parameters<T>) => ReturnType<T>>(
  fn: T,
  delay: number
): (...args: Parameters<T>) => void {
  let timeoutId: ReturnType<typeof setTimeout>;
  return (...args: Parameters<T>) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => fn(...args), delay);
  };
}

export function generateId(): string {
  return crypto.randomUUID();
}

export function getInitials(name: string): string {
  return name
    .split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}
/**
 * Validates and sanitizes a redirect path to prevent open redirect vulnerabilities.
 * Only allows internal paths (starting with /) and blocks external URLs or protocol-relative URLs.
 * 
 * @param path - The path to validate
 * @param fallback - Fallback path if the provided path is invalid (default: '/today')
 * @returns A safe internal path
 */
export function getSafeRedirectPath(path: string | null | undefined, fallback: string = '/today'): string {
  // If no path provided, return fallback
  if (!path) {
    return fallback;
  }

  // Trim whitespace
  const trimmedPath = path.trim();

  // Block empty paths
  if (!trimmedPath) {
    return fallback;
  }

  // Block protocol URLs (http://, https://, javascript:, data:, etc.)
  if (/^[a-z][a-z0-9+.-]*:/i.test(trimmedPath)) {
    return fallback;
  }

  // Block protocol-relative URLs (//evil.com)
  if (trimmedPath.startsWith('//')) {
    return fallback;
  }

  // Block backslash URLs (\\evil.com - IE quirk)
  if (trimmedPath.startsWith('\\')) {
    return fallback;
  }

  // Must start with a single forward slash for internal paths
  if (!trimmedPath.startsWith('/')) {
    return fallback;
  }

  // Block URLs with @ in path (could be parsed as credentials)
  if (trimmedPath.includes('@')) {
    return fallback;
  }

  // Block encoded characters that could bypass validation
  // Check for encoded slashes, colons, or at signs
  if (/%2f|%5c|%3a|%40/i.test(trimmedPath)) {
    return fallback;
  }

  // Valid internal path
  return trimmedPath;
}