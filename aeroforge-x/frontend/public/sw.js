const CACHE_NAME = 'aeroforge-v1'
const APP_SHELL = [
  '/',
  '/index.html',
  '/manifest.json',
]

const DATA_CACHE = 'aeroforge-data-v1'
const API_CACHE_DURATION = 5 * 60 * 1000

const API_ROUTES = [
  '/api/supply/',
  '/api/mes/',
  '/api/qms/',
  '/api/analytics/',
  '/api/twins/',
  '/api/ai/',
]

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL))
  )
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME && key !== DATA_CACHE)
          .map((key) => caches.delete(key))
      )
    )
  )
  self.clients.claim()
})

self.addEventListener('fetch', (event) => {
  const { request } = event
  const url = new URL(request.url)

  if (request.method !== 'GET') return

  const isApi = API_ROUTES.some((route) => url.pathname.startsWith(route))

  if (isApi) {
    event.respondWith(networkFirstWithCache(request))
  } else {
    event.respondWith(cacheFirstWithNetwork(request))
  }
})

async function networkFirstWithCache(request: Request): Promise<Response> {
  try {
    const response = await fetch(request)
    if (response.ok) {
      const cache = await caches.open(DATA_CACHE)
      cache.put(request, response.clone())
    }
    return response
  } catch {
    const cached = await caches.match(request)
    if (cached) return cached
    return new Response(JSON.stringify({ error: 'offline' }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' },
    })
  }
}

async function cacheFirstWithNetwork(request: Request): Promise<Response> {
  const cached = await caches.match(request)
  if (cached) return cached

  try {
    const response = await fetch(request)
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME)
      cache.put(request, response.clone())
    }
    return response
  } catch {
    return new Response('Offline', { status: 503 })
  }
}

self.addEventListener('push', (event) => {
  const data = event.data?.json() ?? { title: 'AeroForge-X', body: 'New notification' }
  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: '/icons/icon-192x192.png',
      badge: '/icons/icon-72x72.png',
      data: data.url ? { url: data.url } : undefined,
    })
  )
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const url = event.notification.data?.url || '/'
  event.waitUntil(
    self.clients.matchAll({ type: 'window' }).then((clients) => {
      const client = clients.find((c) => c.url.includes(self.location.origin))
      if (client) {
        client.navigate(url)
        client.focus()
      } else {
        self.clients.openWindow(url)
      }
    })
  )
})