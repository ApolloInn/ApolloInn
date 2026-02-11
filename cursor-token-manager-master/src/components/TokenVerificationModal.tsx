import React, { useState, useRef, useEffect } from 'react'
import '../styles/TokenVerificationModal.css'

interface VerificationResult {
  token: string
  fullToken?: string // 保存完整的原始 token
  status: 'pending' | 'success' | 'failed' | 'warning'
  email?: string
  plan?: string
  subscriptionStatus?: string
  expiryDate?: string
  usage?: {
    used: number
    limit: number | null
    percentage: number | null
  }
  recentUsage?: {
    last7Days: number
    totalAmount: number
    lastUsageTime?: string
  }
  verifyTime?: string
  error?: string
  warning?: string
}

interface TokenVerificationModalProps {
  show: boolean
  onClose: () => void
  onShowDialog: (options: {
    title?: string
    message: string
    type?: 'info' | 'confirm' | 'warning' | 'error'
    onConfirm?: () => void
  }) => void
  onAccountAdded?: () => void  // 添加账号后的回调，用于刷新列表
}

const TokenVerificationModal: React.FC<TokenVerificationModalProps> = ({
  show,
  onClose,
  onShowDialog,
  onAccountAdded
}) => {
  const [mode, setMode] = useState<'single' | 'batch'>('single')
  const [tokenInput, setTokenInput] = useState('')
  const [singleFormat, setSingleFormat] = useState<'token' | 'cookie'>('token')
  const [batchFormat, setBatchFormat] = useState<'token' | 'cookie'>('token')
  const [verifying, setVerifying] = useState(false)
  const [results, setResults] = useState<VerificationResult[]>([])
  const [deduplicationInfo, setDeduplicationInfo] = useState<{ original: number; duplicates: number; unique: number } | null>(null)
  const [filterStatus, setFilterStatus] = useState<'all' | 'success' | 'warning' | 'failed'>('all')
  const fileInputRef = useRef<HTMLInputElement>(null)

  // 监听模式切换，清空结果和输入
  useEffect(() => {
    setResults([])
    setTokenInput('')
    setDeduplicationInfo(null)
    setFilterStatus('all')
  }, [mode])

  // 监听单个验号格式切换，清空结果和输入
  useEffect(() => {
    if (mode === 'single') {
      setResults([])
      setTokenInput('')
      setDeduplicationInfo(null)
      setFilterStatus('all')
    }
  }, [singleFormat, mode])

  // 监听批量验号格式切换，清空结果
  useEffect(() => {
    if (mode === 'batch') {
      setResults([])
      setDeduplicationInfo(null)
      setFilterStatus('all')
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }, [batchFormat, mode])

  // 弹窗打开/关闭时重置所有状态
  useEffect(() => {
    if (show) {
      setMode('single')
      setTokenInput('')
      setSingleFormat('token')
      setBatchFormat('token')
      setResults([])
      setVerifying(false)
    }
  }, [show])

  if (!show) return null

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose()
    }
  }

  // 单个验号
  const handleSingleVerify = async () => {
    if (!tokenInput.trim()) {
      onShowDialog({
        title: '提示',
        message: '请输入 Token 或 Cookie',
        type: 'warning',
        onConfirm: () => {}
      })
      return
    }

    setVerifying(true)
    const verifyTime = new Date().toLocaleString('zh-CN', { hour12: false })
    const fullToken = tokenInput.trim()
    const result: VerificationResult = {
      token: fullToken.substring(0, 50) + (fullToken.length > 50 ? '...' : ''),
      fullToken: fullToken,
      status: 'pending',
      verifyTime: verifyTime
    }
    setResults([result])

    try {
      if (!window.electronAPI?.verifyToken) {
        throw new Error('验号功能不可用')
      }

      const verifyResult = await window.electronAPI.verifyToken(tokenInput.trim())
      
      console.log('📦 前端接收到验号结果:', verifyResult)
      console.log('📦 recentUsage 数据:', verifyResult.recentUsage)
      
      if (verifyResult.success) {
        result.email = verifyResult.accountInfo?.email
        result.plan = verifyResult.accountInfo?.plan
        result.subscriptionStatus = verifyResult.accountInfo?.subscriptionStatus
        result.expiryDate = verifyResult.accountInfo?.trialExpiryDate
        result.usage = verifyResult.usage
        result.recentUsage = verifyResult.recentUsage
        
        // 严格验证条件
        let validationError = ''
        let isQuotaFull = false
        
        // 1. 检查订阅类型（必须是 Pro Trial）
        const plan = result.plan?.toLowerCase() || ''
        if (!plan.includes('pro') || !plan.includes('trial')) {
          validationError = `订阅类型不符: ${result.plan}`
        }
        
        // 2. 检查订阅状态（必须是 trialing）
        else if (result.subscriptionStatus?.toLowerCase() !== 'trialing') {
          validationError = `订阅状态不符: ${result.subscriptionStatus}`
        }
        
        // 3. 检查过期时间（不能过期）
        else if (result.expiryDate) {
          const expiryTime = new Date(result.expiryDate).getTime()
          const now = new Date().getTime()
          if (expiryTime <= now) {
            validationError = '账号已过期'
          }
        }
        
        // 4. 检查额度（用满的显示为警告，不是失败）
        if (result.usage) {
          if (result.usage.percentage !== null && result.usage.percentage >= 100) {
            isQuotaFull = true
          } else if (result.usage.limit !== null && result.usage.used >= result.usage.limit) {
            isQuotaFull = true
          }
        }
        
        if (validationError) {
          result.status = 'failed'
          result.error = validationError
        } else if (isQuotaFull) {
          result.status = 'warning'
          result.warning = '该账号额度已用完'
        } else {
          result.status = 'success'
        }
        
        console.log('✅ 结果更新后的 recentUsage:', result.recentUsage)
      } else {
        result.status = 'failed'
        result.error = verifyResult.error || '验证失败'
      }
    } catch (error: any) {
      result.status = 'failed'
      result.error = error.message
    }

    setResults([result])
    setVerifying(false)
  }

  // 处理文件上传
  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    const fileName = file.name.toLowerCase()
    if (!fileName.endsWith('.xlsx') && !fileName.endsWith('.xls') && !fileName.endsWith('.csv')) {
      onShowDialog({
        title: '错误',
        message: '请上传 Excel (.xlsx, .xls) 或 CSV (.csv) 文件',
        type: 'error',
        onConfirm: () => {}
      })
      return
    }

    setVerifying(true)

    try {
      // 读取文件内容
      const fileContent = await readFileAsText(file)
      let tokens: string[] = []

      if (fileName.endsWith('.csv')) {
        const result = parseCSV(fileContent)
        tokens = result.tokens
        setDeduplicationInfo(result.deduplicationInfo)
      } else {
        // Excel 文件需要特殊处理
        onShowDialog({
          title: '提示',
          message: 'Excel 文件解析功能开发中，请使用 CSV 格式',
          type: 'warning',
          onConfirm: () => {}
        })
        setVerifying(false)
        return
      }

      if (tokens.length === 0) {
        onShowDialog({
          title: '错误',
          message: '文件中没有找到有效的 Token',
          type: 'error',
          onConfirm: () => {}
        })
        setVerifying(false)
        return
      }

      // 批量验证
      await batchVerify(tokens)
    } catch (error: any) {
      onShowDialog({
        title: '错误',
        message: `文件解析失败: ${error.message}`,
        type: 'error',
        onConfirm: () => {}
      })
      setVerifying(false)
    }
  }

  // 读取文件为文本
  const readFileAsText = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = (e) => resolve(e.target?.result as string)
      reader.onerror = reject
      reader.readAsText(file)
    })
  }

  // 解析 CSV 文件
  const parseCSV = (content: string): { tokens: string[]; deduplicationInfo: { original: number; duplicates: number; unique: number } | null } => {
    const lines = content.split('\n').map(line => line.trim()).filter(line => line)
    if (lines.length === 0) return { tokens: [], deduplicationInfo: null }

    // 检查第一行是否是表头
    const firstLine = lines[0].toLowerCase()
    const hasHeader = firstLine.includes('token') || firstLine.includes('cookie')
    
    // 跳过表头
    const dataLines = hasHeader ? lines.slice(1) : lines
    
    const tokens = dataLines.map(line => {
      // 处理 CSV 的引号和逗号
      const match = line.match(/^"?([^"]+)"?/)
      return match ? match[1].trim() : line.trim()
    }).filter(token => token.length > 0)
    
    // 去重
    const uniqueTokens = Array.from(new Set(tokens))
    const originalCount = tokens.length
    const uniqueCount = uniqueTokens.length
    const duplicatesCount = originalCount - uniqueCount
    
    let deduplicationInfo = null
    if (duplicatesCount > 0) {
      deduplicationInfo = {
        original: originalCount,
        duplicates: duplicatesCount,
        unique: uniqueCount
      }
      console.log(`✅ 去重: 原始 ${originalCount} 条，重复 ${duplicatesCount} 条，剩余 ${uniqueCount} 条`)
    }
    
    return { tokens: uniqueTokens, deduplicationInfo }
  }

  // 批量验证
  const batchVerify = async (tokens: string[]) => {
    const initialResults: VerificationResult[] = tokens.map(token => ({
      token: token.substring(0, 50) + (token.length > 50 ? '...' : ''),
      fullToken: token,
      status: 'pending',
      verifyTime: new Date().toLocaleString('zh-CN', { hour12: false })
    }))
    setResults(initialResults)

    // 获取设置中的批量数量
    const settings = await window.electronAPI?.getSettings() || {}
    const batchSize = settings.batchRefreshSize || 5
    console.log(`🔢 批量验证并发数: ${batchSize}`)

    // 分批处理
    for (let i = 0; i < tokens.length; i += batchSize) {
      const batch = tokens.slice(i, i + batchSize)
      const batchPromises = batch.map(async (token, batchIndex) => {
        const index = i + batchIndex
        try {
          if (!window.electronAPI?.verifyToken) {
            throw new Error('验号功能不可用')
          }

          const verifyResult = await window.electronAPI.verifyToken(token)
        
          if (verifyResult.success) {
            // 严格验证条件
            let validationError = ''
            let isQuotaFull = false
            const plan = verifyResult.accountInfo?.plan?.toLowerCase() || ''
            const subscriptionStatus = verifyResult.accountInfo?.subscriptionStatus?.toLowerCase() || ''
            
            // 1. 检查订阅类型（必须是 Pro Trial）
            if (!plan.includes('pro') || !plan.includes('trial')) {
              validationError = `订阅类型不符: ${verifyResult.accountInfo?.plan}`
            }
            // 2. 检查订阅状态（必须是 trialing）
            else if (subscriptionStatus !== 'trialing') {
              validationError = `订阅状态不符: ${verifyResult.accountInfo?.subscriptionStatus}`
            }
            // 3. 检查过期时间（不能过期）
            else if (verifyResult.accountInfo?.trialExpiryDate) {
              const expiryTime = new Date(verifyResult.accountInfo.trialExpiryDate).getTime()
              const now = new Date().getTime()
              if (expiryTime <= now) {
                validationError = '账号已过期'
              }
            }
            
            // 4. 检查额度（用满的显示为警告）
            if (verifyResult.usage) {
              if (verifyResult.usage.percentage !== null && verifyResult.usage.percentage >= 100) {
                isQuotaFull = true
              } else if (verifyResult.usage.limit !== null && verifyResult.usage.used >= verifyResult.usage.limit) {
                isQuotaFull = true
              }
            }
            
            initialResults[index] = {
              ...initialResults[index],
              status: validationError ? 'failed' : (isQuotaFull ? 'warning' : 'success'),
              email: verifyResult.accountInfo?.email,
              plan: verifyResult.accountInfo?.plan,
              subscriptionStatus: verifyResult.accountInfo?.subscriptionStatus,
              expiryDate: verifyResult.accountInfo?.trialExpiryDate,
              usage: verifyResult.usage,
              recentUsage: verifyResult.recentUsage,
              error: validationError || undefined,
              warning: isQuotaFull ? '该账号额度已用完' : undefined
            }
          } else {
            initialResults[index] = {
              ...initialResults[index],
              status: 'failed',
              error: verifyResult.error
            }
          }
        } catch (error: any) {
          initialResults[index] = {
            ...initialResults[index],
            status: 'failed',
            email: undefined,
            plan: undefined,
            subscriptionStatus: undefined,
            expiryDate: undefined,
            usage: undefined,
            recentUsage: undefined,
            error: error.message
          }
        }
      })

      // 等待当前批次完成
      await Promise.all(batchPromises)
      setResults([...initialResults])
      
      // 批次间延迟
      if (i + batchSize < tokens.length) {
        await new Promise(resolve => setTimeout(resolve, 500))
      }
    }

    setVerifying(false)
  }

  // 下载示例模板文件
  const handleDownloadTemplate = (format: 'token' | 'cookie') => {
    let content = ''
    let filename = ''
    
    if (format === 'token') {
      filename = '批量验号模板-Token格式.csv'
      content = `token
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhdXRoMHx1c2VyXzAxS0JHMU0yRUVLSE43TlNLMFJLOUdQUzFTIiwidGltZSI6IjE3NjQ2OTY0MjQiLCJyYW5kb21uZXNzIjoiMjFiNDA2NWMtMjg5Yy00ZDE5IiwiZXhwIjoxNzY5ODgwNDI0LCJpc3MiOiJodHRwczovL2F1dGhlbnRpY2F0aW9uLmN1cnNvci5zaCIsInNjb3BlIjoib3BlbmlkIHByb2ZpbGUgZW1haWwgb2ZmbGluZV9hY2Nlc3MiLCJhdWQiOiJodHRwczovL2N1cnNvci5jb20iLCJ0eXBlIjoic2Vzc2lvbiJ9.TM6fVc7_EPFJHgAjMJeL225Nd8l76Ll7Z8y5cblp4pA
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhdXRoMHx1c2VyXzAxS0JHMU02VDRZWUNISDdUNEZLUFlNUTBDIiwidGltZSI6IjE3NjQ2OTY0MjkiLCJyYW5kb21uZXNzIjoiYTY2MWI3NGMtYjBiOC00YTM0IiwiZXhwIjoxNzY5ODgwNDI5LCJpc3MiOiJodHRwczovL2F1dGhlbnRpY2F0aW9uLmN1cnNvci5zaCIsInNjb3BlIjoib3BlbmlkIHByb2ZpbGUgZW1haWwgb2ZmbGluZV9hY2Nlc3MiLCJhdWQiOiJodHRwczovL2N1cnNvci5jb20iLCJ0eXBlIjoic2Vzc2lvbiJ9.B3-1XnjZ10JLQ9eRUavuwVA_Th0rM_HNnc1YpGaBNy4
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhdXRoMHx1c2VyXzAxS0JHMU02WVZNUFhXSEpBQVpRUVhXTUY5IiwidGltZSI6IjE3NjQ2OTY0MzEiLCJyYW5kb21uZXNzIjoiNGFmNTI0NjEtNzQwMC00MzY5IiwiZXhwIjoxNzY5ODgwNDMxLCJpc3MiOiJodHRwczovL2F1dGhlbnRpY2F0aW9uLmN1cnNvci5zaCIsInNjb3BlIjoib3BlbmlkIHByb2ZpbGUgZW1haWwgb2ZmbGluZV9hY2Nlc3MiLCJhdWQiOiJodHRwczovL2N1cnNvci5jb20iLCJ0eXBlIjoic2Vzc2lvbiJ9.MnmSNaLk7qraclM5A7184GcWwakQWU5kAzX-hbrKV0U`
    } else {
      filename = '批量验号模板-Cookie格式.csv'
      content = `cookie
user_01KB0CR6X1BH2WRHB897DDT77Z%3A%3AeyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhdXRoMHx1c2VyXzAxS0IwQ1I2WDFCSDJXUkhCODk3RERUNzdaIiwidGltZSI6IjE3NjQ4NTg3NTEiLCJyYW5kb21uZXNzIjoiNTZhMzZjNTgtMDBjOS00YzZlIiwiZXhwIjoxNzcwMDQyNzUxLCJpc3MiOiJodHRwczovL2F1dGhlbnRpY2F0aW9uLmN1cnNvci5zaCIsInNjb3BlIjoib3BlbmlkIHByb2ZpbGUgZW1haWwgb2ZmbGluZV9hY2Nlc3MiLCJhdWQiOiJodHRwczovL2N1cnNvci5jb20iLCJ0eXBlIjoic2Vzc2lvbiJ9.4OngOyuxNjHZjcdnNfJBrjIHJ6ngOtRLvsmGb5YtPyg
user_01KBG1M6T4YYCHH7T4FKPYMQ0C::eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhdXRoMHx1c2VyXzAxS0JHMU02VDRZWUNISDdUNEZLUFlNUTBDIiwidGltZSI6IjE3NjQ2OTY0MjUiLCJyYW5kb21uZXNzIjoiMGM5ODYzM2YtZWFhNi00NmQxIiwiZXhwIjoxNzY5ODgwNDI1LCJpc3MiOiJodHRwczovL2F1dGhlbnRpY2F0aW9uLmN1cnNvci5zaCIsInNjb3BlIjoib3BlbmlkIHByb2ZpbGUgZW1haWwgb2ZmbGluZV9hY2Nlc3MiLCJhdWQiOiJodHRwczovL2N1cnNvci5jb20iLCJ0eXBlIjoid2ViIn0.JOLYQi1ZAM1Xmruz7goP1M79wb3wOsMuByaO6MGqLeg`
    }
    
    // 创建 Blob 并下载
    const blob = new Blob(['\ufeff' + content], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = filename
    link.click()
    URL.revokeObjectURL(link.href)
  }

  // 辅助函数：解析 Token 并提取信息（添加时不获取 longTermToken，切换账号时再获取）
  const parseTokenInfo = (fullToken: string) => {
    let workosId = ''
    let longTermToken = '' // cookie 格式时留空，切换时再获取
    let cookieFormat = ''
    let emailFromToken = ''
    
    // 检查是否是 cookie 格式 (包含 %3A%3A 或 ::)
    const isCookieFormat = fullToken.includes('%3A%3A') || fullToken.includes('::')
    
    if (isCookieFormat) {
      // cookie 格式：只保存 cookie，不提取 longTermToken
      if (fullToken.includes('%3A%3A')) {
        const parts = fullToken.split('%3A%3A')
        workosId = parts[0] || ''
        cookieFormat = fullToken
      } else if (fullToken.includes('::')) {
        const parts = fullToken.split('::')
        workosId = parts[0] || ''
        const jwtPart = parts[1] || ''
        // 统一转为 %3A%3A 格式
        cookieFormat = `${workosId}%3A%3A${jwtPart}`
      }
      // longTermToken 留空，切换账号时再从 cookie 中提取
      longTermToken = ''
    } else {
      // 纯 JWT 格式，保存为 longTermToken
      longTermToken = fullToken
      cookieFormat = '' // 留空，切换时再生成
    }
    
    // 尝试从 JWT payload 中提取 workosId 和 email（仅用于显示）
    // 注意：cookie 格式时，我们需要临时提取 JWT 来获取 email，但不保存到 longTermToken
    try {
      let jwtForParsing = ''
      if (isCookieFormat) {
        // 临时提取 JWT 用于解析 email，但不保存
        if (fullToken.includes('%3A%3A')) {
          jwtForParsing = fullToken.split('%3A%3A')[1] || ''
        } else if (fullToken.includes('::')) {
          jwtForParsing = fullToken.split('::')[1] || ''
        }
      } else {
        jwtForParsing = fullToken
      }
      
      if (jwtForParsing && jwtForParsing.startsWith('eyJ')) {
        const jwtParts = jwtForParsing.split('.')
        if (jwtParts.length === 3) {
          const base64 = jwtParts[1].replace(/-/g, '+').replace(/_/g, '/')
          const padded = base64 + '='.repeat((4 - base64.length % 4) % 4)
          const payload = JSON.parse(atob(padded))
          
          // 提取 workosId（仅用于标识）
          if (!workosId && payload.sub) {
            workosId = payload.sub.split('|')[1] || payload.sub
          }
          
          // 提取 email
          if (payload.email) {
            emailFromToken = payload.email
          }
        }
      }
    } catch (e) {
      console.warn('无法解析 JWT:', e)
    }
    
    return { workosId, longTermToken, cookieFormat, emailFromToken }
  }

  // 导出结果
  // 添加到账号列表
  const handleAddToList = async (result: VerificationResult) => {
    if (!result.fullToken) {
      onShowDialog({
        title: '错误',
        message: '无法获取 Token 信息',
        type: 'error',
        onConfirm: () => {}
      })
      return
    }

    try {
      // 解析 token 格式
      const { workosId, longTermToken, cookieFormat, emailFromToken } = parseTokenInfo(result.fullToken)
      
      // 确定邮箱：优先使用验号结果，其次使用 JWT 中的，最后使用 workosId
      const email = result.email || emailFromToken || (workosId ? `账号_${workosId.slice(-8)}` : `账号_${Date.now()}`)
      
      console.log('📝 添加账号:', { 
        email, 
        resultEmail: result.email, 
        emailFromToken, 
        workosId,
        plan: result.plan 
      })
      
      // 获取现有的账号列表
      const existingTokens = await window.electronAPI.getTokens()
      
      // 检查是否已存在该账号（通过邮箱或 workosId 匹配）
      const existingToken = existingTokens.find((t: any) => 
        (email && (t.name === email || t.accountInfo?.email === email)) ||
        (workosId && t.accountInfo?.id === workosId)
      )
      
      // 构建完整的 accountInfo
      // 如果是纯 JWT 格式，cookieFormat 为空，切换账号时再转换
      const accountInfo: any = {
        email: email,
        plan: result.plan,
        subscriptionStatus: result.subscriptionStatus,
        longTermToken: longTermToken,
        cookieFormat: cookieFormat, // 可能为空（纯JWT时）
        id: workosId || undefined
      }
      
      // 保存的 token 值：优先使用 cookieFormat，如果为空则使用原始 fullToken
      const tokenToSave = cookieFormat || result.fullToken!
      
      // 添加过期时间
      if (result.expiryDate) {
        accountInfo.trialExpiryDate = result.expiryDate
        accountInfo.isTrial = true
        const expiryTime = new Date(result.expiryDate).getTime()
        const now = Date.now()
        const daysRemaining = Math.ceil((expiryTime - now) / (1000 * 60 * 60 * 24))
        if (daysRemaining > 0) {
          accountInfo.daysRemainingOnTrial = daysRemaining
        }
      }
      
      // 添加额度信息
      if (result.usage) {
        accountInfo.quota = {
          used: result.usage.used,
          limit: result.usage.limit,
          remaining: result.usage.limit !== null ? result.usage.limit - result.usage.used : null
        }
      }
      
      // 构建 usage 对象用于前端显示
      const usageData = result.usage ? {
        used: result.usage.used,
        limit: result.usage.limit,
        remaining: result.usage.limit !== null ? result.usage.limit - result.usage.used : null,
        percentage: result.usage.percentage
      } : undefined
      
      let saveResult
      if (existingToken) {
        // 更新已存在的账号
        saveResult = await window.electronAPI.saveToken({
          id: existingToken.id,
          name: email,
          token: tokenToSave,
          isActive: existingToken.isActive,
          accountInfo: accountInfo,
          usage: usageData,
          createTime: existingToken.createTime || new Date().toISOString()
        })

        if (saveResult.success) {
          onShowDialog({
            title: '成功',
            message: `账号 ${email} 已更新`,
            type: 'info',
            onConfirm: () => {}
          })
          onAccountAdded?.()
        } else {
          throw new Error('更新失败')
        }
      } else {
        // 添加新账号
        saveResult = await window.electronAPI.saveToken({
          id: `token_${Date.now()}`,
          name: email,
          token: tokenToSave,
          isActive: false,
          accountInfo: accountInfo,
          usage: usageData,
          createTime: new Date().toISOString()
        })

        if (saveResult.success) {
          onShowDialog({
            title: '成功',
            message: `账号 ${email} 已添加到列表`,
            type: 'info',
            onConfirm: () => {}
          })
          onAccountAdded?.()
        } else {
          throw new Error('保存失败')
        }
      }
    } catch (error: any) {
      console.error('添加账号失败:', error)
      onShowDialog({
        title: '错误',
        message: `操作失败: ${error.message}`,
        type: 'error',
        onConfirm: () => {}
      })
    }
  }

  // 添加全部通过的账号到列表
  const handleAddAllToList = async () => {
    // 获取所有通过验证的账号（success 和 warning 状态，必须有 fullToken）
    const passedResults = results.filter(r => 
      (r.status === 'success' || r.status === 'warning') && r.fullToken
    )
    
    if (passedResults.length === 0) {
      onShowDialog({
        title: '提示',
        message: '没有通过验证的账号可以添加',
        type: 'warning',
        onConfirm: () => {}
      })
      return
    }

    let addedCount = 0
    let updatedCount = 0
    let failedCount = 0
    
    try {
      // 获取现有的账号列表
      const existingTokens = await window.electronAPI.getTokens()
      
      for (const result of passedResults) {
        try {
          // 使用辅助函数解析 token
          const { workosId, longTermToken, cookieFormat, emailFromToken } = parseTokenInfo(result.fullToken!)
          
          // 确定邮箱
          const email = result.email || emailFromToken || (workosId ? `账号_${workosId.slice(-8)}` : `账号_${Date.now()}`)
          
          // 检查是否已存在该账号
          const existingToken = existingTokens.find((t: any) => 
            (email && (t.name === email || t.accountInfo?.email === email)) ||
            (workosId && t.accountInfo?.id === workosId)
          )
          
          // 构建 accountInfo
          // 如果是纯 JWT 格式，cookieFormat 为空，切换账号时再转换
          const accountInfo: any = {
            email: email,
            plan: result.plan,
            subscriptionStatus: result.subscriptionStatus,
            longTermToken: longTermToken,
            cookieFormat: cookieFormat, // 可能为空（纯JWT时）
            id: workosId || undefined
          }
          
          // 保存的 token 值：优先使用 cookieFormat，如果为空则使用原始 fullToken
          const tokenToSave = cookieFormat || result.fullToken!
          
          if (result.expiryDate) {
            accountInfo.trialExpiryDate = result.expiryDate
            accountInfo.isTrial = true
            const expiryTime = new Date(result.expiryDate).getTime()
            const now = Date.now()
            const daysRemaining = Math.ceil((expiryTime - now) / (1000 * 60 * 60 * 24))
            if (daysRemaining > 0) {
              accountInfo.daysRemainingOnTrial = daysRemaining
            }
          }
          
          if (result.usage) {
            accountInfo.quota = {
              used: result.usage.used,
              limit: result.usage.limit,
              remaining: result.usage.limit !== null ? result.usage.limit - result.usage.used : null
            }
          }
          
          const usageData = result.usage ? {
            used: result.usage.used,
            limit: result.usage.limit,
            remaining: result.usage.limit !== null ? result.usage.limit - result.usage.used : null,
            percentage: result.usage.percentage
          } : undefined
          
          let saveResult
          if (existingToken) {
            // 更新
            saveResult = await window.electronAPI.saveToken({
              id: existingToken.id,
              name: email,
              token: tokenToSave,
              isActive: existingToken.isActive,
              accountInfo: accountInfo,
              usage: usageData,
              createTime: existingToken.createTime || new Date().toISOString()
            })
            if (saveResult.success) updatedCount++
            else failedCount++
          } else {
            // 新增
            saveResult = await window.electronAPI.saveToken({
              id: `token_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
              name: email,
              token: tokenToSave,
              isActive: false,
              accountInfo: accountInfo,
              usage: usageData,
              createTime: new Date().toISOString()
            })
            if (saveResult.success) {
              addedCount++
              // 更新 existingTokens 避免重复添加
              existingTokens.push({ name: email, accountInfo: { email: email, id: workosId } })
            } else {
              failedCount++
            }
          }
        } catch (error) {
          console.error('添加账号失败:', result.email || result.token, error)
          failedCount++
        }
      }
      
      // 刷新账号列表
      onAccountAdded?.()
      
      // 显示结果
      let message = ''
      if (addedCount > 0) message += `新增 ${addedCount} 个账号`
      if (updatedCount > 0) message += `${message ? '，' : ''}更新 ${updatedCount} 个账号`
      if (failedCount > 0) message += `${message ? '，' : ''}失败 ${failedCount} 个`
      
      onShowDialog({
        title: '批量添加完成',
        message: message || '没有账号被添加',
        type: failedCount > 0 ? 'warning' : 'info',
        onConfirm: () => {}
      })
    } catch (error: any) {
      onShowDialog({
        title: '错误',
        message: `批量添加失败: ${error.message}`,
        type: 'error',
        onConfirm: () => {}
      })
    }
  }

  const handleExportResults = () => {
    if (results.length === 0) return

    const successResults = results.filter(r => r.status === 'success' || r.status === 'warning')
    if (successResults.length === 0) {
      onShowDialog({
        title: '提示',
        message: '没有成功验证的账号可以导出',
        type: 'warning',
        onConfirm: () => {}
      })
      return
    }

    // 生成 CSV 内容
    const headers = ['邮箱', '订阅类型', '订阅状态', '过期时间', '已用额度', '总额度', '使用率', '最近7天使用', '最后使用时间', '验号时间', 'Token']
    const csvContent = [
      headers.join(','),
      ...successResults.map(r => [
        r.email || '',
        r.plan || '',
        r.subscriptionStatus || '',
        r.expiryDate ? new Date(r.expiryDate).toLocaleDateString('zh-CN') : '',
        r.usage?.used || '',
        r.usage?.limit || '',
        r.usage?.percentage ? `${r.usage.percentage.toFixed(1)}%` : '',
        r.recentUsage?.last7Days || '',
        r.recentUsage?.lastUsageTime || '',
        r.verifyTime || '',
        r.token
      ].map(cell => `"${cell}"`).join(','))
    ].join('\n')

    // 下载文件
    const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `验号结果_${new Date().toLocaleDateString('zh-CN').replace(/\//g, '-')}.csv`
    link.click()
  }

  const successCount = results.filter(r => r.status === 'success').length
  const warningCount = results.filter(r => r.status === 'warning').length
  const failedCount = results.filter(r => r.status === 'failed').length
  const pendingCount = results.filter(r => r.status === 'pending').length

  // 筛选结果（单个验证时不筛选）
  const filteredResults = mode === 'single' ? results : results.filter(result => {
    if (filterStatus === 'all') return true
    return result.status === filterStatus
  })

  return (
    <div className="verification-modal-backdrop" onClick={handleBackdropClick}>
      <div className="verification-modal-container" onClick={(e) => e.stopPropagation()}>
        <div className="verification-modal-header">
          <h3 className="verification-modal-title">🔍 账号验号</h3>
          <button 
            className="verification-modal-close"
            onClick={onClose}
            aria-label="关闭"
          >
            ×
          </button>
        </div>
        
        <div className="verification-modal-content">
          {/* 模式切换 */}
          <div className="verification-mode-tabs">
            <button
              className={`verification-mode-tab ${mode === 'single' ? 'active' : ''}`}
              onClick={() => setMode('single')}
            >
              单个验号
            </button>
            <button
              className={`verification-mode-tab ${mode === 'batch' ? 'active' : ''}`}
              onClick={() => setMode('batch')}
            >
              批量验号
            </button>
          </div>

          {/* 验证规则提示 */}
          <div className="verification-rules-hint">
            <div className="rules-title">✅ 验证规则</div>
            <div className="rules-content">
              只有同时满足以下条件才算验证成功：
              <span className="rule-item">① 订阅类型包含 Pro Trial</span>
              <span className="rule-item">② 订阅状态为 trialing</span>
              <span className="rule-item">③ 未过期</span>
              <span className="rule-item">④ 额度未用完</span>
            </div>
          </div>

          {/* 单个验号 */}
          {mode === 'single' && (
            <div className="verification-single-section">
              <div className="verification-format-tabs">
                <button
                  className={`format-tab ${singleFormat === 'token' ? 'active' : ''}`}
                  onClick={() => setSingleFormat('token')}
                >
                  Token 格式
                </button>
                <button
                  className={`format-tab ${singleFormat === 'cookie' ? 'active' : ''}`}
                  onClick={() => setSingleFormat('cookie')}
                >
                  Cookie 格式
                </button>
              </div>

              <textarea
                className="verification-input"
                placeholder={singleFormat === 'token' 
                  ? '请输入 Token (eyJ 开头)' 
                  : '请输入 Cookie 格式 (user_xxx%3A%3Aeyj... 或 user_xxx::eyj...)'}
                value={tokenInput}
                onChange={(e) => setTokenInput(e.target.value)}
                rows={4}
                disabled={verifying}
              />

              <button
                className="verification-submit-btn"
                onClick={handleSingleVerify}
                disabled={verifying || !tokenInput.trim()}
              >
                {verifying ? '验证中...' : '开始验证'}
              </button>
            </div>
          )}

          {/* 批量验号 */}
          {mode === 'batch' && (
            <div className="verification-batch-section">
              <div className="verification-format-tabs">
                <button
                  className={`format-tab ${batchFormat === 'token' ? 'active' : ''}`}
                  onClick={() => setBatchFormat('token')}
                >
                  Token 格式
                </button>
                <button
                  className={`format-tab ${batchFormat === 'cookie' ? 'active' : ''}`}
                  onClick={() => setBatchFormat('cookie')}
                >
                  Cookie 格式
                </button>
              </div>

              <div className="batch-upload-area">
                <div className="upload-icon">📄</div>
                <h4>上传表格文件</h4>
                <p className="upload-hint">
                  支持 CSV 格式，表头为 "{batchFormat === 'token' ? 'token' : 'cookie'}"
                </p>
                <p className="upload-hint">每行一个账号，最多支持 100 个</p>
                
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv,.xlsx,.xls"
                  onChange={handleFileUpload}
                  style={{ display: 'none' }}
                />
                
                <button
                  className="upload-btn"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={verifying}
                >
                  {verifying ? '验证中...' : '📁 选择文件'}
                </button>
              </div>

              <div className="batch-template-hint">
                <div className="template-header">
                  <span className="template-title">📋 CSV 模板示例：</span>
                  <button 
                    className="download-template-btn"
                    onClick={() => handleDownloadTemplate(batchFormat)}
                  >
                    📥 下载示例文件
                  </button>
                </div>
                <pre className="template-code">
{batchFormat === 'token' ? (
  <>token{'\n'}eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...{'\n'}eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...</>
) : (
  <>cookie{'\n'}user_01KB0CR6X1BH2WRHB897DDT77Z%3A%3AeyJ...{'\n'}user_01KB0CR6X1BH2WRHB897DDT77Z::eyJ...</>
)}
                </pre>
              </div>
            </div>
          )}

          {/* 验证结果 */}
          {results.length > 0 && (
            <div className="verification-results-section">
              <div className="results-header">
                <div className="results-title-container">
                  <h4 className="results-title">验证结果</h4>
                  {deduplicationInfo && (
                    <div className="deduplication-info">
                      <span className="dedup-item">📋 原始: {deduplicationInfo.original} 条</span>
                      <span className="dedup-item dedup-duplicates">♻️ 重复: {deduplicationInfo.duplicates} 条</span>
                      <span className="dedup-item dedup-unique">✨ 剩余: {deduplicationInfo.unique} 条</span>
                    </div>
                  )}
                </div>
                <div className="results-stats">
                  {pendingCount > 0 && <span className="stat-pending">⏳ {pendingCount}</span>}
                  {successCount > 0 && <span className="stat-success">✅ {successCount}</span>}
                  {warningCount > 0 && <span className="stat-warning">⚠️ {warningCount}</span>}
                  {failedCount > 0 && <span className="stat-failed">❌ {failedCount}</span>}
                </div>
                {(successCount > 0 || warningCount > 0) && (
                  <div className="results-actions">
                    <button className="add-all-btn" onClick={handleAddAllToList}>
                      ➕ 添加全部 ({successCount + warningCount})
                    </button>
                    {mode === 'batch' && (
                      <button className="export-btn" onClick={handleExportResults}>
                        📥 导出结果
                      </button>
                    )}
                  </div>
                )}
              </div>

              {/* 筛选按钮（仅批量验证时显示） */}
              {mode === 'batch' && results.length > 1 && (
                <div className="filter-buttons">
                  <button 
                    className={`filter-btn ${filterStatus === 'all' ? 'active' : ''}`}
                    onClick={() => setFilterStatus('all')}
                  >
                    全部 ({results.length})
                  </button>
                  <button 
                    className={`filter-btn filter-success ${filterStatus === 'success' ? 'active' : ''}`}
                    onClick={() => setFilterStatus('success')}
                  >
                    ✅ 通过 ({successCount})
                  </button>
                  <button 
                    className={`filter-btn filter-warning ${filterStatus === 'warning' ? 'active' : ''}`}
                    onClick={() => setFilterStatus('warning')}
                  >
                    ⚠️ 警告 ({warningCount})
                  </button>
                  <button 
                    className={`filter-btn filter-failed ${filterStatus === 'failed' ? 'active' : ''}`}
                    onClick={() => setFilterStatus('failed')}
                  >
                    ❌ 失败 ({failedCount})
                  </button>
                </div>
              )}

              <div className="results-list">
                {filteredResults.map((result, index) => (
                  <div key={index} className={`result-item ${result.status}`}>
                    <div className="result-header">
                      <span className="result-status-icon">
                        {result.status === 'pending' && '⏳'}
                        {result.status === 'success' && '✅'}
                        {result.status === 'warning' && '⚠️'}
                        {result.status === 'failed' && '❌'}
                      </span>
                      <span className="result-email">{result.email || result.token}</span>
                    </div>
                    
                    {result.status === 'warning' && result.warning && (
                      <div className="result-warning-banner">
                        <span className="warning-icon">⚠️</span>
                        <span className="warning-text">{result.warning}</span>
                      </div>
                    )}
                    
                    {(result.status === 'success' || result.status === 'warning') && (
                      <div className="result-details">
                        <div className="result-detail-item">
                          <span className="detail-label">订阅:</span>
                          <span className="detail-value">{result.plan}</span>
                        </div>
                        {result.subscriptionStatus && (
                          <div className="result-detail-item">
                            <span className="detail-label">状态:</span>
                            <span className={`detail-value subscription-status ${result.subscriptionStatus}`}>
                              {result.subscriptionStatus}
                            </span>
                          </div>
                        )}
                        {result.expiryDate && (
                          <div className="result-detail-item">
                            <span className="detail-label">过期:</span>
                            <span className="detail-value">
                              {new Date(result.expiryDate).toLocaleDateString('zh-CN')}
                            </span>
                          </div>
                        )}
                        {result.usage && (
                          <div className="result-detail-item">
                            <span className="detail-label">额度:</span>
                            <span className="detail-value">
                              {result.usage.used} / {result.usage.limit || '∞'}
                              {result.usage.percentage !== null && 
                                ` (${result.usage.percentage.toFixed(1)}%)`}
                            </span>
                          </div>
                        )}
                        {result.recentUsage && (
                          <div className="result-detail-item">
                            <span className="detail-label">7天使用:</span>
                            <span className="detail-value">
                              {result.recentUsage.last7Days} 次
                              {result.recentUsage.totalAmount > 0 && 
                                ` ($${(result.recentUsage.totalAmount / 100).toFixed(2)})`}
                            </span>
                          </div>
                        )}
                        {result.recentUsage && (
                          <div className="result-detail-item">
                            <span className="detail-label">最后使用:</span>
                            <span className="detail-value">
                              {result.recentUsage.lastUsageTime || '暂无记录'}
                            </span>
                          </div>
                        )}
                        {result.verifyTime && (
                          <div className="result-detail-item">
                            <span className="detail-label">验号时间:</span>
                            <span className="detail-value">{result.verifyTime}</span>
                          </div>
                        )}
                      </div>
                    )}

                    {/* 添加到列表按钮 */}
                    {result.status === 'success' && (
                      <div className="result-actions">
                        <button 
                          className="btn-add-to-list"
                          onClick={() => handleAddToList(result)}
                        >
                          ➕ 添加到列表
                        </button>
                      </div>
                    )}
                    
                    {result.status === 'failed' && (
                      <div className="result-error">
                        {result.error}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default TokenVerificationModal

