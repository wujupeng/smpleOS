import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

import zhCN from './zh-CN/common.json'
import enUS from './en-US/common.json'

const RTL_LOCALES = ['ar', 'he', 'fa', 'ur']

function isRTL(locale: string): boolean {
  return RTL_LOCALES.some(rtl => locale.startsWith(rtl))
}

const savedLocale = localStorage.getItem('aeroforge-locale') || 'zh-CN'

i18n.use(initReactI18next).init({
  resources: {
    'zh-CN': { translation: zhCN },
    'en-US': { translation: enUS },
  },
  lng: savedLocale,
  fallbackLng: 'zh-CN',
  interpolation: {
    escapeValue: false,
  },
})

if (typeof document !== 'undefined') {
  document.documentElement.setAttribute('dir', isRTL(savedLocale) ? 'rtl' : 'ltr')
  document.documentElement.setAttribute('lang', savedLocale)
}

export default i18n

export function changeLocale(locale: string) {
  localStorage.setItem('aeroforge-locale', locale)
  i18n.changeLanguage(locale)
  const dir = isRTL(locale) ? 'rtl' : 'ltr'
  document.documentElement.setAttribute('dir', dir)
  document.documentElement.setAttribute('lang', locale)
  document.body.style.direction = dir
}

export function getCurrentLocale(): string {
  return i18n.language || 'zh-CN'
}

export function formatDate(date: Date | string, locale?: string): string {
  const d = typeof date === 'string' ? new Date(date) : date
  const lng = locale || getCurrentLocale()
  if (lng === 'zh-CN' || lng === 'zh-TW') {
    const y = d.getFullYear()
    const m = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    return `${y}年${m}月${day}日`
  }
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const y = d.getFullYear()
  return `${m}/${day}/${y}`
}

export function formatNumber(num: number, locale?: string): string {
  const lng = locale || getCurrentLocale()
  return new Intl.NumberFormat(lng === 'zh-CN' ? 'zh-CN' : 'en-US').format(num)
}

export function formatCurrency(amount: number, locale?: string): string {
  const lng = locale || getCurrentLocale()
  const currency = lng === 'zh-CN' ? 'CNY' : 'USD'
  return new Intl.NumberFormat(lng === 'zh-CN' ? 'zh-CN' : 'en-US', {
    style: 'currency',
    currency,
  }).format(amount)
}