import { useEffect, useCallback } from 'react'

interface ElectronAPI {
  getAppVersion: () => Promise<string>
  getPlatform: () => Promise<string>
  showOpenDialog: (options: unknown) => Promise<unknown>
  showSaveDialog: (options: unknown) => Promise<unknown>
  readFile: (filePath: string) => Promise<{ success: boolean; content?: string; error?: string }>
  writeFile: (filePath: string, content: string) => Promise<{ success: boolean; error?: string }>
  openExternal: (url: string) => Promise<boolean>
  onMenuAction: (callback: (action: string) => void) => void
  getServerConfig: () => Promise<{ host: string; port: number }>
  setServerConfig: (config: { host: string; port: number }) => Promise<boolean>
}

declare global {
  interface Window {
    electronAPI?: ElectronAPI
  }
}

export function isElectron(): boolean {
  return !!(window && window.electronAPI)
}

export function useElectronMenu(onAction: (action: string) => void) {
  useEffect(() => {
    if (!window.electronAPI) return
    window.electronAPI.onMenuAction(onAction)
  }, [onAction])
}

export function useElectron() {
  const api = window.electronAPI

  const getAppVersion = useCallback(async () => {
    return api?.getAppVersion?.() ?? 'web'
  }, [api])

  const getPlatform = useCallback(async () => {
    return api?.getPlatform?.() ?? 'web'
  }, [api])

  const showOpenDialog = useCallback(async (options: unknown) => {
    return api?.showOpenDialog?.(options)
  }, [api])

  const showSaveDialog = useCallback(async (options: unknown) => {
    return api?.showSaveDialog?.(options)
  }, [api])

  const readFile = useCallback(async (filePath: string) => {
    return api?.readFile?.(filePath)
  }, [api])

  const writeFile = useCallback(async (filePath: string, content: string) => {
    return api?.writeFile?.(filePath, content)
  }, [api])

  const openExternal = useCallback(async (url: string) => {
    return api?.openExternal?.(url)
  }, [api])

  const getServerConfig = useCallback(async () => {
    return api?.getServerConfig?.() ?? { host: 'localhost', port: 8000 }
  }, [api])

  const setServerConfig = useCallback(async (config: { host: string; port: number }) => {
    return api?.setServerConfig?.(config)
  }, [api])

  return {
    isAvailable: !!api,
    getAppVersion,
    getPlatform,
    showOpenDialog,
    showSaveDialog,
    readFile,
    writeFile,
    openExternal,
    getServerConfig,
    setServerConfig,
  }
}