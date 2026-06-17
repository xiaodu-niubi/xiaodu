import axios from 'axios'

const client = axios.create({
  baseURL: '/api',
  timeout: 120000,
  headers: { 'Content-Type': 'application/json' },
})

// SSE 流式请求，返回 AbortController 用于取消
function sendMessageStream(message, conversationId, onToken, onStatus, onDone, onError) {
  const controller = new AbortController()

  async function run() {
    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message,
          conversation_id: conversationId,
          stream: true,
        }),
        signal: controller.signal,
      })

    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: response.statusText }))
      throw new Error(err.detail || `HTTP ${response.status}`)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            if (data.type === 'token') {
              onToken(data.content)
            } else if (data.type === 'status') {
              onStatus && onStatus(data.content)
            } else if (data.type === 'error') {
              onError && onError(data.content || '服务器错误')
            } else if (data.type === 'done' && data.conversation_id) {
              onDone(data.conversation_id)
            }
          } catch (e) { console.warn('SSE parse error:', line, e) }
        }
      }
    }
  } catch (e) {
    if (e.name === 'AbortError') return
    onError(e.message)
  }
  }

  run()
  return controller
}

export default {
  // SSE 流式
  sendMessageStream,

  // 普通请求
  async sendMessage(message, conversationId = null) {
    const resp = await client.post('/chat', {
      message,
      conversation_id: conversationId,
      stream: false,
    })
    return resp.data
  },

  // Conversations
  async listConversations(limit = 50) {
    const resp = await client.get('/conversations', { params: { limit } })
    return resp.data.conversations || []
  },

  async getConversation(id) {
    const resp = await client.get(`/conversations/${id}`)
    return resp.data
  },

  async createConversation(title = 'New Conversation') {
    const resp = await client.post('/conversations', { title })
    return resp.data
  },

  async deleteConversation(id) {
    await client.delete(`/conversations/${id}`)
  },

  async updateConversationTitle(id, title) {
    await client.put(`/conversations/${id}`, { title })
  },

  // Knowledge
  async listKnowledge() {
    const resp = await client.get('/knowledge/list')
    return resp.data.documents || []
  },

  async uploadKnowledge(file) {
    const form = new FormData()
    form.append('file', file)
    const resp = await client.post('/knowledge/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return resp.data
  },

  async reloadKnowledge() {
    const resp = await client.post('/knowledge/reload')
    return resp.data
  },

  // Tools
  async listTools() {
    const resp = await client.get('/tools')
    return resp.data.tools || []
  },

  // Health
  async healthCheck() {
    const resp = await client.get('/health')
    return resp.data
  },
}
