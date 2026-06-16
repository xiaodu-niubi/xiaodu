import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api/index.js'

export const useChatStore = defineStore('chat', () => {
  const conversations = ref([])
  const currentConversationId = ref(null)
  const messages = ref([])
  const isLoading = ref(false)
  const streamingContent = ref('')
  const statusText = ref('')
  const error = ref(null)
  const sidebarOpen = ref(true)
  let abortController = null

  const currentConversation = computed(() =>
    conversations.value.find(c => c.id === currentConversationId.value)
  )

  async function loadConversations() {
    try {
      conversations.value = await api.listConversations()
    } catch (e) {
      console.error('加载对话列表失败:', e)
    }
  }

  async function selectConversation(id) {
    currentConversationId.value = id
    error.value = null
    try {
      const conv = await api.getConversation(id)
      messages.value = (conv.messages || []).map(m => ({
        id: m.id,
        role: m.role,
        content: m.content,
        tool_calls: m.tool_calls,
        created_at: m.created_at,
      }))
    } catch (e) {
      error.value = '加载对话失败'
    }
  }

  async function newConversation() {
    if (abortController) {
      abortController.abort()
      abortController = null
    }
    currentConversationId.value = null
    messages.value = []
    streamingContent.value = ''
    statusText.value = ''
    error.value = null
    isLoading.value = false
  }

  async function sendMessage(text) {
    if (!text.trim() || isLoading.value) return

    error.value = null
    isLoading.value = true
    streamingContent.value = ''

    // 添加用户消息
    messages.value.push({
      id: Date.now(),
      role: 'user',
      content: text,
    })

    // 添加占位的 AI 消息
    const aiMsgId = Date.now() + 1
    messages.value.push({
      id: aiMsgId,
      role: 'assistant',
      content: '',
    })

    abortController = api.sendMessageStream(
      text,
      currentConversationId.value,
      // onToken - 逐字追加
      (token) => {
        const msg = messages.value.find(m => m.id === aiMsgId)
        if (msg) {
          msg.content += token
          streamingContent.value += token
        }
      },
      // onStatus - 处理状态更新
      (status) => {
        const statusMap = {
          'analyzing': '正在分析...',
          'routing': '正在分配任务...',
          'executing_rag': '正在检索知识库...',
          'executing_tool': '正在执行工具...',
          'executing_web': '正在搜索网络...',
          'executing_memory': '正在读取记忆...',
          'executing_fallback': '正在生成回复...',
        }
        statusText.value = statusMap[status] || status
      },
      // onDone - 对话创建完成
      async (conversationId) => {
        currentConversationId.value = conversationId
        isLoading.value = false
        streamingContent.value = ''
        statusText.value = ''
        abortController = null
        await loadConversations()
      },
      // onError
      (errMsg) => {
        const msg = messages.value.find(m => m.id === aiMsgId)
        if (msg && !msg.content) {
          msg.content = `请求失败：${errMsg}`
        }
        error.value = errMsg || '请求失败，请检查后端服务'
        isLoading.value = false
        streamingContent.value = ''
        statusText.value = ''
        abortController = null
      }
    )
  }

  function stopGeneration() {
    if (abortController) {
      abortController.abort()
      abortController = null
    }
    isLoading.value = false
    statusText.value = ''
    streamingContent.value = ''
    // 如果有部分内容，保留它（不清空），以后可能补充完整
  }

  async function deleteConversation(id) {
    try {
      await api.deleteConversation(id)
      if (currentConversationId.value === id) {
        newConversation()
      }
      await loadConversations()
    } catch (e) {
      error.value = '删除对话失败'
    }
  }

  function toggleSidebar() {
    sidebarOpen.value = !sidebarOpen.value
  }

  return {
    conversations,
    currentConversationId,
    messages,
    isLoading,
    streamingContent,
    statusText,
    error,
    sidebarOpen,
    currentConversation,
    loadConversations,
    selectConversation,
    newConversation,
    sendMessage,
    stopGeneration,
    deleteConversation,
    toggleSidebar,
  }
})
