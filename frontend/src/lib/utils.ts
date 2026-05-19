import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(
  date: string | Date | null | undefined,
  format?: string
): string {
  if (!date) return '-';

  const parsedDate = typeof date === 'string' ? new Date(date) : date;

  if (Number.isNaN(parsedDate.getTime())) return '-';

  return parsedDate.toLocaleDateString('tr-TR', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}