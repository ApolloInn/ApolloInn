/**
 * AURORA Web UI — Stitch Design
 * Client-side application logic
 */

(() => {
  'use strict';

  // ── Config ──
  const GATEWAY_URL = location.origin.replace(':3001', ':3000');
  const WS_URL = GATEWAY_URL.replace('http', 'ws') + '/ws';

  // ── State ──
  let sessionId = 'web-' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
  let sending = false;
  let currentAssistantEl = null;
  let ws = null;
  let messageCount = 0;

  // ── DOM refs ──
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  const chatMessages = $('#chatMessages');
  const chatInput = $('#chatInput');
  const sendBtn = $('#sendBtn');
  const welcomeScreen = $('#welcomeScreen');
  const statusDot = $('#statusDot');
  const statusLabel = $('#statusLabel');
  const footerLatency = $('#footerLatency');
  const footerGateway = $('#footerGateway');

  // ═══════════════ Tab Navigation ═══════════════

  $$('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
      const target = tab.dataset.tab;

      // Update tabs
      $$('.tab').forEach(t => t.classList.remove('active'));
      tab.classList.add('active');

      // Update content
      $$('.tab-content').forEach(c => c.classList.remove('active'));
      const content = $(`.tab-content[data-content="${target}"]`);
      if (content) content.classList.add('active');
    });
  });

  // ═══════════════ Settings Navigation ═══════════════

  $$('.settings-nav-item').forEach(item => {
    item.addEventListener('click', () => {
      const section = item.dataset.section;

      $$('.settings-nav-item').forEach(i => i.classList.remove('active'));
      item.classList.add('active');

      $$('.settings-panel').forEach(p => p.classList.remove('active'));
      const panel = $(`.settings-panel[data-panel="${section}"]`);
      if (panel) panel.classList.add('active');
    });
  });

  // ═══════════════ Chat ═══════════════

  // Auto-resize textarea
  chatInput.addEventListener('input', () => {
    chatInput.style.height = 'auto';
    chatInput.style.height = Math.min(chatInput.scrollHeight, 120) + 'px';
  });

  // Keyboard
  chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  sendBtn.addEventListener('click', sendMessage);

  // Suggestion chips
  $$('.suggestion-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      chatInput.value = chip.dataset.msg;
      sendMessage();
    });
  });

  function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function hideWelcome() {
    if (welcomeScreen) {
      welcomeScreen.style.display = 'none';
    }
  }

  function formatTime() {
    const now = new Date();
    return now.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
  }

  function addMessage(role, text) {
    hideWelcome();
    messageCount++;

    const wrapper = document.createElement('div');
    wrapper.className = `message ${role}`;

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.textContent = text;

    const meta = document.createElement('div');
    meta.className = 'message-meta';

    const sender = document.createElement('span');
    sender.className = 'message-sender';
    sender.textContent = role === 'user' ? 'Operator 01' : 'Aether Core';

    const time = document.createElement('span');
    time.className = 'message-time';
    time.textContent = formatTime();

    meta.appendChild(sender);
    meta.appendChild(time);

    if (role === 'user') {
      wrapper.appendChild(meta);
      wrapper.appendChild(bubble);
    } else {
      wrapper.appendChild(bubble);
      wrapper.appendChild(meta);
    }

    chatMessages.appendChild(wrapper);
    scrollToBottom();

    // Update session info
    updateSessionMeta();

    return bubble;
  }

  function addToolEvent(type, name, detail) {
    hideWelcome();
    const el = document.createElement('div');
    el.className = `tool-event ${type}`;
    el.innerHTML = `<span class="tool-name">${escapeHtml(name)}</span> ${escapeHtml(detail || '')}`;
    chatMessages.appendChild(el);
    scrollToBottom();
  }

  function showTyping() {
    removeTyping();
    const el = document.createElement('div');
    el.className = 'typing-indicator';
    el.id = 'typingIndicator';
    el.innerHTML = '<span></span><span></span><span></span>';
    chatMessages.appendChild(el);
    scrollToBottom();
  }

  function removeTyping() {
    const el = $('#typingIndicator');
    if (el) el.remove();
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function updateSessionMeta() {
    const sessionItem = $('.session-item');
    if (sessionItem) {
      const meta = sessionItem.querySelector('.session-meta');
      if (meta) {
        meta.textContent = `${formatTime()} · ${messageCount} 条消息`;
      }
    }
  }

  function updateGoal(text) {
    const goalText = $('.goal-text');
    if (goalText) goalText.textContent = text;
  }

  function addActiveTask(text, status) {
    const container = $('#activeTasks');
    if (!container) return;

    // Remove idle placeholder
    const idle = container.querySelector('.idle');
    if (idle) idle.remove();

    const el = document.createElement('div');
    el.className = `task-mini ${status}`;
    const icon = status === 'done' ? 'check_circle' : status === 'failed' ? 'error' : 'pending';
    el.innerHTML = `<span class="material-symbols-rounded">${icon}</span><span>${escapeHtml(text)}</span>`;
    container.appendChild(el);
  }

  // ═══════════════ Send Message (SSE) ═══════════════

  async function sendMessage() {
    const text = chatInput.value.trim();
    if (!text || sending) return;

    sending = true;
    sendBtn.disabled = true;
    chatInput.value = '';
    chatInput.style.height = 'auto';

    addMessage('user', text);
    updateGoal(text.slice(0, 40) + (text.length > 40 ? '...' : ''));
    showTyping();
    currentAssistantEl = null;

    const startTime = Date.now();

    try {
      const res = await fetch(`${GATEWAY_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, sessionId }),
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setConnected(true);

      const latency = Date.now() - startTime;
      footerLatency.textContent = `${latency}ms`;

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let toolCallCount = 0;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const raw = line.slice(6).trim();
          if (raw === '[DONE]') continue;

          try {
            const chunk = JSON.parse(raw);
            removeTyping();

            if (chunk.type === 'text' && chunk.text) {
              if (!currentAssistantEl) {
                currentAssistantEl = addMessage('assistant', '');
              }
              currentAssistantEl.textContent += chunk.text;
              scrollToBottom();
            } else if (chunk.type === 'tool_call') {
              toolCallCount++;
              addToolEvent('', chunk.name || 'tool', '调用中…');
              addActiveTask(chunk.name || 'tool', 'running');
            } else if (chunk.type === 'tool_result') {
              const ok = chunk.result?.startsWith('✓');
              addToolEvent(ok ? 'success' : 'error', '', chunk.result?.slice(0, 120) || '');
              addActiveTask(chunk.result?.slice(2, 30) || 'task', ok ? 'done' : 'failed');
            } else if (chunk.type === 'error') {
              addToolEvent('error', '错误', chunk.message || '');
            }
          } catch { /* ignore parse errors */ }
        }
      }

      // Update tool call count
      const toolCountEl = $('#toolCallCount');
      if (toolCountEl) {
        const current = parseInt(toolCountEl.textContent) || 0;
        toolCountEl.textContent = `${current + toolCallCount} 次`;
      }

    } catch (err) {
      removeTyping();
      addMessage('assistant', '连接失败: ' + err.message);
      setConnected(false);
      addLog('error', `连接失败: ${err.message}`);
    } finally {
      removeTyping();
      sending = false;
      sendBtn.disabled = false;
      chatInput.focus();
    }
  }

  // ═══════════════ Connection Status ═══════════════

  function setConnected(ok) {
    statusDot.classList.toggle('connected', ok);
    statusLabel.textContent = ok ? '在线' : '离线';
    footerGateway.textContent = ok ? '在线' : '离线';
  }

  async function checkHealth() {
    try {
      const start = Date.now();
      const res = await fetch(`${GATEWAY_URL}/health`);
      const latency = Date.now() - start;

      if (res.ok) {
        setConnected(true);
        footerLatency.textContent = `${latency}ms`;

        // Update connectivity panel
        const connList = $('#connectivityList');
        if (connList) {
          connList.innerHTML = `
            <div class="connectivity-item">
              <span class="connector-dot connected"></span>
              <div class="connectivity-info">
                <span>AURORA Gateway</span>
                <span class="connectivity-latency">延迟: ${latency}ms</span>
              </div>
            </div>
          `;
        }

        addLog('info', `Gateway 连接成功 (${latency}ms)`);
        return;
      }
    } catch {}

    setConnected(false);
    addLog('warn', 'Gateway 未连接');
  }

  // Test connectivity button
  const testConnBtn = $('#testConnBtn');
  if (testConnBtn) {
    testConnBtn.addEventListener('click', checkHealth);
  }

  // ═══════════════ Logging ═══════════════

  function addLog(level, msg) {
    const container = $('#logContainer');
    if (!container) return;

    const now = new Date();
    const time = now.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });

    const entry = document.createElement('div');
    entry.className = `log-entry ${level}`;
    entry.innerHTML = `
      <span class="log-level">${level.toUpperCase()}</span>
      <span class="log-time">${time}</span>
      <span class="log-msg">${escapeHtml(msg)}</span>
    `;

    container.appendChild(entry);
    container.scrollTop = container.scrollHeight;

    // Keep max 200 entries
    while (container.children.length > 200) {
      container.removeChild(container.firstChild);
    }
  }

  // ═══════════════ Slider value display ═══════════════

  $$('.settings-slider').forEach(slider => {
    const valueEl = slider.parentElement.querySelector('.slider-value');
    if (!valueEl) return;

    slider.addEventListener('input', () => {
      const val = parseInt(slider.value);
      if (slider.max === '200') {
        // Temperature slider
        valueEl.textContent = (val / 100).toFixed(1);
      } else {
        // Percentage sliders
        if (val < 30) valueEl.textContent = '简洁';
        else if (val < 70) valueEl.textContent = '适中';
        else valueEl.textContent = '详细';
      }
    });
  });

  // ═══════════════ Keyboard Shortcuts ═══════════════

  document.addEventListener('keydown', (e) => {
    // Cmd+N: New session
    if ((e.metaKey || e.ctrlKey) && e.key === 'n') {
      e.preventDefault();
      sessionId = 'web-' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
      chatMessages.innerHTML = '';
      if (welcomeScreen) welcomeScreen.style.display = '';
      chatMessages.appendChild(welcomeScreen);
      messageCount = 0;
      currentAssistantEl = null;
      updateSessionMeta();
      chatInput.focus();
    }

    // Cmd+,: Settings
    if ((e.metaKey || e.ctrlKey) && e.key === ',') {
      e.preventDefault();
      const settingsTab = $('.tab[data-tab="settings"]');
      if (settingsTab) settingsTab.click();
    }
  });

  // ═══════════════ Init ═══════════════

  addLog('info', 'AURORA Web UI 已启动');
  addLog('info', `Session: ${sessionId}`);
  checkHealth();
  chatInput.focus();

  // Periodic health check
  setInterval(checkHealth, 30000);

})();
