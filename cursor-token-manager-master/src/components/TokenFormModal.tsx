import React from 'react'
import TokenForm from './TokenForm'
import { Token } from '../App'
import '../styles/TokenFormModal.css'

interface TokenFormModalProps {
  show: boolean
  token: Token | null
  existingTokens?: Token[]
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

const TokenFormModal: React.FC<TokenFormModalProps> = ({
  show,
  token,
  existingTokens = [],
  onSave,
  onCancel,
  onShowDialog
}) => {
  if (!show) return null

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onCancel()
    }
  }

  const isViewMode = !!token

  return (
    <div className="token-form-modal-backdrop" onClick={handleBackdropClick}>
      <div 
        className={`token-form-modal-container ${isViewMode ? 'view-mode' : ''}`} 
        onClick={(e) => e.stopPropagation()}
      >
        <div className="token-form-modal-header">
          <h3 className="token-form-modal-title">
            {token ? '账号详情' : '批量添加账号'}
          </h3>
          <button 
            className="token-form-modal-close"
            onClick={onCancel}
            aria-label="关闭"
          >
            ×
          </button>
        </div>
        <div className="token-form-modal-content">
          <TokenForm
            token={token}
            existingTokens={existingTokens}
            onSave={onSave}
            onCancel={onCancel}
            onShowDialog={onShowDialog}
          />
        </div>
      </div>
    </div>
  )
}

export default TokenFormModal
