import { contextBridge, ipcRenderer } from 'electron'

const electronAPI = {
  getAppVersion: () => ipcRenderer.invoke('app:get-version'),
  getPlatform: () => ipcRenderer.invoke('app:get-platform'),
  showOpenDialog: (options: Electron.OpenDialogOptions) => ipcRenderer.invoke('dialog:open', options),
  showSaveDialog: (options: Electron.SaveDialogOptions) => ipcRenderer.invoke('dialog:save', options),
  readFile: (filePath: string) => ipcRenderer.invoke('file:read', filePath),
  writeFile: (filePath: string, content: string) => ipcRenderer.invoke('file:write', filePath, content),
  openExternal: (url: string) => ipcRenderer.invoke('shell:open-external', url),
  onMenuAction: (callback: (action: string) => void) => {
    ipcRenderer.on('menu:action', (_event, action) => callback(action))
  },
  getServerConfig: () => ipcRenderer.invoke('config:get-server'),
  setServerConfig: (config: { host: string; port: number }) => ipcRenderer.invoke('config:set-server', config),
}

contextBridge.exposeInMainWorld('electronAPI', electronAPI)

export type ElectronAPI = typeof electronAPI