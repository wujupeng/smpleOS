import { app, BrowserWindow, ipcMain, Menu, dialog, shell } from 'electron'
import * as path from 'path'
import { registerIpcHandlers } from './ipc-handlers'
import { buildApplicationMenu } from './menu'

const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged

let mainWindow: BrowserWindow | null = null

const MAIN_WINDOW_WIDTH = 1440
const MAIN_WINDOW_HEIGHT = 900
const MIN_WIDTH = 1024
const MIN_HEIGHT = 680

function createMainWindow(): BrowserWindow {
  const win = new BrowserWindow({
    width: MAIN_WINDOW_WIDTH,
    height: MAIN_WINDOW_HEIGHT,
    minWidth: MIN_WIDTH,
    minHeight: MIN_HEIGHT,
    title: 'AeroForge-X',
    icon: path.join(__dirname, '../assets/icon.png'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
      webSecurity: true,
    },
    show: false,
    backgroundColor: '#001529',
  })

  win.once('ready-to-show', () => {
    win.show()
    if (isDev) {
      win.webContents.openDevTools()
    }
  })

  win.on('closed', () => {
    mainWindow = null
  })

  win.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url)
    return { action: 'deny' }
  })

  if (isDev) {
    win.loadURL('http://localhost:3000')
  } else {
    const frontendPath = path.join(process.resourcesPath, 'frontend', 'dist', 'index.html')
    win.loadFile(frontendPath)
  }

  return win
}

app.whenReady().then(() => {
  registerIpcHandlers()
  Menu.setApplicationMenu(buildApplicationMenu())

  mainWindow = createMainWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      mainWindow = createMainWindow()
    } else if (mainWindow) {
      mainWindow.show()
    }
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

app.on('before-quit', () => {
  mainWindow = null
})

app.setAppUserModelId('com.aeroforge.desktop')