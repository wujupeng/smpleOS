import { Menu, app, BrowserWindow, shell } from 'electron'

export function buildApplicationMenu(): Menu | null {
  const template: Electron.MenuItemConstructorOptions[] = [
    {
      label: '文件',
      submenu: [
        {
          label: '新建项目',
          accelerator: 'CmdOrCtrl+N',
          click: (_menuItem, win) => {
            win?.webContents.send('menu:action', 'new-project')
          },
        },
        {
          label: '打开项目',
          accelerator: 'CmdOrCtrl+O',
          click: (_menuItem, win) => {
            win?.webContents.send('menu:action', 'open-project')
          },
        },
        { type: 'separator' },
        {
          label: '导出报告',
          accelerator: 'CmdOrCtrl+E',
          click: (_menuItem, win) => {
            win?.webContents.send('menu:action', 'export-report')
          },
        },
        { type: 'separator' },
        { role: 'close' },
      ],
    },
    {
      label: '编辑',
      submenu: [
        { role: 'undo', label: '撤销' },
        { role: 'redo', label: '重做' },
        { type: 'separator' },
        { role: 'cut', label: '剪切' },
        { role: 'copy', label: '复制' },
        { role: 'paste', label: '粘贴' },
        { role: 'selectAll', label: '全选' },
      ],
    },
    {
      label: '视图',
      submenu: [
        {
          label: '设计中心',
          accelerator: 'CmdOrCtrl+1',
          click: (_menuItem, win) => {
            win?.webContents.send('menu:action', 'navigate:/design')
          },
        },
        {
          label: 'CAE 分析',
          accelerator: 'CmdOrCtrl+2',
          click: (_menuItem, win) => {
            win?.webContents.send('menu:action', 'navigate:/cae')
          },
        },
        {
          label: '数字孪生',
          accelerator: 'CmdOrCtrl+3',
          click: (_menuItem, win) => {
            win?.webContents.send('menu:action', 'navigate:/twin')
          },
        },
        {
          label: 'PLM 变更',
          accelerator: 'CmdOrCtrl+4',
          click: (_menuItem, win) => {
            win?.webContents.send('menu:action', 'navigate:/plm')
          },
        },
        {
          label: 'PLM/BOM',
          accelerator: 'CmdOrCtrl+5',
          click: (_menuItem, win) => {
            win?.webContents.send('menu:action', 'navigate:/bom')
          },
        },
        {
          label: 'MES',
          accelerator: 'CmdOrCtrl+6',
          click: (_menuItem, win) => {
            win?.webContents.send('menu:action', 'navigate:/mes')
          },
        },
        { type: 'separator' },
        { role: 'reload', label: '刷新' },
        { role: 'forceReload', label: '强制刷新' },
        { role: 'toggleDevTools', label: '开发者工具' },
        { type: 'separator' },
        { role: 'resetZoom', label: '重置缩放' },
        { role: 'zoomIn', label: '放大' },
        { role: 'zoomOut', label: '缩小' },
        { type: 'separator' },
        { role: 'togglefullscreen', label: '全屏' },
      ],
    },
    {
      label: '工具',
      submenu: [
        {
          label: '服务器配置',
          click: (_menuItem, win) => {
            win?.webContents.send('menu:action', 'server-config')
          },
        },
        { type: 'separator' },
        {
          label: 'CAE 求解器配置',
          click: (_menuItem, win) => {
            win?.webContents.send('menu:action', 'cae-solver-config')
          },
        },
        {
          label: '数据备份',
          click: (_menuItem, win) => {
            win?.webContents.send('menu:action', 'data-backup')
          },
        },
      ],
    },
    {
      label: '帮助',
      submenu: [
        {
          label: 'AeroForge-X 文档',
          click: () => {
            shell.openExternal('https://docs.aeroforge-x.io')
          },
        },
        {
          label: 'API 参考',
          click: () => {
            shell.openExternal('https://api.aeroforge-x.io')
          },
        },
        { type: 'separator' },
        {
          label: '检查更新',
          click: (_menuItem, win) => {
            win?.webContents.send('menu:action', 'check-update')
          },
        },
        { type: 'separator' },
        {
          label: `关于 AeroForge-X`,
          click: (_menuItem, win) => {
            win?.webContents.send('menu:action', 'about')
          },
        },
      ],
    },
  ]

  return Menu.buildFromTemplate(template)
}