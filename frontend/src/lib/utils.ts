import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// Date formatting utilities
export function formatDate(date: string | Date, format: 'short' | 'long' | 'time' = 'short'): string {
  const dateObj = typeof date === 'string' ? new Date(date) : date

  switch (format) {
    case 'short':
      return dateObj.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      })
    case 'long':
      return dateObj.toLocaleDateString('en-US', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      })
    case 'time':
      return dateObj.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    default:
      return dateObj.toLocaleDateString()
  }
}

export function formatDateTime(date: string | Date): string {
  return formatDate(date, 'time')
}

export function getDaysUntil(date: string | Date): number {
  const targetDate = typeof date === 'string' ? new Date(date) : date
  const now = new Date()
  const diffTime = targetDate.getTime() - now.getTime()
  return Math.ceil(diffTime / (1000 * 60 * 60 * 24))
}

export function isOverdue(date: string | Date): boolean {
  return getDaysUntil(date) < 0
}

export function getRelativeTime(date: string | Date): string {
  const days = getDaysUntil(date)
  if (days === 0) return 'Today'
  if (days === 1) return 'Tomorrow'
  if (days === -1) return 'Yesterday'
  if (days > 0) return `In ${days} days`
  return `${Math.abs(days)} days ago`
}

// String utilities
export function capitalizeFirst(str: string): string {
  return str.charAt(0).toUpperCase() + str.slice(1)
}

export function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text
  return text.slice(0, maxLength) + '...'
}

export function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^\w\s-]/g, '')
    .replace(/[\s_-]+/g, '-')
    .replace(/^-+|-+$/g, '')
}

// Number utilities
export function formatNumber(num: number, decimals: number = 0): string {
  return num.toLocaleString('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })
}

export function formatCurrency(amount: number, currency: string = 'USD'): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
  }).format(amount)
}

export function formatPercentage(value: number, decimals: number = 1): string {
  return `${value.toFixed(decimals)}%`
}

// Color utilities based on priority or status
export function getStatusColor(status: string): string {
  const colorMap: Record<string, string> = {
    active: 'success',
    maintenance: 'warning',
    retired: 'danger',
    completed: 'success',
    pending: 'warning',
    cancelled: 'danger',
    overdue: 'danger',
    'due-soon': 'warning',
    'on-time': 'success',
  }
  return colorMap[status.toLowerCase()] || 'info'
}

export function getPriorityColor(priority: string): string {
  const colorMap: Record<string, string> = {
    low: 'info',
    medium: 'warning',
    high: 'danger',
    critical: 'danger',
  }
  return colorMap[priority.toLowerCase()] || 'info'
}

// Validation utilities
export function isValidEmail(email: string): boolean {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return emailRegex.test(email)
}

export function isValidPhone(phone: string): boolean {
  const phoneRegex = /^\+?[\d\s\-\(\)]+$/
  return phoneRegex.test(phone) && phone.length >= 10
}

// Array utilities
export function groupBy<T>(array: T[], key: keyof T): Record<string, T[]> {
  return array.reduce((groups, item) => {
    const group = String(item[key])
    groups[group] = groups[group] || []
    groups[group].push(item)
    return groups
  }, {} as Record<string, T[]>)
}

export function sortBy<T>(array: T[], key: keyof T, direction: 'asc' | 'desc' = 'asc'): T[] {
  return [...array].sort((a, b) => {
    const aVal = a[key]
    const bVal = b[key]
    let comparison = 0

    if (aVal < bVal) comparison = -1
    else if (aVal > bVal) comparison = 1

    return direction === 'desc' ? comparison * -1 : comparison
  })
}

// File utilities
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

export function downloadFile(data: Blob, filename: string): void {
  const url = window.URL.createObjectURL(data)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

// Local storage utilities
export function storageAvailable(type: 'localStorage' | 'sessionStorage' = 'localStorage'): boolean {
  try {
    const storage = window[type]
    const test = '__storage_test__'
    storage.setItem(test, test)
    storage.removeItem(test)
    return true
  } catch {
    return false
  }
}

export function safeStorageGet(key: string, defaultValue: any = null): any {
  if (!storageAvailable()) return defaultValue
  try {
    const item = localStorage.getItem(key)
    return item ? JSON.parse(item) : defaultValue
  } catch {
    return defaultValue
  }
}

export function safeStorageSet(key: string, value: any): void {
  if (!storageAvailable()) return
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch {
    // Silently fail if storage is full or unavailable
  }
}

export function safeStorageRemove(key: string): void {
  if (!storageAvailable()) return
  try {
    localStorage.removeItem(key)
  } catch {
    // Silently fail if storage is unavailable
  }
}

// URL utilities
export function buildUrl(base: string, params: Record<string, any>): string {
  const url = new URL(base)
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      url.searchParams.append(key, String(value))
    }
  })
  return url.toString()
}

// Debounce utility
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout
  return (...args: Parameters<T>) => {
    clearTimeout(timeout)
    timeout = setTimeout(() => func(...args), wait)
  }
}

// Throttle utility
export function throttle<T extends (...args: any[]) => any>(
  func: T,
  limit: number
): (...args: Parameters<T>) => void {
  let inThrottle: boolean
  return (...args: Parameters<T>) => {
    if (!inThrottle) {
      func(...args)
      inThrottle = true
      setTimeout(() => (inThrottle = false), limit)
    }
  }
}