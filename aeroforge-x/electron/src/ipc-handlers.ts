import { ipcMain, app, dialog, shell } from 'electron'
import * as fs from 'fs'
import * as path from 'path'

interface ServerConfig {
  host: string
  port: number
}

const CONFIG_FILE = path.join(app.getPath('userData'), 'server-config.json')

const DEFAULT_CONFIG: ServerConfig = {
  host: 'localhost',
  port: 8000,
}

function loadConfig(): ServerConfig {
  try {
    if (fs.existsSync(CONFIG_FILE)) {
      const raw = fs.readFileSync(CONFIG_FILE, 'utf-8')
      return { ...DEFAULT_CONFIG, ...JSON.parse(raw) }
    }
  } catch {
    // ignore
  }
  return { ...DEFAULT_CONFIG }
}

function saveConfig(config: ServerConfig): void {
  try {
    fs.writeFileSync(CONFIG_FILE, JSON.stringify(config, null, 2), 'utf-8')
  } catch {
    // ignore
  }
}

export function registerIpcHandlers(): void {
  ipcMain.handle('app:get-version', () => {
    return app.getVersion()
  })

  ipcMain.handle('app:get-platform', () => {
    return process.platform
  })

  ipcMain.handle('dialog:open', async (_event, options: Electron.OpenDialogOptions) => {
    const result = await dialog.showOpenDialog(options)
    return result
  })

  ipcMain.handle('dialog:save', async (_event, options: Electron.SaveDialogOptions) => {
    const result = await dialog.showSaveDialog(options)
    return result
  })

  ipcMain.handle('file:read', async (_event, filePath: string) => {
    try {
      const content = fs.readFileSync(filePath, 'utf-8')
      return { success: true, content }
    } catch (err) {
      return { success: false, error: String(err) }
    }
  })

  ipcMain.handle('file:write', async (_event, filePath: string, content: string) => {
    try {
      fs.writeFileSync(filePath, content, 'utf-8')
      return { success: true }
    } catch (err) {
      return { success: false, error: String(err) }
    }
  })

  ipcMain.handle('shell:open-external', async (_event, url: string) => {
    await shell.openExternal(url)
    return true
  })

  ipcMain.handle('config:get-server', () => {
    return loadConfig()
  })

  ipcMain.handle('config:set-server', (_event, config: ServerConfig) => {
    saveConfig(config)
    return true
  })
}