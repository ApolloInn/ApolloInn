import '../styles/Sidebar.css'
import packageJson from '../../package.json'
import { useState, useEffect } from 'react'
import UpdateModal from './UpdateModal'

interface SidebarProps {
  currentPage: 'home' | 'accounts' | 'settings' | 'system' | 'database' | 'mac' | 'docs'
  onPageChange: (page: 'home' | 'accounts' | 'settings' | 'system' | 'database' | 'mac' | 'docs') => void
  tokensCount?: number
  updateInfo?: {
    hasUpdate: boolean
    currentVersion?: string
    latestVersion?: string
    releaseUrl?: string
    releaseNotes?: string
    manualDownload?: boolean
  }
}

const Sidebar: React.FC<SidebarProps> = ({ currentPage, onPageChange, tokensCount = 0, updateInfo }) => {
  const [isDownloading, setIsDownloading] = useState(false)
  const [isDownloaded, setIsDownloaded] = useState(false)
  const [downloadProgress, setDownloadProgress] = useState<number>(0)
  const [error, setError] = useState<string>('')
  const [showUpdateModal, setShowUpdateModal] = useState(false)

  useEffect(() => {
    if (!window.electronAPI) return

    // 监听下载进度
    const unsubProgress = window.electronAPI.onUpdateDownloadProgress?.((progress) => {
      setIsDownloading(true)
      setDownloadProgress(progress.percent)
      setError('')
    })

    // 监听下载完成
    const unsubDownloaded = window.electronAPI.onUpdateDownloaded?.(() => {
      setIsDownloading(false)
      setIsDownloaded(true)
      setError('')
    })

    // 监听错误
    const unsubError = window.electronAPI.onUpdateError?.((errorMsg) => {
      console.error('更新错误:', errorMsg)
      setIsDownloading(false)
      setIsDownloaded(false)
      setError('更新失败')
      
      // 3秒后清除错误，恢复显示"发现新版本"
      setTimeout(() => {
        setError('')
      }, 3000)
    })

    return () => {
      unsubProgress?.()
      unsubDownloaded?.()
      unsubError?.()
    }
  }, [])

  // 点击侧边栏更新提示 - 打开更新弹窗
  const handleUpdateClick = () => {
    setShowUpdateModal(true)
  }

  // 在弹窗中点击下载
  const handleDownload = async () => {
    console.log('开始下载更新...')
    setIsDownloading(true)
    setError('')
    
    try {
      const result = await window.electronAPI.downloadUpdate()
      console.log('下载结果:', result)
      
      if (!result.success) {
        console.error('下载失败:', result.error)
        setIsDownloading(false)
        setError('下载失败，请稍后重试')
      }
    } catch (err: any) {
      console.error('下载异常:', err)
      setIsDownloading(false)
      setError('下载异常，请稍后重试')
    }
  }

  // 在弹窗中点击安装
  const handleInstall = async () => {
    console.log('执行安装...')
    try {
      await window.electronAPI.installUpdate()
    } catch (err) {
      console.error('安装失败:', err)
      setError('安装失败')
    }
  }

  // 打开发布页面
  const handleOpenUrl = () => {
    if (updateInfo?.releaseUrl) {
      window.open(updateInfo.releaseUrl, '_blank')
    }
  }
  const version = `v${packageJson.version}`
  return (
    <div className="sidebar-container">
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <div className="logo-icon">C</div>
          <div className="logo-text">
            <span className="logo-title">Yuan</span>
            <span className="logo-subtitle">账号管理器</span>
          </div>
        </div>
      </div>

      <nav className="sidebar-nav">
        <div className="nav-section">
          <button
            className={`nav-item ${currentPage === 'home' ? 'active' : ''}`}
            onClick={() => onPageChange('home')}
          >
            <span className="nav-icon">🏠</span>
            <span className="nav-label">主页</span>
          </button>

          <button
            className={`nav-item ${currentPage === 'accounts' ? 'active' : ''}`}
            onClick={() => onPageChange('accounts')}
          >
            <span className="nav-icon">👥</span>
            <span className="nav-label">账号管理</span>
            {tokensCount > 0 && (
              <span className="nav-badge">{tokensCount}</span>
            )}
          </button>

          <button
            className={`nav-item ${currentPage === 'settings' ? 'active' : ''}`}
            onClick={() => onPageChange('settings')}
          >
            <span className="nav-icon">⚙️</span>
            <span className="nav-label">设置</span>
          </button>

          <button
            className={`nav-item ${currentPage === 'database' ? 'active' : ''}`}
            onClick={() => onPageChange('database')}
          >
            <span className="nav-icon">🛠️</span>
            <span className="nav-label">环境管理</span>
          </button>

          <button
            className={`nav-item ${currentPage === 'system' ? 'active' : ''}`}
            onClick={() => onPageChange('system')}
          >
            <span className="nav-icon">🔧</span>
            <span className="nav-label">系统管理</span>
          </button>

          <button
            className={`nav-item ${currentPage === 'mac' ? 'active' : ''}`}
            onClick={() => onPageChange('mac')}
          >
            <span className="nav-icon">🍎</span>
            <span className="nav-label">Mac管理</span>
            <span className="nav-badge-wip">待完成</span>
          </button>

          <button
            className={`nav-item ${currentPage === 'docs' ? 'active' : ''}`}
            onClick={() => onPageChange('docs')}
          >
            <span className="nav-icon">📖</span>
            <span className="nav-label">文档</span>
          </button>
        </div>

        <div className="nav-footer">
          {updateInfo?.hasUpdate ? (
            <div 
              className="sidebar-update-notice" 
              onClick={handleUpdateClick}
              style={{ 
                cursor: 'pointer',
                opacity: 1
              }}
              title="点击查看更新详情"
            >
              {isDownloaded ? (
                <>
                  <div className="update-icon">✅</div>
                  <div className="update-content">
                    <div className="update-title">点击安装</div>
                    <div className="update-version">{updateInfo.latestVersion}</div>
                  </div>
                </>
              ) : isDownloading ? (
                <>
                  <div className="update-icon">⏬</div>
                  <div className="update-content">
                    <div className="update-title">下载中...</div>
                    <div className="update-version">{downloadProgress.toFixed(0)}%</div>
                  </div>
                </>
              ) : (
                <>
                  <div className="update-icon">🎉</div>
                  <div className="update-content">
                    <div className="update-title">发现新版本</div>
                    <div className="update-version">{updateInfo.latestVersion}</div>
                  </div>
                </>
              )}
            </div>
          ) : (
            <div className="sidebar-version">{version}</div>
          )}
        </div>
      </nav>

      {/* 更新详情弹窗 */}
      <UpdateModal
        show={showUpdateModal}
        currentVersion={updateInfo?.currentVersion || version}
        latestVersion={updateInfo?.latestVersion}
        releaseNotes={updateInfo?.releaseNotes}
        releaseUrl={updateInfo?.releaseUrl}
        manualDownload={updateInfo?.manualDownload}
        isDownloading={isDownloading}
        isDownloaded={isDownloaded}
        downloadProgress={downloadProgress}
        error={error}
        onClose={() => setShowUpdateModal(false)}
        onDownload={handleDownload}
        onInstall={handleInstall}
        onOpenUrl={handleOpenUrl}
      />
    </div>
  )
}

export default Sidebar
