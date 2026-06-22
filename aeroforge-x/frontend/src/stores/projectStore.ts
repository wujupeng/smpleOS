import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import apiClient from '../services/apiClient'

interface ProjectInfo {
  id: string
  name: string
  code: string
  description: string
  tenant_id: string
  aircraft_type: string
  status: string
  spec_id: string
  settings: Record<string, unknown>
  members: Array<{ user_id: string; role: string; joined_at: string }>
  created_by: string
  created_at: string
}

interface ProjectState {
  currentProjectId: string | null
  currentProject: ProjectInfo | null
  projects: ProjectInfo[]
  loading: boolean

  setCurrentProject: (projectId: string | null) => void
  fetchProjects: (tenantId: string) => Promise<void>
  clearProjects: () => void
}

export const useProjectStore = create<ProjectState>()(
  persist(
    (set, get) => ({
      currentProjectId: null,
      currentProject: null,
      projects: [],
      loading: false,

      setCurrentProject: (projectId: string | null) => {
        const projects = get().projects
        const project = projects.find(p => p.id === projectId) || null
        set({ currentProjectId: projectId, currentProject: project })
      },

      fetchProjects: async (tenantId: string) => {
        set({ loading: true })
        try {
          const resp = await apiClient.get('/projects', { params: { tenant_id: tenantId } })
          const projects = resp.data?.data?.projects ?? []
          set({ projects, loading: false })
          const currentId = get().currentProjectId
          if (currentId) {
            const current = projects.find((p: ProjectInfo) => p.id === currentId)
            if (current) {
              set({ currentProject: current })
            }
          }
        } catch {
          set({ loading: false })
        }
      },

      clearProjects: () => {
        set({ projects: [], currentProjectId: null, currentProject: null })
      },
    }),
    {
      name: 'aeroforge-project-store',
      partialize: (state) => ({ currentProjectId: state.currentProjectId }),
    }
  )
)