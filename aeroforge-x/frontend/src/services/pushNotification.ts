const VAPID_PUBLIC_KEY = 'BEl62iUYgUivxIkv69yViEuiBIa-Ib9-SkvMeAtA3LFgDzkOs-GV3Wn5F0rGqP6R0sL4hY5Y5Y5Y5Y5Y5Y5Y5Y'

export class PushNotificationService {
  static async requestPermission(): Promise<boolean> {
    if (!('Notification' in window)) return false
    const result = await Notification.requestPermission()
    return result === 'granted'
  }

  static async subscribe(): Promise<PushSubscription | null> {
    if (!('serviceWorker' in navigator)) return null

    try {
      const registration = await navigator.serviceWorker.ready
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: VAPID_PUBLIC_KEY,
      })
      return subscription
    } catch {
      return null
    }
  }

  static async unsubscribe(): Promise<boolean> {
    if (!('serviceWorker' in navigator)) return false

    try {
      const registration = await navigator.serviceWorker.ready
      const subscription = await registration.pushManager.getSubscription()
      if (subscription) {
        return subscription.unsubscribe()
      }
      return false
    } catch {
      return false
    }
  }

  static async isSubscribed(): Promise<boolean> {
    if (!('serviceWorker' in navigator)) return false

    try {
      const registration = await navigator.serviceWorker.ready
      const subscription = await registration.pushManager.getSubscription()
      return subscription !== null
    } catch {
      return false
    }
  }

  static showLocal(title: string, body: string, url?: string): void {
    if (!('Notification' in window) || Notification.permission !== 'granted') return

    new Notification(title, {
      body,
      icon: '/icons/icon-192x192.png',
      badge: '/icons/icon-72x72.png',
      data: url ? { url } : undefined,
    })
  }
}