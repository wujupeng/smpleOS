const QUEUE_KEY = 'aeroforge-offline-queue'

interface OfflineAction {
  id: string
  url: string
  method: string
  body: unknown
  timestamp: number
  retryCount: number
}

export class OfflineQueue {
  static enqueue(url: string, method: string, body: unknown): void {
    const queue = this.getAll()
    queue.push({
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      url,
      method,
      body,
      timestamp: Date.now(),
      retryCount: 0,
    })
    localStorage.setItem(QUEUE_KEY, JSON.stringify(queue))
  }

  static getAll(): OfflineAction[] {
    try {
      return JSON.parse(localStorage.getItem(QUEUE_KEY) || '[]')
    } catch {
      return []
    }
  }

  static remove(id: string): void {
    const queue = this.getAll().filter(item => item.id !== id)
    localStorage.setItem(QUEUE_KEY, JSON.stringify(queue))
  }

  static async flush(): Promise<{ success: number; failed: number }> {
    const queue = this.getAll()
    let success = 0
    let failed = 0

    for (const item of queue) {
      try {
        const response = await fetch(item.url, {
          method: item.method,
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(item.body),
        })
        if (response.ok) {
          this.remove(item.id)
          success++
        } else {
          item.retryCount++
          failed++
        }
      } catch {
        item.retryCount++
        failed++
      }
    }

    localStorage.setItem(QUEUE_KEY, JSON.stringify(queue))
    return { success, failed }
  }

  static get count(): number {
    return this.getAll().length
  }
}

export function requestWithOffline(url: string, method: string, body: unknown): Promise<Response> {
  if (navigator.onLine) {
    return fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
  }

  if (method !== 'GET') {
    OfflineQueue.enqueue(url, method, body)
  }

  return Promise.resolve(new Response(JSON.stringify({ queued: true, offline: true }), {
    status: 202,
    headers: { 'Content-Type': 'application/json' },
  }))
}