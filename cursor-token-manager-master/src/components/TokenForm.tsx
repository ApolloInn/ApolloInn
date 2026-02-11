import React, { useState, useEffect } from 'react'
import { Token } from '../App'
import '../styles/TokenForm.css'

interface TokenFormProps {
  token: Token | null
  existingTokens?: Token[]  // 已有的账号列表，用于去重
  onSave: (token: Token) => void
  onCancel: () => void
  onShowDialog: (options: {
    title?: string
    message: string
    type?: 'info' | 'confirm' | 'warning' | 'error'
    onConfirm?: () => void
    onCancel?: () => void
    confirmText?: string
    cancelText?: string
  }) => void
}

interface ParseResult {
  userId: string
  email: string
  tokenType: string
  scope: string
  expiryDate?: string
  expiryDateFormatted?: string
  isExpired: boolean
  isValid: boolean
  subscriptionStatus?: string
  isTrial?: boolean
  daysRemainingOnTrial?: number
  name?: string
  importSource?: string
  createTime?: string
  subscriptionUpdatedAt?: string
}

interface BatchParseResult {
  line: number
  input: string
  status: 'pending' | 'parsing' | 'success' | 'error' | 'duplicate' | 'duplicate-input'
  parseResult?: ParseResult
  error?: string
  selected: boolean
  duplicateOf?: string  // 重复的目标（邮箱或行号）
}

const TokenForm: React.FC<TokenFormProps> = ({ token, existingTokens = [], onSave, onCancel, onShowDialog }) => {
  const [tokenValue, setTokenValue] = useState('')
  const [parseResult, setParseResult] = useState<ParseResult | null>(null)
  const [isParsing, setIsParsing] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [isConverting, setIsConverting] = useState(false)
  const [mode, setMode] = useState<'cookie' | 'token'>('cookie')
  
  // 批量添加相关状态
  const [batchResults, setBatchResults] = useState<BatchParseResult[]>([])
  const [isBatchParsing, setIsBatchParsing] = useState(false)
  const [batchProgress, setBatchProgress] = useState({ current: 0, total: 0 })

  // 判断是否为添加模式（非编辑模式）
  const isAddMode = !token

  useEffect(() => {
    if (token) {
      setTokenValue(token.token)
      if (token.token.includes('WorkosCursorSessionToken') || (token.token.startsWith('user_') && token.token.includes('%3A%3A'))) {
        setMode('cookie')
      } else {
        setMode('token')
      }
      
      if (token.accountInfo) {
        let expiryDateFormatted = '未知'
        let scope = 'openid profile email offline_access'
        let isExpired = false
        
        try {
          const jwtPart = token.accountInfo.longTermToken || (token.token.startsWith('eyJ') ? token.token : (token.token.includes('%3A%3A') ? token.token.split('%3A%3A')[1] : token.token.split('::')[1]))
          if (jwtPart && jwtPart.includes('.')) {
            const base64Url = jwtPart.split('.')[1]
            const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
            const jsonPayload = decodeURIComponent(window.atob(base64).split('').map(function(c) {
                return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)
            }).join(''))
            const payload = JSON.parse(jsonPayload)
            
            if (payload.exp) {
              const expDate = new Date(payload.exp * 1000)
              expiryDateFormatted = expDate.toLocaleString('zh-CN')
              isExpired = expDate < new Date()
            }
            if (payload.scope) {
              scope = payload.scope
            }
          }
        } catch (e) {
          console.warn('前端解析 JWT 失败', e)
        }

        setParseResult({
          userId: token.accountInfo.id || '未知',
          email: token.accountInfo.email || '未获取',
          tokenType: 'session',
          scope: scope,
          name: token.accountInfo.name,
          isValid: !isExpired,
          isExpired: isExpired,
          subscriptionStatus: token.accountInfo.plan,
          isTrial: token.accountInfo.isTrial,
          daysRemainingOnTrial: token.accountInfo.daysRemainingOnTrial,
          expiryDateFormatted: expiryDateFormatted,
          importSource: token.accountInfo.cookieFormat ? 'cookie' : 'jwt_token',
          createTime: token.createTime ? new Date(token.createTime).toLocaleString('zh-CN', { hour12: false }) : '未知',
          subscriptionUpdatedAt: new Date().toLocaleString('zh-CN', { hour12: false })
        })
      } else {
        setParseResult(null)
      }
    } else {
      setTokenValue('')
      setMode('cookie')
      setParseResult(null)
      setBatchResults([])
    }
  }, [token])
  
  const handleSwitchFormat = (format: 'long' | 'cookie') => {
    if (!token?.accountInfo) return
    
    if (format === 'long' && token.accountInfo.longTermToken) {
      setTokenValue(token.accountInfo.longTermToken)
      setMode('token')
    } else if (format === 'cookie' && token.accountInfo.cookieFormat) {
      setTokenValue(token.accountInfo.cookieFormat)
      setMode('cookie')
    }
  }

  const handleConvertToCookie = async () => {
    if (!tokenValue.trim()) {
      onShowDialog({
        title: '提示',
        message: '请先输入长效 Token',
        type: 'warning',
        onConfirm: () => {
          onShowDialog({ show: false, message: '', type: 'info' } as any)
        }
      })
      return
    }

    setIsConverting(true)
    try {
      if (!window.electronAPI || !window.electronAPI.convertTokenToCookie) {
        throw new Error('转换功能不可用，请重启应用')
      }
      
      const result = await window.electronAPI.convertTokenToCookie(tokenValue.trim())
      
      if (result.success && result.cookieFormat) {
        setTokenValue(result.cookieFormat)
        setMode('cookie')
        
        onShowDialog({
          title: '转换成功',
          message: `已成功转换为 Cookie 格式\n\nWorkosId: ${result.workosId}\n\n现在可以解析或保存该 Token`,
          type: 'info',
          onConfirm: () => {
            onShowDialog({ show: false, message: '', type: 'info' } as any)
          }
        })
      } else {
        onShowDialog({
          title: '转换失败',
          message: result.error || '无法转换 Token 格式',
          type: 'error',
          onConfirm: () => {
            onShowDialog({ show: false, message: '', type: 'info' } as any)
          }
        })
      }
    } catch (error: any) {
      console.error('转换失败:', error)
      onShowDialog({
        title: '错误',
        message: '转换过程发生错误: ' + error.message,
        type: 'error',
        onConfirm: () => {
          onShowDialog({ show: false, message: '', type: 'info' } as any)
        }
      })
    } finally {
      setIsConverting(false)
    }
  }

  // 提取 token 的唯一标识（用于去重）
  const extractTokenKey = (input: string): string => {
    const trimmed = input.trim()
    // Cookie 格式: user_xxx%3A%3Ayyy 或 user_xxx::yyy
    if (trimmed.includes('%3A%3A')) {
      return trimmed.split('%3A%3A')[0]
    }
    if (trimmed.includes('::')) {
      return trimmed.split('::')[0]
    }
    // JWT 格式: 取前100个字符作为标识
    if (trimmed.startsWith('eyJ')) {
      return trimmed.substring(0, 100)
    }
    return trimmed
  }

  // 解析输入文本，支持：
  // 1. 每行一个 token/cookie
  // 2. 双引号包裹的内容作为一条（"cookie1""cookie2" 或 "cookie1"\n"cookie2"）
  // 3. WorkosCursorSessionToken:"cookie" 格式
  const parseInputLines = (input: string): string[] => {
    const result: string[] = []
    const text = input.trim()
    
    // 检查是否包含双引号
    if (text.includes('"')) {
      // 使用正则匹配双引号包裹的内容
      const regex = /"([^"]+)"/g
      let match
      while ((match = regex.exec(text)) !== null) {
        const content = match[1].trim()
        if (content) {
          result.push(content)
        }
      }
      
      // 如果找到了双引号内容，返回结果
      if (result.length > 0) {
        return result
      }
    }
    
    // 默认按行分割，并处理每行可能的特殊格式
    const lines = text.split('\n').map(line => line.trim()).filter(line => line)
    
    return lines.map(line => {
      let processed = line
      
      // 处理各种前缀格式（支持中英文冒号）
      const prefixes = [
        'workoscursorsessiontoken',
        'sessiontoken',
        'token',
        'cookie'
      ]
      
      const lowerLine = line.toLowerCase()
      
      for (const prefix of prefixes) {
        if (lowerLine.startsWith(prefix)) {
          // 找到前缀后的分隔符位置（支持 : = ： 等）
          const rest = line.substring(prefix.length)
          const match = rest.match(/^[\s]*[:=：][\s]*(.+)/)
          if (match) {
            processed = match[1].trim()
            break
          }
        }
      }
      
      // 移除可能的引号
      if (processed.startsWith('"') && processed.endsWith('"')) {
        processed = processed.slice(1, -1)
      }
      if (processed.startsWith("'") && processed.endsWith("'")) {
        processed = processed.slice(1, -1)
      }
      
      return processed.trim()
    }).filter(line => line)
  }

  // 批量解析 - 并发处理，最多50个并行，带去重
  const handleBatchParse = async () => {
    const lines = parseInputLines(tokenValue)
    
    if (lines.length === 0) {
      onShowDialog({
        title: '提示',
        message: '请输入至少一个 Token 或 Cookie，每行一个',
        type: 'warning',
        onConfirm: () => {
          onShowDialog({ show: false, message: '', type: 'info' } as any)
        }
      })
      return
    }

    // 构建已有账号的 token key 集合（用于检测与已有账号重复）
    const existingKeys = new Set<string>()
    const existingEmails = new Map<string, string>() // key -> email
    existingTokens.forEach(t => {
      const key = extractTokenKey(t.token)
      existingKeys.add(key)
      if (t.accountInfo?.email) {
        existingEmails.set(key, t.accountInfo.email)
      }
      // 也检查 cookieFormat
      if (t.accountInfo?.cookieFormat) {
        const cookieKey = extractTokenKey(t.accountInfo.cookieFormat)
        existingKeys.add(cookieKey)
        if (t.accountInfo?.email) {
          existingEmails.set(cookieKey, t.accountInfo.email)
        }
      }
    })

    // 检测输入中的重复项
    const inputKeys = new Map<string, number>() // key -> 第一次出现的行号
    const initialResults: BatchParseResult[] = []
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i].trim()
      const key = extractTokenKey(line)
      
      // 检查是否与已有账号重复
      if (existingKeys.has(key)) {
        const existingEmail = existingEmails.get(key) || '已有账号'
        initialResults.push({
          line: i + 1,
          input: line,
          status: 'duplicate',
          selected: false,
          duplicateOf: existingEmail
        })
      }
      // 检查是否与之前输入的行重复
      else if (inputKeys.has(key)) {
        initialResults.push({
          line: i + 1,
          input: line,
          status: 'duplicate-input',
          selected: false,
          duplicateOf: `第 ${inputKeys.get(key)} 行`
        })
      }
      // 新的唯一项
      else {
        inputKeys.set(key, i + 1)
        initialResults.push({
          line: i + 1,
          input: line,
          status: 'pending',
          selected: true
        })
      }
    }

    setBatchResults(initialResults)
    
    // 过滤出需要解析的项
    const toParse = initialResults
      .map((r, idx) => ({ ...r, originalIndex: idx }))
      .filter(r => r.status === 'pending')
    
    if (toParse.length === 0) {
      onShowDialog({
        title: '全部重复',
        message: `所有 ${lines.length} 个账号都与已有账号或输入内容重复`,
        type: 'warning',
        onConfirm: () => {
          onShowDialog({ show: false, message: '', type: 'info' } as any)
        }
      })
      return
    }

    setIsBatchParsing(true)
    setBatchProgress({ current: 0, total: toParse.length })

    const CONCURRENCY = 50 // 最大并发数
    let completedCount = 0
    
    // 用于解析后二次去重（根据解析出的邮箱）
    const parsedEmails = new Map<string, number>() // email -> 原始索引

    // 单个解析任务
    const parseOne = async (originalIndex: number, line: string) => {
      // 更新状态为解析中
      setBatchResults(prev => prev.map((r, idx) => 
        idx === originalIndex ? { ...r, status: 'parsing' } : r
      ))

      try {
        if (!window.electronAPI || !window.electronAPI.parseToken) {
          throw new Error('parseToken 方法不可用')
        }
        
        const result = await window.electronAPI.parseToken(line)
        
        if (result.success && result.parseResult) {
          const email = result.parseResult.email || result.parseResult.userId
          
          // 检查解析出的邮箱是否与已有账号重复
          const existingToken = existingTokens.find(t => t.accountInfo?.email === email)
          if (existingToken) {
            setBatchResults(prev => prev.map((r, idx) => 
              idx === originalIndex ? { 
                ...r, 
                status: 'duplicate', 
                parseResult: result.parseResult,
                duplicateOf: email,
                selected: false 
              } : r
            ))
          }
          // 检查是否与之前解析的结果重复
          else if (parsedEmails.has(email)) {
            setBatchResults(prev => prev.map((r, idx) => 
              idx === originalIndex ? { 
                ...r, 
                status: 'duplicate-input', 
                parseResult: result.parseResult,
                duplicateOf: `第 ${prev[parsedEmails.get(email)!].line} 行`,
                selected: false 
              } : r
            ))
          }
          else {
            parsedEmails.set(email, originalIndex)
            setBatchResults(prev => prev.map((r, idx) => 
              idx === originalIndex ? { ...r, status: 'success', parseResult: result.parseResult } : r
            ))
          }
        } else {
          setBatchResults(prev => prev.map((r, idx) => 
            idx === originalIndex ? { 
              ...r, 
              status: 'error', 
              error: result.errorMessage || '解析失败',
              selected: false 
            } : r
          ))
        }
      } catch (error: any) {
        setBatchResults(prev => prev.map((r, idx) => 
          idx === originalIndex ? { 
            ...r, 
            status: 'error', 
            error: error.message || '解析异常',
            selected: false 
          } : r
        ))
      }

      completedCount++
      setBatchProgress({ current: completedCount, total: toParse.length })
    }

    // 并发控制函数
    const runWithConcurrency = async (tasks: (() => Promise<void>)[], concurrency: number) => {
      const results: Promise<void>[] = []
      const executing: Promise<void>[] = []

      for (const task of tasks) {
        const p = task()
        results.push(p)

        if (concurrency <= tasks.length) {
          const e: Promise<void> = p.then(() => {
            executing.splice(executing.indexOf(e), 1)
          })
          executing.push(e)

          if (executing.length >= concurrency) {
            await Promise.race(executing)
          }
        }
      }

      await Promise.all(results)
    }

    // 创建所有解析任务
    const tasks = toParse.map(item => () => parseOne(item.originalIndex, item.input))

    // 执行并发解析
    await runWithConcurrency(tasks, CONCURRENCY)

    setIsBatchParsing(false)
  }

  // 切换单个结果的选中状态
  const toggleResultSelection = (index: number) => {
    setBatchResults(prev => prev.map((r, idx) => 
      idx === index ? { ...r, selected: !r.selected } : r
    ))
  }

  // 全选/取消全选成功的结果
  const toggleAllSelection = (selected: boolean) => {
    setBatchResults(prev => prev.map(r => 
      r.status === 'success' ? { ...r, selected } : r
    ))
  }

  // 批量添加选中的账号
  const handleBatchAdd = async () => {
    const selectedResults = batchResults.filter(r => r.selected && r.status === 'success')
    
    if (selectedResults.length === 0) {
      onShowDialog({
        title: '提示',
        message: '请至少选择一个成功解析的账号',
        type: 'warning',
        onConfirm: () => {
          onShowDialog({ show: false, message: '', type: 'info' } as any)
        }
      })
      return
    }

    setIsLoading(true)
    let addedCount = 0
    
    for (const result of selectedResults) {
      const tokenData: Token = {
        id: Date.now().toString() + '_' + addedCount,
        name: '',
        token: result.input,
        isActive: false
      }

      try {
        await onSave(tokenData)
        addedCount++
      } catch (error) {
        console.error('添加失败:', error)
      }
      
      // 小延迟
      await new Promise(resolve => setTimeout(resolve, 50))
    }

    setIsLoading(false)
    
    if (addedCount === selectedResults.length) {
      onShowDialog({
        title: '添加成功',
        message: `已成功添加 ${addedCount} 个账号`,
        type: 'info',
        onConfirm: () => {
          onShowDialog({ show: false, message: '', type: 'info' } as any)
          onCancel() // 关闭表单
        }
      })
    } else {
      onShowDialog({
        title: '部分添加成功',
        message: `成功添加 ${addedCount} 个，失败 ${selectedResults.length - addedCount} 个`,
        type: 'warning',
        onConfirm: () => {
          onShowDialog({ show: false, message: '', type: 'info' } as any)
        }
      })
    }
  }

  const handleParse = async () => {
    if (!tokenValue.trim()) {
      onShowDialog({
        title: '提示',
        message: `请先输入 ${mode === 'token' ? 'Token' : 'Cookie'}`,
        type: 'warning',
        onConfirm: () => {
          onShowDialog({ show: false, message: '', type: 'info' } as any)
        }
      })
      return
    }

    setIsParsing(true)
    try {
      if (!window.electronAPI || !window.electronAPI.parseToken) {
        throw new Error('parseToken 方法不可用，请重启应用')
      }
      const result = await window.electronAPI.parseToken(tokenValue.trim())
      if (result.success && result.parseResult) {
        setParseResult(result.parseResult)
      } else {
        if (result.error === 'not_authenticated' || result.errorMessage?.includes('没有这个账号')) {
          onShowDialog({
            title: '解析失败',
            message: result.errorMessage || '没有这个账号，Token 无效或已过期',
            type: 'error',
            onConfirm: () => {
              onShowDialog({ show: false, message: '', type: 'info' } as any)
            }
          })
        } else {
          onShowDialog({
            title: '解析失败',
            message: result.errorMessage || '无法解析 Token，请检查格式是否正确',
            type: 'error',
            onConfirm: () => {
              onShowDialog({ show: false, message: '', type: 'info' } as any)
            }
          })
        }
        setParseResult(null)
      }
    } catch (error: any) {
      console.error('解析 Token 失败:', error)
      onShowDialog({
        title: '错误',
        message: `解析 Token 时发生错误: ${error.message || '未知错误'}`,
        type: 'error',
        onConfirm: () => {
          onShowDialog({ show: false, message: '', type: 'info' } as any)
        }
      })
      setParseResult(null)
    } finally {
      setIsParsing(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!tokenValue.trim()) {
      onShowDialog({
        title: '提示',
        message: '请填写Token信息',
        type: 'warning',
        onConfirm: () => {
          onShowDialog({ show: false, message: '', type: 'info' } as any)
        }
      })
      return
    }

    if (!token && !parseResult) {
      onShowDialog({
        title: '提示',
        message: '请先点击"解析"按钮验证 Token',
        type: 'warning',
        onConfirm: () => {
          onShowDialog({ show: false, message: '', type: 'info' } as any)
        }
      })
      return
    }

    setIsLoading(true)

    const tokenData: Token = {
      id: token?.id || Date.now().toString(),
      name: token?.name || '',
      token: tokenValue.trim(),
      isActive: token?.isActive || false
    }

    try {
      await onSave(tokenData)
    } finally {
      setIsLoading(false)
    }
  }

  // 判断是否有多行输入（批量模式）
  const isBatchMode = isAddMode && tokenValue.includes('\n')
  const successCount = batchResults.filter(r => r.status === 'success').length
  const errorCount = batchResults.filter(r => r.status === 'error').length
  const duplicateCount = batchResults.filter(r => r.status === 'duplicate').length
  const duplicateInputCount = batchResults.filter(r => r.status === 'duplicate-input').length
  const selectedCount = batchResults.filter(r => r.selected && r.status === 'success').length

  // 添加模式下的批量布局
  if (isAddMode) {
    return (
      <div className="token-form-container batch-mode">
        <div className="batch-layout">
          {/* 左侧输入区 */}
          <div className="batch-input-section">
            <div className="form-tabs">
              <button
                type="button"
                className={`form-tab ${mode === 'cookie' ? 'active' : ''}`}
                onClick={() => {
                  setMode('cookie')
                  setTokenValue('')
                  setParseResult(null)
                  setBatchResults([])
                }}
              >
                Cookies
              </button>
              <button
                type="button"
                className={`form-tab ${mode === 'token' ? 'active' : ''}`}
                onClick={() => {
                  setMode('token')
                  setTokenValue('')
                  setParseResult(null)
                  setBatchResults([])
                }}
              >
                长效 Token
              </button>
            </div>

            <div className="batch-input-header">
              <span className="batch-input-hint">
                支持多种格式，自动识别前缀和双引号
              </span>
              <span className="batch-line-count">
                {tokenValue.trim() ? `${parseInputLines(tokenValue).length} 条` : '0 条'}
              </span>
            </div>

            <textarea
              className="form-textarea batch-textarea"
              placeholder={mode === 'token' 
                ? "支持多种格式，自动识别：\n\n1. 纯 Token：\neyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...\n\n2. 双引号包裹：\n\"eyJhbGci...\"\"eyJhbGci...\"\n\n3. 带前缀（自动去除）：\nToken: eyJhbGci...\nToken=eyJhbGci..." 
                : "支持多种格式，自动识别：\n\n1. 纯 Cookie：\nuser_01HXYZ...%3A%3AeyJhbGci...\n\n2. 双引号包裹：\n\"user_01...\"\"user_02...\"\n\n3. 带前缀（自动去除）：\nWorkosCursorSessionToken:\"user_01...\"\nSessionToken：user_01...\nCookie=user_01..."}
              value={tokenValue}
              onChange={(e) => {
                setTokenValue(e.target.value)
                setParseResult(null)
                setBatchResults([])
              }}
              disabled={isLoading || isBatchParsing}
            />

            <div className="batch-input-actions">
              {mode === 'token' && tokenValue.trim().startsWith('eyJ') && !tokenValue.includes('%3A%3A') && !tokenValue.includes('::') && !tokenValue.includes('\n') && (
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={handleConvertToCookie}
                  disabled={isConverting || isParsing || isLoading || !tokenValue.trim()}
                >
                  {isConverting ? '转换中...' : '🔄 转换为 Cookie'}
                </button>
              )}
              
              <button
                type="button"
                className="btn-primary"
                onClick={isBatchMode ? handleBatchParse : handleParse}
                disabled={isParsing || isLoading || isConverting || isBatchParsing || !tokenValue.trim()}
              >
                {isBatchParsing ? `解析中 (${batchProgress.current}/${batchProgress.total})...` : 
                 isParsing ? '解析中...' : 
                 isBatchMode ? '批量解析' : '解析'}
              </button>
            </div>
          </div>

          {/* 右侧结果区 */}
          <div className="batch-result-section">
            <div className="batch-result-header">
              <span className="batch-result-title">
                {batchResults.length > 0 ? '解析结果' : '解析结果预览'}
              </span>
              {batchResults.length > 0 && (
                <div className="batch-result-stats">
                  <span className="stat-success">✅ {successCount}</span>
                  {errorCount > 0 && <span className="stat-error">❌ {errorCount}</span>}
                  {(duplicateCount + duplicateInputCount) > 0 && (
                    <span className="stat-duplicate">🔄 {duplicateCount + duplicateInputCount} 重复</span>
                  )}
                </div>
              )}
            </div>

            {batchResults.length === 0 && !parseResult && (
              <div className="batch-result-empty">
                <div className="empty-icon">📋</div>
                <p>在左侧输入 Token 或 Cookie</p>
                <p className="hint">支持每行一个或双引号 "cookie" 格式</p>
              </div>
            )}

            {/* 单个解析结果 */}
            {parseResult && !isBatchMode && batchResults.length === 0 && (
              <div className="single-parse-result">
                <div className="parse-result-card">
                  <div className="card-header success">
                    <span className="status-icon">✅</span>
                    <span className="email">{parseResult.email || parseResult.name || '未命名'}</span>
                  </div>
                  <div className="card-body">
                    <div className="info-row">
                      <span className="label">订阅:</span>
                      <span className={`value ${parseResult.isTrial ? 'trial' : ''}`}>
                        {parseResult.subscriptionStatus || 'free'}
                        {parseResult.isTrial && ` (剩余${parseResult.daysRemainingOnTrial}天)`}
                      </span>
                    </div>
                    <div className="info-row">
                      <span className="label">状态:</span>
                      <span className={`value ${parseResult.isValid ? 'valid' : 'invalid'}`}>
                        {parseResult.isValid ? '有效' : '无效/过期'}
                      </span>
                    </div>
                    <div className="info-row">
                      <span className="label">用户ID:</span>
                      <span className="value mono">{parseResult.userId}</span>
                    </div>
                  </div>
                </div>
                
                <div className="single-actions">
                  <button type="button" className="btn-secondary" onClick={onCancel} disabled={isLoading}>
                    取消
                  </button>
                  <button 
                    type="button" 
                    className="btn-primary" 
                    onClick={handleSubmit}
                    disabled={isLoading || !parseResult}
                  >
                    {isLoading ? '添加中...' : '添加账号'}
                  </button>
                </div>
              </div>
            )}

            {/* 批量解析结果列表 */}
            {batchResults.length > 0 && (
              <>
                <div className="batch-result-toolbar">
                  <label className="select-all-checkbox">
                    <input 
                      type="checkbox"
                      checked={selectedCount > 0 && selectedCount === successCount}
                      onChange={(e) => toggleAllSelection(e.target.checked)}
                      disabled={successCount === 0}
                    />
                    <span>全选成功项 ({selectedCount}/{successCount})</span>
                  </label>
                </div>
                
                <div className="batch-result-list">
                  {batchResults.map((result, index) => (
                    <div 
                      key={index} 
                      className={`batch-result-item ${result.status} ${result.selected ? 'selected' : ''}`}
                      onClick={() => result.status === 'success' && toggleResultSelection(index)}
                    >
                      <div className="item-checkbox">
                        {result.status === 'success' && (
                          <input 
                            type="checkbox"
                            checked={result.selected}
                            onChange={() => toggleResultSelection(index)}
                            onClick={(e) => e.stopPropagation()}
                          />
                        )}
                        {result.status === 'parsing' && <div className="mini-spinner"></div>}
                        {result.status === 'pending' && <span className="pending-dot">○</span>}
                        {result.status === 'error' && <span className="error-icon">✕</span>}
                        {(result.status === 'duplicate' || result.status === 'duplicate-input') && (
                          <span className="duplicate-icon">🔄</span>
                        )}
                      </div>
                      
                      <div className="item-content">
                        {result.status === 'success' && result.parseResult ? (
                          <div className="item-detail-card">
                            <div className="detail-row">
                              <span className="detail-label">用户ID:</span>
                              <span className="detail-value mono">{result.parseResult.userId}</span>
                            </div>
                            <div className="detail-row">
                              <span className="detail-label">邮箱:</span>
                              <span className="detail-value">{result.parseResult.email || '未命名'}</span>
                            </div>
                            <div className="detail-row">
                              <span className="detail-label">状态:</span>
                              <span className="detail-value">待应用</span>
                            </div>
                            <div className="detail-row">
                              <span className="detail-label">Token类型:</span>
                              <span className="detail-value">{result.parseResult.tokenType || 'session'}</span>
                            </div>
                            <div className="detail-row">
                              <span className="detail-label">订阅状态:</span>
                              <span className={`detail-value ${result.parseResult.isTrial ? 'trial' : ''}`}>
                                {result.parseResult.subscriptionStatus || 'free'}
                                {result.parseResult.isTrial && ' (试用)'}
                              </span>
                            </div>
                            {result.parseResult.subscriptionUpdatedAt && (
                              <div className="detail-row">
                                <span className="detail-label">订阅更新时间:</span>
                                <span className="detail-value">{result.parseResult.subscriptionUpdatedAt}</span>
                              </div>
                            )}
                            <div className="detail-row">
                              <span className="detail-label">Token状态:</span>
                              <span className={`detail-value ${result.parseResult.isValid ? 'valid' : 'invalid'}`}>
                                {result.parseResult.isValid ? '✅ 有效' : '❌ 无效'}
                              </span>
                            </div>
                            {result.parseResult.expiryDateFormatted && (
                              <div className="detail-row">
                                <span className="detail-label">过期时间:</span>
                                <span className={`detail-value ${result.parseResult.isExpired ? 'expired' : ''}`}>
                                  {result.parseResult.expiryDateFormatted}
                                  {result.parseResult.isExpired && ' (已过期)'}
                                </span>
                              </div>
                            )}
                            {result.parseResult.isTrial && result.parseResult.daysRemainingOnTrial !== undefined && (
                              <div className="detail-row">
                                <span className="detail-label">试用剩余:</span>
                                <span className="detail-value trial-days">{result.parseResult.daysRemainingOnTrial} 天</span>
                              </div>
                            )}
                          </div>
                        ) : result.status === 'error' ? (
                          <div className="item-error-content">
                            <div className="error-input">{result.input.substring(0, 50)}...</div>
                            <div className="error-msg">{result.error}</div>
                          </div>
                        ) : result.status === 'duplicate' || result.status === 'duplicate-input' ? (
                          <div className="item-duplicate-content">
                            <div className="dup-email">{result.parseResult?.email || result.input.substring(0, 30) + '...'}</div>
                            <div className="dup-reason">
                              {result.status === 'duplicate' ? '已存在: ' : '重复: '}{result.duplicateOf}
                            </div>
                          </div>
                        ) : (
                          <div className="item-pending-content">
                            <span className="pending-input">{result.input.substring(0, 50)}...</span>
                          </div>
                        )}
                      </div>
                      
                      <div className="item-line">#{result.line}</div>
                    </div>
                  ))}
                </div>

                <div className="batch-actions">
                  <button type="button" className="btn-secondary" onClick={onCancel} disabled={isLoading}>
                    取消
                  </button>
                  <button 
                    type="button" 
                    className="btn-primary" 
                    onClick={handleBatchAdd}
                    disabled={isLoading || selectedCount === 0}
                  >
                    {isLoading ? '添加中...' : `添加选中 (${selectedCount})`}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    )
  }

  // 编辑模式（查看详情）保持原样
  return (
    <div className="token-form-container">
      <form className="token-form" onSubmit={handleSubmit}>
        <div className="form-tabs">
          <button
            type="button"
            className={`form-tab ${mode === 'cookie' ? 'active' : ''}`}
            onClick={() => {
              if (token?.accountInfo?.cookieFormat) {
                handleSwitchFormat('cookie')
              } else {
                onShowDialog({
                  title: '提示',
                  message: '此账号尚未获取 Cookie 格式\n\n请先切换到此账号，系统会自动生成 Cookie 格式',
                  type: 'info',
                  onConfirm: () => {
                    onShowDialog({ show: false, message: '', type: 'info' } as any)
                  }
                })
              }
            }}
          >
            Cookies
          </button>
          <button
            type="button"
            className={`form-tab ${mode === 'token' ? 'active' : ''}`}
            onClick={() => {
              if (token?.accountInfo?.longTermToken) {
                handleSwitchFormat('long')
              } else {
                onShowDialog({
                  title: '提示',
                  message: '此账号尚未获取长效 Token\n\n请先切换到此账号，系统会自动获取长效 Token',
                  type: 'info',
                  onConfirm: () => {
                    onShowDialog({ show: false, message: '', type: 'info' } as any)
                  }
                })
              }
            }}
          >
            长效 Token
          </button>
        </div>

        {token && token.accountInfo && (
          <div style={{
            marginBottom: '15px',
            padding: '10px 12px',
            backgroundColor: token.accountInfo.longTermToken ? '#e0f2fe' : '#fef3c7',
            border: `1px solid ${token.accountInfo.longTermToken ? '#7dd3fc' : '#fcd34d'}`,
            borderRadius: '6px',
            fontSize: '13px',
            color: token.accountInfo.longTermToken ? '#0c4a6e' : '#92400e'
          }}>
            {token.accountInfo.longTermToken && token.accountInfo.cookieFormat ? (
              <>
                <div style={{ fontWeight: 500, marginBottom: '4px' }}>
                  📋 此账号包含两种格式
                </div>
                <div style={{ fontSize: '12px', opacity: 0.9 }}>
                  点击上方标签可切换查看 "长效 Token" 或 "Cookies" 格式
                </div>
              </>
            ) : token.accountInfo.cookieFormat && !token.accountInfo.longTermToken ? (
              <>
                <div style={{ fontWeight: 500, marginBottom: '4px' }}>
                  🍪 此账号仅有 Cookie 格式
                </div>
                <div style={{ fontSize: '12px', opacity: 0.9 }}>
                  切换到此账号后，将自动获取长效 Token，届时可复制
                </div>
              </>
            ) : token.accountInfo.longTermToken && !token.accountInfo.cookieFormat ? (
              <>
                <div style={{ fontWeight: 500, marginBottom: '4px' }}>
                  🔑 此账号仅有长效 Token 格式
                </div>
                <div style={{ fontSize: '12px', opacity: 0.9 }}>
                  切换到此账号后，将自动生成 Cookie 格式
                </div>
              </>
            ) : null}
          </div>
        )}

        <div className="form-group">
          <div className="form-label-row">
            <label htmlFor="token-value">
              {mode === 'token' ? 'Cursor Token' : 'Session Token'}
            </label>
          </div>
          <textarea
            id="token-value"
            className="form-textarea"
            value={tokenValue}
            readOnly
            rows={4}
          />
        </div>

        {parseResult && (
          <div className="parse-result">
            <h4 className="parse-result-title">账号详细信息</h4>
            <div className="parse-result-content">
              <div className="parse-result-item full-width">
                <span className="parse-result-label">用户ID:</span>
                <span className="parse-result-value" style={{ fontSize: '12px', fontFamily: 'monospace', userSelect: 'all' }}>
                  {parseResult.userId}
                </span>
              </div>

              <div className="parse-result-row">
                <div className="parse-result-item">
                  <span className="parse-result-label">邮箱:</span>
                  <span className="parse-result-value" style={{ userSelect: 'all' }}>
                    {parseResult.email || parseResult.name || '未命名'}
                  </span>
                </div>
                <div className="parse-result-item">
                  <span className="parse-result-label">状态:</span>
                  <span className="parse-result-value">
                    {token ? (token.isActive ? '✅ 使用中' : '待应用') : '待添加'}
                  </span>
                </div>
              </div>
              
              <div className="parse-result-row">
                <div className="parse-result-item">
                  <span className="parse-result-label">订阅状态:</span>
                  <span className={`parse-result-value ${parseResult.isTrial ? 'trial-status' : ''}`}>
                    {parseResult.subscriptionStatus || 'free'}
                    {parseResult.isTrial && ' (试用中)'}
                  </span>
                </div>
                <div className="parse-result-item">
                  <span className="parse-result-label">Token状态:</span>
                  <span className={`parse-result-value ${parseResult.isValid ? 'valid' : 'expired'}`}>
                    {parseResult.isValid ? '✅ 有效' : '❌ 无效/过期'}
                  </span>
                </div>
              </div>

              <div className="parse-result-row">
                <div className="parse-result-item">
                  <span className="parse-result-label">过期时间:</span>
                  <span className={`parse-result-value ${parseResult.isExpired ? 'expired' : ''}`}>
                    {parseResult.expiryDateFormatted || '未知'}
                  </span>
                </div>
                <div className="parse-result-item">
                  <span className="parse-result-label">导入来源:</span>
                  <span className="parse-result-value">{parseResult.importSource || '未知'}</span>
                </div>
              </div>

              {parseResult.isTrial && parseResult.daysRemainingOnTrial !== undefined && (
                <div className="parse-result-item full-width" style={{ marginTop: '8px', paddingTop: '8px', borderTop: '1px dashed #eee' }}>
                  <span className="parse-result-label">试用剩余:</span>
                  <span className="parse-result-value highlight-warning">
                    {parseResult.daysRemainingOnTrial} 天
                  </span>
                </div>
              )}
            </div>
          </div>
        )}
      </form>
    </div>
  )
}

export default TokenForm
