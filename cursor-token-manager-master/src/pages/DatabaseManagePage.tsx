import React, { useState, useEffect } from 'react'
import '../styles/DatabaseManagePage.css'

interface Token {
  id: string
  name: string
  token: string
  isActive: boolean
  accountInfo?: {
    email?: string
    plan?: string
    id?: string
  }
}

interface DatabaseInfo {
  dbPath: string
  dbSize: number
  dbSizeFormatted: string
  globalStoragePath: string
  globalStorageSize: number
  globalStorageSizeFormatted: string
  lastModified: string
}

interface DatabaseManagePageProps {
  tokens?: Token[]
  onShowDialog?: (options: {
    title?: string
    message: string
    type?: 'info' | 'confirm' | 'warning' | 'error'
    onConfirm?: () => void
    onCancel?: () => void
    confirmText?: string
    cancelText?: string
  }) => void
}

const DatabaseManagePage: React.FC<DatabaseManagePageProps> = ({ tokens = [], onShowDialog }) => {
  // 数据库管理状态
  const [dbInfo, setDbInfo] = useState<DatabaseInfo | null>(null)
  const [dbLoading, setDbLoading] = useState(false)
  const [selectedAccountId, setSelectedAccountId] = useState<string>('')
  const [resetProgress, setResetProgress] = useState<{ step: string; progress: number; message: string } | null>(null)
  const [isResetting, setIsResetting] = useState(false)
  
  // 高级工具状态
  const [toolStatus, setToolStatus] = useState<{
    isProcessing: boolean
    message: string
    type: 'success' | 'error' | 'info' | null
  }>({
    isProcessing: false,
    message: '',
    type: null
  })

  // 默认选中当前激活的账号
  useEffect(() => {
    const activeToken = tokens.find(t => t.isActive)
    if (activeToken && !selectedAccountId) {
      setSelectedAccountId(activeToken.id)
    }
  }, [tokens])

  // 获取数据库信息
  const handleGetDatabaseInfo = async () => {
    setDbLoading(true)
    try {
      const result = await window.electronAPI.getDatabaseInfo()
      if (result.success && result.info) {
        setDbInfo(result.info)
      } else {
        onShowDialog?.({
          title: '错误',
          message: result.error || '获取数据库信息失败',
          type: 'error',
          onConfirm: () => {}
        })
      }
    } catch (error: any) {
      onShowDialog?.({
        title: '错误',
        message: error.message || '获取数据库信息失败',
        type: 'error',
        onConfirm: () => {}
      })
    } finally {
      setDbLoading(false)
    }
  }

  // 重置数据库
  const handleResetDatabase = () => {
    onShowDialog?.({
      title: '⚠️ 危险操作确认',
      message: `确定要重置 Cursor 数据库吗？\n\n此操作将：\n1. 删除 Cursor 数据库文件\n2. 删除 storage.json（包含机器码）\n3. 重启 Cursor 创建新数据库\n${selectedAccountId ? '4. 写入选中的账号信息\n5. 重置机器码后再次重启' : ''}\n\n此操作不可撤销！`,
      type: 'warning',
      confirmText: '确认重置',
      cancelText: '取消',
      onConfirm: async () => {
        setIsResetting(true)
        setResetProgress({ step: 'START', progress: 0, message: '准备重置...' })
        
        try {
          const result = await window.electronAPI.resetDatabase(selectedAccountId || undefined)
          if (!result.success) {
            onShowDialog?.({
              title: '错误',
              message: result.error || '重置数据库失败',
              type: 'error',
              onConfirm: () => {}
            })
          }
        } catch (error: any) {
          onShowDialog?.({
            title: '错误',
            message: error.message || '重置数据库失败',
            type: 'error',
            onConfirm: () => {}
          })
        } finally {
          setTimeout(() => {
            setIsResetting(false)
            setResetProgress(null)
            // 重新获取数据库信息
            handleGetDatabaseInfo()
          }, 2000)
        }
      },
      onCancel: () => {}
    })
  }

  // 监听数据库重置进度
  useEffect(() => {
    if (!window.electronAPI?.onDatabaseResetProgress) return
    
    const cleanup = window.electronAPI.onDatabaseResetProgress((data) => {
      setResetProgress(data)
      if (data.step === 'DONE') {
        onShowDialog?.({
          title: '成功',
          message: '数据库重置完成！Cursor 已重新启动。',
          type: 'info',
          onConfirm: () => {}
        })
      }
    })
    
    return () => cleanup?.()
  }, [])

  // 重置机器码
  const handleResetMachineId = async () => {
    if (!window.electronAPI) return
    
    setToolStatus({
      isProcessing: true,
      message: '正在重置机器码（包括 main.js 补丁）...',
      type: 'info'
    })
    
    try {
      const result = await window.electronAPI.resetMachineId()
      
      if (result.success) {
        setToolStatus({
          isProcessing: false,
          message: '✓ 机器码已重置！storage.json 已更新，main.js 已打补丁（如找到），请重启 Cursor 生效。',
          type: 'success'
        })
      } else {
        setToolStatus({
          isProcessing: false,
          message: `✗ 重置失败：${result.error || '未知错误'}`,
          type: 'error'
        })
      }
      
      setTimeout(() => {
        setToolStatus({ isProcessing: false, message: '', type: null })
      }, 5000)
    } catch (error: any) {
      setToolStatus({
        isProcessing: false,
        message: `✗ 操作失败：${error.message || '未知错误'}`,
        type: 'error'
      })
      
      setTimeout(() => {
        setToolStatus({ isProcessing: false, message: '', type: null })
      }, 5000)
    }
  }

  // 清理历史会话
  const handleClearHistory = async () => {
    if (!window.electronAPI) return
    
    onShowDialog?.({
      title: '⚠️ 警告',
      message: '此操作将清除所有历史记录和工作区存储，并删除 Cursor 数据库。\n\n这将会：\n1. 清除所有聊天历史\n2. 清除工作区存储\n3. 删除 state.vscdb 数据库\n4. 自动关闭 Cursor 进程\n\n是否继续？',
      type: 'warning',
      confirmText: '确认清理',
      cancelText: '取消',
      onConfirm: async () => {
        setToolStatus({
          isProcessing: true,
          message: '正在清理历史会话...',
          type: 'info'
        })
        
        try {
          const result = await window.electronAPI.clearHistory()
          
          if (result.success) {
            setToolStatus({
              isProcessing: false,
              message: '✓ 历史会话已清除！Cursor 已关闭，请重新启动。',
              type: 'success'
            })
          } else {
            setToolStatus({
              isProcessing: false,
              message: `✗ 清理失败：${result.error || '未知错误'}`,
              type: 'error'
            })
          }
          
          setTimeout(() => {
            setToolStatus({ isProcessing: false, message: '', type: null })
          }, 5000)
        } catch (error: any) {
          setToolStatus({
            isProcessing: false,
            message: `✗ 操作失败：${error.message || '未知错误'}`,
            type: 'error'
          })
          
          setTimeout(() => {
            setToolStatus({ isProcessing: false, message: '', type: null })
          }, 5000)
        }
      },
      onCancel: () => {}
    })
  }

  // 页面加载时自动获取数据库信息
  useEffect(() => {
    handleGetDatabaseInfo()
  }, [])

  return (
    <div className="database-manage-page">
      <div className="page-header">
        <div>
          <h1 className="page-title">环境管理</h1>
          <p className="page-subtitle">管理 Cursor 运行环境和本地数据</p>
        </div>
      </div>

      <div className="page-content">
        {/* 高级工具卡片 */}
        <div className="db-section">
          <div className="section-header">
            <h3 className="section-title">🔧 高级工具</h3>
          </div>
          
          <div className="tools-card">
            <p className="tools-desc">以下操作会直接修改 Cursor 配置，请谨慎使用。</p>
            
            <div className="tools-grid">
              <div className="tool-item">
                <div className="tool-header">
                  <span className="tool-icon">🔄</span>
                  <h4>重置机器码</h4>
                </div>
                <p className="tool-desc">从根源重置你的"数字身份"，修改设备标识并对 main.js 打补丁</p>
                <ul className="tool-details">
                  <li>修改 storage.json 中的设备标识</li>
                  <li>对 main.js 打补丁，防止读取真实硬件信息</li>
                  <li>自动备份原始 main.js 文件</li>
                </ul>
                <button
                  className="tool-btn"
                  onClick={handleResetMachineId}
                  disabled={toolStatus.isProcessing}
                >
                  {toolStatus.isProcessing ? '处理中...' : '🔄 重置机器码'}
                </button>
              </div>
              
              <div className="tool-item danger">
                <div className="tool-header">
                  <span className="tool-icon">🗑️</span>
                  <h4>清理历史会话</h4>
                </div>
                <p className="tool-desc">安全高效的无痕清理，清空聊天历史和工作区存储</p>
                <ul className="tool-details">
                  <li>清空 History 和 workspaceStorage 目录</li>
                  <li>删除 state.vscdb 数据库及其备份</li>
                  <li>自动关闭 Cursor 进程</li>
                  <li>不会删除个人设置和扩展</li>
                </ul>
                <button
                  className="tool-btn danger"
                  onClick={handleClearHistory}
                  disabled={toolStatus.isProcessing}
                >
                  {toolStatus.isProcessing ? '处理中...' : '🗑️ 清理历史会话'}
                </button>
              </div>
            </div>
            
            {toolStatus.message && (
              <div className={`tool-status ${toolStatus.type}`}>
                {toolStatus.message}
              </div>
            )}
          </div>
        </div>

        {/* 数据库信息卡片 */}
        <div className="db-section">
          <div className="section-header">
            <h3 className="section-title">📊 数据库信息</h3>
            <button 
              className="btn-refresh-db"
              onClick={handleGetDatabaseInfo}
              disabled={dbLoading}
            >
              {dbLoading ? '检测中...' : '🔍 重新检测'}
            </button>
          </div>
          
          <div className="db-info-card">
            {dbInfo ? (
              <div className="db-info-grid">
                <div className="db-info-item">
                  <div className="db-info-icon">📁</div>
                  <div className="db-info-content">
                    <span className="db-info-label">数据库路径</span>
                    <span className="db-info-value path">{dbInfo.dbPath}</span>
                  </div>
                </div>
                
                <div className="db-info-item">
                  <div className="db-info-icon">💾</div>
                  <div className="db-info-content">
                    <span className="db-info-label">数据库大小</span>
                    <span className="db-info-value">{dbInfo.dbSizeFormatted}</span>
                  </div>
                </div>
                
                <div className="db-info-item">
                  <div className="db-info-icon">📦</div>
                  <div className="db-info-content">
                    <span className="db-info-label">存储目录大小</span>
                    <span className="db-info-value">{dbInfo.globalStorageSizeFormatted}</span>
                  </div>
                </div>
                
                <div className="db-info-item">
                  <div className="db-info-icon">🕐</div>
                  <div className="db-info-content">
                    <span className="db-info-label">最后修改时间</span>
                    <span className="db-info-value">{dbInfo.lastModified}</span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="db-info-empty">
                <div className="empty-icon">🗄️</div>
                <p>点击"重新检测"获取数据库信息</p>
              </div>
            )}
          </div>
        </div>

        {/* 重置数据库卡片 */}
        <div className="db-section danger-section">
          <div className="section-header">
            <h3 className="section-title danger">⚠️ 重置数据库</h3>
          </div>
          
          <div className="reset-card">
            <div className="reset-warning">
              <div className="warning-icon">⚠️</div>
              <div className="warning-content">
                <h4>危险操作</h4>
                <p>此操作将删除 Cursor 数据库并重新创建。所有本地缓存、会话数据和机器码将被清除。</p>
              </div>
            </div>
            
            <div className="reset-steps">
              <h4>重置流程：</h4>
              <ol>
                <li>关闭 Cursor 进程</li>
                <li>删除数据库文件 (state.vscdb)</li>
                <li>删除存储配置 (storage.json)</li>
                <li>启动 Cursor 创建新数据库</li>
                {selectedAccountId && (
                  <>
                    <li>再次关闭 Cursor</li>
                    <li>写入选中账号信息</li>
                    <li>重置机器码</li>
                    <li>重新启动 Cursor</li>
                  </>
                )}
              </ol>
            </div>
            
            <div className="reset-form">
              <div className="form-group">
                <label>重置后写入账号（可选）</label>
                <select 
                  value={selectedAccountId}
                  onChange={(e) => setSelectedAccountId(e.target.value)}
                  disabled={isResetting}
                >
                  <option value="">-- 不写入账号，仅重置 --</option>
                  {tokens.map(token => (
                    <option key={token.id} value={token.id}>
                      {token.accountInfo?.email || token.name || '未命名账号'}
                      {token.isActive ? ' (当前使用)' : ''}
                    </option>
                  ))}
                </select>
                <p className="form-hint">选择账号后，重置完成会自动写入该账号信息并重置机器码</p>
              </div>
              
              <button 
                className="btn-reset-db"
                onClick={handleResetDatabase}
                disabled={isResetting}
              >
                {isResetting ? '重置中...' : '🗑️ 重置数据库'}
              </button>
            </div>
            
            {resetProgress && (
              <div className="reset-progress">
                <div className="progress-header">
                  <span className="progress-step">{resetProgress.message}</span>
                  <span className="progress-percent">{resetProgress.progress}%</span>
                </div>
                <div className="progress-bar">
                  <div 
                    className="progress-fill"
                    style={{ width: `${resetProgress.progress}%` }}
                  />
                </div>
              </div>
            )}
          </div>
        </div>

        {/* 说明卡片 */}
        <div className="db-section">
          <div className="section-header">
            <h3 className="section-title">💡 使用说明</h3>
          </div>
          
          <div className="help-card">
            <div className="help-item">
              <h4>什么时候需要重置数据库？</h4>
              <ul>
                <li>Cursor 出现登录问题或账号异常</li>
                <li>切换账号后仍显示旧账号信息</li>
                <li>需要彻底清除本地缓存和会话</li>
                <li>遇到"设备数量超限"等问题</li>
              </ul>
            </div>
            
            <div className="help-item">
              <h4>重置数据库会清除什么？</h4>
              <ul>
                <li>state.vscdb - Cursor 主数据库</li>
                <li>storage.json - 包含机器码等配置</li>
                <li>所有本地登录状态和缓存</li>
              </ul>
            </div>
            
            <div className="help-item">
              <h4>注意事项</h4>
              <ul>
                <li>重置前请确保已保存重要的工作</li>
                <li>重置后需要重新登录或切换账号</li>
                <li>选择写入账号可以自动完成登录配置</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default DatabaseManagePage

