import { useState, useMemo, useEffect, useRef, useCallback } from 'react'
import { Token, DialogOptions } from '../App'
import TokenList from '../components/TokenList'
import '../styles/AccountManagePage.css'

interface AccountManagePageProps {
  tokens: Token[]
  onAddAccount: () => void
  onEditToken: (token: Token) => void
  onDeleteToken: (id: string) => void
  onSetActive: (id: string) => void
  onRefreshUsage: (id: string) => void
  onShowUsageDetails: (token: Token) => void
  onShowVerification: () => void
  onSyncLocal: () => void
  onRefreshAll: () => void
  onClearFreeAccounts: () => void
  onShowDialog: (options: DialogOptions) => void
}

const AccountManagePage: React.FC<AccountManagePageProps> = ({
  tokens,
  onAddAccount,
  onEditToken,
  onDeleteToken,
  onSetActive,
  onRefreshUsage,
  onShowUsageDetails,
  onShowVerification,
  onSyncLocal,
  onRefreshAll,
  onClearFreeAccounts,
  onShowDialog
}) => {
  // 无限滚动相关
  const [displayCount, setDisplayCount] = useState(20)
  const loadMoreRef = useRef<HTMLDivElement>(null)
  const listContainerRef = useRef<HTMLDivElement>(null)
  
  // 筛选状态
  const [filterEmailSuffixes, setFilterEmailSuffixes] = useState<string[]>([])
  const [filterSubscription, setFilterSubscription] = useState<string>('all')
  const [filterExpiryDays, setFilterExpiryDays] = useState<string>('all')
  const [showFilters, setShowFilters] = useState(false)
  const [showEmailSuffixDropdown, setShowEmailSuffixDropdown] = useState(false)
  
  // 选择功能
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [selectTopCount, setSelectTopCount] = useState<string>('')
  const [isRefreshingSelected, setIsRefreshingSelected] = useState(false)
  
  const emailDropdownRef = useRef<HTMLDivElement>(null)
  
  // 点击外部关闭下拉框
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (emailDropdownRef.current && !emailDropdownRef.current.contains(event.target as Node)) {
        setShowEmailSuffixDropdown(false)
      }
    }
    
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // 获取所有邮箱后缀
  const emailSuffixes = useMemo(() => {
    const suffixes = new Set<string>()
    tokens.forEach(t => {
      const email = t.accountInfo?.email || ''
      const atIndex = email.lastIndexOf('@')
      if (atIndex > 0) {
        suffixes.add(email.substring(atIndex + 1).toLowerCase())
      }
    })
    return Array.from(suffixes).sort()
  }, [tokens])

  // 获取所有订阅状态
  const subscriptionTypes = useMemo(() => {
    const types = new Set<string>()
    tokens.forEach(t => {
      const plan = t.accountInfo?.plan || ''
      if (plan) types.add(plan)
    })
    return Array.from(types).sort()
  }, [tokens])

  // 切换邮箱后缀选择
  const toggleEmailSuffix = (suffix: string) => {
    setFilterEmailSuffixes(prev => {
      if (prev.includes(suffix)) {
        return prev.filter(s => s !== suffix)
      } else {
        return [...prev, suffix]
      }
    })
  }

  // 筛选后的数据
  const filteredTokens = useMemo(() => {
    return tokens.filter(t => {
      if (filterEmailSuffixes.length > 0) {
        const email = t.accountInfo?.email || ''
        const atIndex = email.lastIndexOf('@')
        const suffix = atIndex > 0 ? email.substring(atIndex + 1).toLowerCase() : ''
        if (!filterEmailSuffixes.includes(suffix)) return false
      }
      
      if (filterSubscription !== 'all') {
        const plan = t.accountInfo?.plan || ''
        if (plan !== filterSubscription) return false
      }
      
      if (filterExpiryDays !== 'all') {
        const daysRemaining = t.accountInfo?.daysRemainingOnTrial
        if (daysRemaining === undefined) {
          if (filterExpiryDays !== 'unknown') return false
        } else {
          switch (filterExpiryDays) {
            case 'expired':
              if (daysRemaining > 0) return false
              break
            case '0-3':
              if (daysRemaining < 0 || daysRemaining > 3) return false
              break
            case '4-7':
              if (daysRemaining < 4 || daysRemaining > 7) return false
              break
            case '8-14':
              if (daysRemaining < 8 || daysRemaining > 14) return false
              break
            case '14+':
              if (daysRemaining <= 14) return false
              break
            case 'unknown':
              return false
          }
        }
      }
      
      return true
    })
  }, [tokens, filterEmailSuffixes, filterSubscription, filterExpiryDays])

  // 显示的数据（无限滚动）
  const displayedTokens = useMemo(() => {
    return filteredTokens.slice(0, displayCount)
  }, [filteredTokens, displayCount])

  // 统计数据
  const freeAccountsCount = useMemo(() => {
    return tokens.filter(t => {
      const plan = t.accountInfo?.plan?.toLowerCase() || ''
      const subscription = t.accountInfo?.subscriptionStatus?.toLowerCase() || ''
      return plan === 'free' || subscription === 'free'
    }).length
  }, [tokens])

  // 检查是否有激活的筛选
  const hasActiveFilters = filterEmailSuffixes.length > 0 || filterSubscription !== 'all' || filterExpiryDays !== 'all'

  // 重置所有筛选
  const resetFilters = () => {
    setFilterEmailSuffixes([])
    setFilterSubscription('all')
    setFilterExpiryDays('all')
    setShowEmailSuffixDropdown(false)
    setDisplayCount(20)
  }

  // 无限滚动：加载更多
  const loadMore = useCallback(() => {
    if (displayCount < filteredTokens.length) {
      setDisplayCount(prev => Math.min(prev + 20, filteredTokens.length))
    }
  }, [displayCount, filteredTokens.length])

  // 无限滚动：监听滚动
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          loadMore()
        }
      },
      { threshold: 0.1, root: listContainerRef.current }
    )
    
    if (loadMoreRef.current) {
      observer.observe(loadMoreRef.current)
    }
    
    return () => observer.disconnect()
  }, [loadMore])

  // 筛选变化时重置显示数量
  useEffect(() => {
    setDisplayCount(20)
  }, [filterEmailSuffixes, filterSubscription, filterExpiryDays])

  // 选择功能
  const toggleSelect = (id: string) => {
    setSelectedIds(prev => {
      const newSet = new Set(prev)
      if (newSet.has(id)) {
        newSet.delete(id)
      } else {
        newSet.add(id)
      }
      return newSet
    })
  }

  const selectAll = () => {
    setSelectedIds(new Set(filteredTokens.map(t => t.id)))
  }

  const clearSelection = () => {
    setSelectedIds(new Set())
  }

  const selectTopN = (n: number) => {
    const topN = filteredTokens.slice(0, n).map(t => t.id)
    setSelectedIds(new Set(topN))
  }

  // 处理快速选择输入
  const handleSelectTopInput = () => {
    const n = parseInt(selectTopCount)
    if (n > 0 && n <= filteredTokens.length) {
      selectTopN(n)
      setSelectTopCount('')
    }
  }

  // 刷新选中账号
  const refreshSelectedAccounts = async () => {
    if (selectedIds.size === 0) return
    
    setIsRefreshingSelected(true)
    const selectedTokens = tokens.filter(t => selectedIds.has(t.id))
    
    for (const token of selectedTokens) {
      try {
        await onRefreshUsage(token.id)
      } catch (error) {
        console.error('刷新失败:', token.accountInfo?.email, error)
      }
    }
    
    setIsRefreshingSelected(false)
    onShowDialog({
      title: '刷新完成',
      message: `已刷新 ${selectedIds.size} 个账号的用量信息`,
      type: 'info',
      onConfirm: () => {}
    })
  }

  // 导出选中账号
  const exportSelectedAccounts = () => {
    if (selectedIds.size === 0) return
    
    const selectedTokens = tokens.filter(t => selectedIds.has(t.id))
    
    // 生成 CSV
    const headers = ['邮箱', '订阅类型', '订阅状态', '到期时间', '剩余天数', '已用额度', '总额度', 'Cookie']
    const rows = selectedTokens.map(t => [
      t.accountInfo?.email || '',
      t.accountInfo?.plan || '',
      t.accountInfo?.subscriptionStatus || '',
      t.accountInfo?.trialExpiryDate ? new Date(t.accountInfo.trialExpiryDate).toLocaleDateString('zh-CN') : '',
      t.accountInfo?.daysRemainingOnTrial?.toString() || '',
      t.usage?.used?.toString() || '',
      t.usage?.limit?.toString() || '',
      t.accountInfo?.cookieFormat || t.token || ''
    ])
    
    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
    ].join('\n')
    
    // 下载
    const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `账号导出_${new Date().toLocaleDateString('zh-CN').replace(/\//g, '-')}_${selectedIds.size}个.csv`
    link.click()
    URL.revokeObjectURL(link.href)
    
    onShowDialog({
      title: '导出成功',
      message: `已导出 ${selectedIds.size} 个账号`,
      type: 'info',
      onConfirm: () => {}
    })
  }

  const handleClearFree = () => {
    if (freeAccountsCount === 0) {
      alert('没有 Free 账号需要清理')
      return
    }
    
    const confirmed = window.confirm(
      `⚠️ 确认清理 ${freeAccountsCount} 个 Free 账号？\n\n` +
      '此操作将删除所有订阅类型为 Free/Free Trial 的账号，且不可恢复！'
    )
    
    if (confirmed) {
      onClearFreeAccounts()
    }
  }

  return (
    <div className="account-manage-page">
      <div className="page-header">
        <div>
          <h1 className="page-title">账号管理</h1>
          <p className="page-subtitle">管理你的所有 Cursor 账号和令牌 · 共 {tokens.length} 个账号</p>
        </div>
        <div className="page-actions">
          <button className="btn-secondary" onClick={onSyncLocal}>
            🔄 同步本地账号
          </button>
          <button className="btn-secondary" onClick={onRefreshAll}>
            ⌛ 刷新用量
          </button>
          <button className="btn-secondary" onClick={onShowVerification}>
            🔍 验号
          </button>
          {freeAccountsCount > 0 && (
            <button className="btn-danger-outline" onClick={handleClearFree}>
              🗑️ 清理 Free ({freeAccountsCount})
            </button>
          )}
          <button className="btn-primary" onClick={onAddAccount}>
            ➕ 添加账号
          </button>
        </div>
      </div>

      <div className="page-body">
        {tokens.length > 0 && (
          <div className="toolbar-section">
            {/* 筛选栏 */}
            <div className="filter-bar">
              <button 
                className={`filter-toggle-btn ${showFilters ? 'active' : ''} ${hasActiveFilters ? 'has-filters' : ''}`}
                onClick={() => setShowFilters(!showFilters)}
              >
                🔍 筛选 {hasActiveFilters && <span className="filter-badge">●</span>}
              </button>
              
              {hasActiveFilters && (
                <button className="filter-reset-btn" onClick={resetFilters}>
                  ✕ 清除筛选
                </button>
              )}
              
              <div className="content-stats">
                {hasActiveFilters ? (
                  <>筛选结果: {filteredTokens.length} 条（共 {tokens.length} 条）</>
                ) : (
                  <>共 {filteredTokens.length} 条</>
                )}
              </div>
            </div>
            
            {/* 筛选选项 */}
            {showFilters && (
              <div className="filter-options">
                <div className="filter-group filter-group-email">
                  <label className="filter-label">📧 邮箱后缀（可多选）</label>
                  <div className="filter-multi-select-container" ref={emailDropdownRef}>
                    <button 
                      className={`filter-multi-select-btn ${filterEmailSuffixes.length > 0 ? 'has-selection' : ''}`}
                      onClick={() => setShowEmailSuffixDropdown(!showEmailSuffixDropdown)}
                    >
                      {filterEmailSuffixes.length === 0 ? (
                        <span className="placeholder">选择邮箱后缀...</span>
                      ) : (
                        <span className="selected-count">{filterEmailSuffixes.length} 个已选</span>
                      )}
                      <span className="dropdown-arrow">{showEmailSuffixDropdown ? '▲' : '▼'}</span>
                    </button>
                    
                    {showEmailSuffixDropdown && (
                      <div className="filter-multi-dropdown">
                        <div className="filter-multi-dropdown-header">
                          <button 
                            className="select-all-btn"
                            onClick={() => setFilterEmailSuffixes(emailSuffixes)}
                          >
                            全选
                          </button>
                          <button 
                            className="clear-all-btn"
                            onClick={() => setFilterEmailSuffixes([])}
                          >
                            清空
                          </button>
                        </div>
                        <div className="filter-multi-dropdown-list">
                          {emailSuffixes.map(suffix => (
                            <label key={suffix} className="filter-checkbox-item">
                              <input 
                                type="checkbox"
                                checked={filterEmailSuffixes.includes(suffix)}
                                onChange={() => toggleEmailSuffix(suffix)}
                              />
                              <span className="checkbox-label">@{suffix}</span>
                              <span className="checkbox-count">
                                ({tokens.filter(t => {
                                  const email = t.accountInfo?.email || ''
                                  const atIndex = email.lastIndexOf('@')
                                  return atIndex > 0 && email.substring(atIndex + 1).toLowerCase() === suffix
                                }).length})
                              </span>
                            </label>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                  
                  {filterEmailSuffixes.length > 0 && (
                    <div className="selected-tags">
                      {filterEmailSuffixes.map(suffix => (
                        <span key={suffix} className="selected-tag">
                          @{suffix}
                          <button 
                            className="tag-remove-btn"
                            onClick={() => toggleEmailSuffix(suffix)}
                          >
                            ×
                          </button>
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                
                <div className="filter-group">
                  <label className="filter-label">💎 订阅类型</label>
                  <select 
                    className="filter-select"
                    value={filterSubscription}
                    onChange={(e) => setFilterSubscription(e.target.value)}
                  >
                    <option value="all">全部</option>
                    {subscriptionTypes.map(type => (
                      <option key={type} value={type}>{type}</option>
                    ))}
                  </select>
                </div>
                
                <div className="filter-group">
                  <label className="filter-label">⏰ 到期天数</label>
                  <select 
                    className="filter-select"
                    value={filterExpiryDays}
                    onChange={(e) => setFilterExpiryDays(e.target.value)}
                  >
                    <option value="all">全部</option>
                    <option value="expired">已过期</option>
                    <option value="0-3">0-3 天</option>
                    <option value="4-7">4-7 天</option>
                    <option value="8-14">8-14 天</option>
                    <option value="14+">14 天以上</option>
                    <option value="unknown">未知</option>
                  </select>
                </div>
              </div>
            )}
            
            {/* 选择操作栏 */}
            <div className="selection-bar">
              <div className="selection-controls">
                <label className="select-all-checkbox">
                  <input 
                    type="checkbox"
                    checked={selectedIds.size > 0 && selectedIds.size === filteredTokens.length}
                    onChange={() => selectedIds.size === filteredTokens.length ? clearSelection() : selectAll()}
                  />
                  <span>全选</span>
                </label>
                
                <div className="select-top-input">
                  <input 
                    type="number"
                    placeholder="前N个"
                    value={selectTopCount}
                    onChange={(e) => setSelectTopCount(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSelectTopInput()}
                    min="1"
                    max={filteredTokens.length}
                  />
                  <button onClick={handleSelectTopInput} disabled={!selectTopCount}>
                    选中
                  </button>
                </div>
                
                <div className="quick-select-btns">
                  <button onClick={() => selectTopN(10)} disabled={filteredTokens.length < 10}>前10</button>
                  <button onClick={() => selectTopN(50)} disabled={filteredTokens.length < 50}>前50</button>
                  <button onClick={() => selectTopN(100)} disabled={filteredTokens.length < 100}>前100</button>
                </div>
                
                {selectedIds.size > 0 && (
                  <button className="clear-selection-btn" onClick={clearSelection}>
                    清除选择
                  </button>
                )}
              </div>
              
              {selectedIds.size > 0 && (
                <div className="selection-actions">
                  <span className="selection-count">已选 {selectedIds.size} 个</span>
                  <button 
                    className="btn-secondary btn-sm"
                    onClick={refreshSelectedAccounts}
                    disabled={isRefreshingSelected}
                  >
                    {isRefreshingSelected ? '刷新中...' : '🔄 刷新选中'}
                  </button>
                  <button 
                    className="btn-secondary btn-sm"
                    onClick={exportSelectedAccounts}
                  >
                    📥 导出选中
                  </button>
                </div>
              )}
            </div>
          </div>
        )}
        
        {/* 可滚动的列表区域 */}
        <div className="list-scroll-container" ref={listContainerRef}>
          <TokenList
            tokens={displayedTokens}
            selectedIds={selectedIds}
            onToggleSelect={toggleSelect}
            onEdit={onEditToken}
            onDelete={onDeleteToken}
            onSetActive={onSetActive}
            onCheckUsage={onRefreshUsage}
            onShowUsageDetails={onShowUsageDetails}
            onShowDialog={onShowDialog}
          />

          {/* 无限滚动加载更多 */}
          {displayCount < filteredTokens.length && (
            <div ref={loadMoreRef} className="load-more">
              <div className="load-more-spinner"></div>
              <span>加载更多... ({displayCount}/{filteredTokens.length})</span>
            </div>
          )}

          {tokens.length === 0 && (
            <div className="empty-state">
              <div className="empty-icon">📭</div>
              <h3>还没有账号</h3>
              <p>点击"添加账号"开始导入你的 Cursor 令牌</p>
            </div>
          )}
          
          {tokens.length > 0 && filteredTokens.length === 0 && hasActiveFilters && (
            <div className="empty-state">
              <div className="empty-icon">🔍</div>
              <h3>没有匹配的账号</h3>
              <p>当前筛选条件下没有账号，请尝试调整筛选条件</p>
              <button className="btn-secondary" onClick={resetFilters} style={{ marginTop: '12px' }}>
                清除筛选
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default AccountManagePage
