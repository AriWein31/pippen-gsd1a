// Format time remaining for course coverage
export function formatTimeRemaining(endsAt: Date): {
  hours: number;
  minutes: number;
  totalMinutes: number;
  formatted: string;
  nextDoseFormatted: string;
} {
  const now = new Date();
  const diff = endsAt.getTime() - now.getTime();

  if (diff <= 0) {
    return {
      hours: 0,
      minutes: 0,
      totalMinutes: 0,
      formatted: '0m',
      nextDoseFormatted: 'Now',
    };
  }

  const totalMinutes = Math.floor(diff / (1000 * 60));
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;

  const formatted = hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`;

  // Next dose is at the end time
  const nextDose = new Date(endsAt);
  const nextDoseFormatted = nextDose.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });

  return {
    hours,
    minutes,
    totalMinutes,
    formatted,
    nextDoseFormatted,
  };
}

// Calculate coverage percentage
export function calculateCoveragePercent(startedAt: Date, endsAt: Date): number {
  const now = new Date();
  const totalDuration = endsAt.getTime() - startedAt.getTime();
  const elapsed = now.getTime() - startedAt.getTime();

  if (totalDuration <= 0) return 100;
  if (elapsed <= 0) return 0;

  const percent = (elapsed / totalDuration) * 100;
  return Math.min(100, Math.max(0, percent));
}

// Format date for display
export function formatDate(date: Date): string {
  return new Date(date).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

// Format time for display
export function formatTime(date: Date): string {
  return new Date(date).toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
}

// Format datetime for display
export function formatDateTime(date: Date): string {
  return `${formatDate(date)} ${formatTime(date)}`;
}

// Validate glucose value
export function validateGlucose(value: number): { valid: boolean; error?: string } {
  if (isNaN(value)) {
    return { valid: false, error: 'Please enter a valid number' };
  }
  if (value < 20 || value > 600) {
    return { valid: false, error: 'Glucose must be between 20 and 600 mg/dL' };
  }
  return { valid: true };
}

// Validate cornstarch grams
export function validateCornstarch(grams: number): { valid: boolean; error?: string } {
  if (isNaN(grams)) {
    return { valid: false, error: 'Please enter a valid number' };
  }
  if (grams < 1 || grams > 100) {
    return { valid: false, error: 'Please enter a value between 1 and 100 grams' };
  }
  return { valid: true };
}

// Validate severity
export function validateSeverity(value: number): { valid: boolean; error?: string } {
  if (isNaN(value)) {
    return { valid: false, error: 'Please select a severity level' };
  }
  if (value < 1 || value > 10) {
    return { valid: false, error: 'Severity must be between 1 and 10' };
  }
  return { valid: true };
}

// Debounce function
export function debounce<T extends (...args: unknown[]) => void>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: ReturnType<typeof setTimeout> | null = null;

  return (...args: Parameters<T>) => {
    if (timeout) clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
}

// Generate unique ID
export function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
}

// Class name helper
export function cn(...classes: (string | boolean | undefined | null)[]): string {
  return classes.filter(Boolean).join(' ');
}
