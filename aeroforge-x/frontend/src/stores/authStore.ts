import { create } from 'zustand'
import apiClient from '../services/apiClient'

interface AuthState {
  token: string | null
  username: string | null
  roles: string[]
  isAuthenticated: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem('aeroforge_token'),
  username: localStorage.getItem('aeroforge_username'),
  roles: JSON.parse(localStorage.getItem('aeroforge_roles') || '[]'),
  isAuthenticated: !!localStorage.getItem('aeroforge_token'),

  login: async (username: string, password: string) => {
    const response = await apiClient.post('/auth/login', { username, password })
    const { token, roles } = response.data.data
    localStorage.setItem('aeroforge_token', token)
    localStorage.setItem('aeroforge_username', username)
    localStorage.setItem('aeroforge_roles', JSON.stringify(roles))
    set({ token, username, roles, isAuthenticated: true })
  },

  logout: () => {
    localStorage.removeItem('aeroforge_token')
    localStorage.removeItem('aeroforge_username')
    localStorage.removeItem('aeroforge_roles')
    set({ token: null, username: null, roles: [], isAuthenticated: false })
  },
}))