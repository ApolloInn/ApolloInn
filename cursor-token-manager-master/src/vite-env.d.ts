/// <reference types="vite/client" />

declare module '*/package.json' {
  interface PackageJson {
    name: string
    version: string
    releaseDate?: string
    description: string
    repository?: {
      type: string
      url: string
    }
    homepage?: string
    publish?: Array<{
      provider: string
      owner: string
      repo: string
    }>
    [key: string]: any
  }
  const value: PackageJson
  export default value
}

interface Window {
  electronAPI: {
    getTokens: () => Promise<any[]>
    saveToken: (token: { id: string; name: string; token: string; isActive: boolean; accountInfo?: any; usage?: any; createTime?: string }) => Promise<{ success: boolean }>
    deleteToken: (id: string) => Promise<{ success: boolean }>
    setActiveToken: (id: string) => Promise<{ success: boolean }>
    switchCursorAccount: (id: string, options?: { resetMachineId?: boolean, clearHistory?: boolean }) => Promise<{ success: boolean; error?: string; path?: string; needCursorPath?: boolean; message?: string }>
    getAccountInfo: (token: string) => Promise<{ success: boolean; accountInfo?: { email?: string; name?: string; username?: string; id?: string; plan?: string; avatar?: string; [key: string]: any }; error?: string; errorMessage?: string; endpoint?: string }>
    checkTokenUsage: (id: string) => Promise<{ success: boolean; usage?: { used: number; limit: number | null; remaining?: number | null; percentage: number | null }; error?: string }>
    fetchUsageDetails: (params: {
      cookieFormat: string
      startDate: string
      endDate: string
      page: number
      pageSize: number
      teamId: number
    }) => Promise<{ success: boolean; data?: { totalUsageEventsCount: number; usageEventsDisplay: any[] }; error?: string }>
    verifyToken: (token: string) => Promise<{ 
      success: boolean
      accountInfo?: any
      usage?: { used: number; limit: number | null; remaining: number | null; percentage: number | null }
      recentUsage?: { last7Days: number; totalAmount: number; lastUsageTime?: string }
      error?: string
    }>
    minimizeWindow: () => Promise<void>
    maximizeWindow: () => Promise<void>
    closeWindow: () => Promise<void>
    getSettings: () => Promise<{ cursorDbPath?: string; cursorAppPath?: string; batchRefreshSize?: number; switchResetMachineId?: boolean; switchClearHistory?: boolean; showSwitchProgress?: boolean; autoRefreshInterval?: number; autoRefreshEnabled?: boolean }>
    saveSettings: (settings: { cursorDbPath?: string; cursorAppPath?: string; batchRefreshSize?: number; switchResetMachineId?: boolean; switchClearHistory?: boolean; showSwitchProgress?: boolean; autoRefreshInterval?: number; autoRefreshEnabled?: boolean }) => Promise<{ success: boolean }>
    pickCursorAppPath: () => Promise<{ success: boolean; path?: string; error?: string }>
    scanCursorPaths: () => Promise<{ success: boolean; cursorAppPath?: string; cursorDbPath?: string; scannedPaths?: string[]; foundPaths?: string[]; error?: string }>
    syncCursorAccount: () => Promise<{ success: boolean; message?: string; error?: string; account?: { email: string; id: string } }>
    parseToken: (token: string) => Promise<{ success: boolean; parseResult?: any; error?: string; errorMessage?: string }>
    convertTokenToCookie: (token: string) => Promise<{ success: boolean; cookieFormat?: string; workosId?: string; message?: string; error?: string }>
    resetMachineId: () => Promise<{ success: boolean; error?: string; newIds?: any }>
    clearHistory: () => Promise<{ success: boolean; error?: string }>
    onSwitchAccountProgress: (callback: (data: { step: string; progress: number; message: string }) => void) => () => void
    checkForUpdates: () => Promise<{ success: boolean; hasUpdate?: boolean; currentVersion?: string; latestVersion?: string; releaseUrl?: string; releaseNotes?: string; publishedAt?: string; error?: string; manualDownload?: boolean }>
    downloadUpdate: () => Promise<{ success: boolean; error?: string }>
    installUpdate: () => Promise<{ success: boolean; error?: string }>
    onUpdateChecking: (callback: () => void) => () => void
    onUpdateAvailable: (callback: (info: any) => void) => () => void
    onUpdateNotAvailable: (callback: (info: any) => void) => () => void
    onUpdateDownloadProgress: (callback: (progress: { percent: number; bytesPerSecond: number; total: number; transferred: number }) => void) => () => void
    onUpdateDownloaded: (callback: (info: any) => void) => () => void
    onUpdateError: (callback: (error: string) => void) => () => void
    // 数据库管理
    getDatabaseInfo: () => Promise<{
      success: boolean
      info?: {
        dbPath: string
        dbSize: number
        dbSizeFormatted: string
        globalStoragePath: string
        globalStorageSize: number
        globalStorageSizeFormatted: string
        lastModified: string
      }
      error?: string
    }>
    resetDatabase: (accountId?: string) => Promise<{ success: boolean; error?: string }>
    onDatabaseResetProgress: (callback: (data: { step: string; progress: number; message: string }) => void) => () => void
    // 文档读取
    readDocFile?: (fileName: string) => Promise<{ success: boolean; content?: string; error?: string }>
  }
}
