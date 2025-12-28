import { Color } from "@raycast/api";

/**
 * Format a number as EUR currency with thousands separators
 * 
 * @param value - The number to format
 * @returns Formatted currency string (e.g., "€1,234.56")
 */
export function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "EUR",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

/**
 * Format a number as a percentage with + or - sign
 * 
 * @param value - The percentage value (e.g., 26.95 for 26.95%)
 * @param includeSign - Whether to include + or - sign
 * @returns Formatted percentage string (e.g., "+26.95%")
 */
export function formatPercentage(value: number, includeSign = true): string {
  const sign = includeSign && value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}%`;
}

/**
 * Format a gain/loss value with currency and percentage
 * 
 * @param eurValue - The EUR value
 * @param pctValue - The percentage value
 * @returns Formatted string (e.g., "+€3,234.50 (+26.95%)")
 */
export function formatGainLoss(eurValue: number, pctValue: number): string {
  const eurFormatted = formatCurrency(Math.abs(eurValue));
  const sign = eurValue >= 0 ? "+" : "-";
  const pctFormatted = formatPercentage(pctValue);
  
  return `${sign}${eurFormatted} (${pctFormatted})`;
}

/**
 * Get color for a gain/loss value
 * 
 * @param value - The value (positive = gain, negative = loss)
 * @returns Raycast Color
 */
export function getGainLossColor(value: number): Color {
  if (value > 0) {
    return Color.Green;
  } else if (value < 0) {
    return Color.Red;
  }
  return Color.SecondaryText;
}

/**
 * Format a date relative to now (e.g., "in 5 days", "yesterday")
 * 
 * @param dateString - ISO date string
 * @returns Relative date string
 */
export function formatRelativeDate(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffTime = date.getTime() - now.getTime();
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  
  if (diffDays === 0) {
    return "Today";
  } else if (diffDays === 1) {
    return "Tomorrow";
  } else if (diffDays === -1) {
    return "Yesterday";
  } else if (diffDays > 0) {
    return `in ${diffDays} days`;
  } else {
    return `${Math.abs(diffDays)} days ago`;
  }
}

/**
 * Format a full date (e.g., "January 30, 2025")
 * 
 * @param dateString - ISO date string
 * @returns Formatted date string
 */
export function formatFullDate(dateString: string): string {
  const date = new Date(dateString);
  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  }).format(date);
}

/**
 * Format a number with thousands separators
 * 
 * @param value - The number to format
 * @param decimals - Number of decimal places (default: 1)
 * @returns Formatted number string
 */
export function formatNumber(value: number, decimals = 1): string {
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

/**
 * Truncate a string to a maximum length with ellipsis
 * 
 * @param str - The string to truncate
 * @param maxLength - Maximum length (default: 50)
 * @returns Truncated string
 */
export function truncate(str: string, maxLength = 50): string {
  if (str.length <= maxLength) {
    return str;
  }
  return str.substring(0, maxLength - 3) + "...";
}

/**
 * Group events by time period
 * 
 * @param events - Array of events with days_until property
 * @returns Grouped events object
 */
export function groupEventsByTimePeriod<T extends { days_until: number }>(
  events: T[]
): {
  thisWeek: T[];
  nextWeek: T[];
  later: T[];
} {
  const thisWeek: T[] = [];
  const nextWeek: T[] = [];
  const later: T[] = [];
  
  events.forEach((event) => {
    if (event.days_until <= 7) {
      thisWeek.push(event);
    } else if (event.days_until <= 14) {
      nextWeek.push(event);
    } else {
      later.push(event);
    }
  });
  
  return { thisWeek, nextWeek, later };
}
