import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api, { errorText } from '../api/index.js'

export const useChatStore = defineStore('chat', () => {
  const conversations = ref([]), currentConversationId = ref(null), messages = ref([])
  const isLoading = ref(false), statusText = ref(''), error = ref(null)
  const sidebarOpen = ref(window.innerWidth > 900)
  const panelOpen = ref(false), panelTab = ref('sources'), selectedMessageId = ref(null)
  const panelWidth = ref(370), artifactDrafts = ref({})
  const page = ref('workspace'), mode = ref('knowledge'), useWeb = ref(false)
  const documents = ref([]), selectedDocumentIds = ref([]), libraryError = ref('')
  const sources = ref([]), activeTools = ref([]), loadingConversation = ref(false)
  const historyError = ref(''), draft = ref(''), selectionVersion = ref(0)
  let controller = null, epoch = 0
  const currentConversation = computed(() => conversations.value.find(c => c.id === currentConversationId.value))
  const selectedMessage = computed(() => messages.value.find(m => m.id === selectedMessageId.value)
    || [...messages.value].reverse().find(m => m.role === 'assistant' && m.content))
  const currentSources = computed(() => selectedMessage.value?.metadata?.sources || sources.value)
  const statusMap = { analyzing: '正在理解任务', executing_search: '正在查找资料',
    executing_tool: '正在执行工具', generating: '正在整理回答', routing: '正在准备任务' }

  async function loadConversations() {
    try { conversations.value = await api.listConversations(); historyError.value = '' }
    catch (err) { historyError.value = '历史记录加载失败：' + errorText(err) }
  }
  async function loadDocuments() {
    try {
      documents.value = await api.listKnowledge(); libraryError.value = ''
      selectedDocumentIds.value = selectedDocumentIds.value.filter(id => documents.value.some(d => d.id === id && d.status === 'ready'))
    } catch (err) { libraryError.value = errorText(err) }
  }
  function stopGeneration() {
    epoch++
    controller?.abort(); controller = null
    const last = messages.value.find(m => m.metadata?.status === 'running')
    if (last) last.metadata.status = 'stopped'
    isLoading.value = false; statusText.value = ''
  }
  async function selectConversation(id) {
    stopGeneration()
    const requestEpoch = ++epoch
    currentConversationId.value = id; error.value = null
    loadingConversation.value = true; page.value = 'workspace'
    messages.value = []; sources.value = []; activeTools.value = []; selectedMessageId.value = null
    if (window.innerWidth <= 900) sidebarOpen.value = false
    try {
      const conv = await api.getConversation(id)
      if (requestEpoch !== epoch) return
      messages.value = (conv.messages || []).map(m => ({ ...m,
        metadata: typeof m.metadata === 'string' ? JSON.parse(m.metadata) : m.metadata || {},
        tool_calls: typeof m.tool_calls === 'string' ? JSON.parse(m.tool_calls) : m.tool_calls || [],
      }))
      // A refreshed running task cannot be attached to the previous HTTP stream.
      messages.value.forEach(m => {
        if (m.metadata.status === 'running') m.metadata.status = 'interrupted'
      })
      selectionVersion.value++
    } catch (err) { if (requestEpoch === epoch) error.value = errorText(err) }
    finally { if (requestEpoch === epoch) loadingConversation.value = false }
  }
  function newConversation(nextMode = 'knowledge') {
    stopGeneration()
    currentConversationId.value = null; messages.value = []; statusText.value = ''
    error.value = null; sources.value = []; activeTools.value = []; selectedMessageId.value = null
    loadingConversation.value = false; mode.value = nextMode; page.value = 'workspace'; panelOpen.value = false
    draft.value = ''; selectionVersion.value++
    if (window.innerWidth <= 900) sidebarOpen.value = false
  }
  function openPanel(message, tab = 'sources') {
    selectedMessageId.value = message.id; panelTab.value = tab; panelOpen.value = true; selectionVersion.value++
  }
  function sendMessage(text) {
    text = text.trim()
    if (!text || isLoading.value || loadingConversation.value) return
    if (mode.value === 'compare' && selectedDocumentIds.value.length < 2) {
      error.value = '对比文档前，请选择至少两份已就绪的资料。'; return
    }
    error.value = null; sources.value = []; activeTools.value = []
    isLoading.value = true; statusText.value = '正在准备任务'
    const requestEpoch = ++epoch
    const user = { id: crypto.randomUUID(), role: 'user', content: text, created_at: new Date().toISOString() }
    const assistant = { id: crypto.randomUUID(), role: 'assistant', content: '', tool_calls: [],
      metadata: { status: 'running', sources: [], mode: mode.value }, created_at: new Date().toISOString() }
    messages.value.push(user, assistant)
    const localId = assistant.id
    selectedMessageId.value = localId
    const find = () => messages.value.find(m => m.localId === localId || m.id === localId)
    controller = api.sendMessageStream({
      message: text, conversation_id: currentConversationId.value, mode: mode.value,
      document_ids: selectedDocumentIds.value, use_web: useWeb.value,
    }, event => {
      if (requestEpoch !== epoch) return
      const msg = find()
      if (!msg) return
      if (event.type === 'session') {
        currentConversationId.value = event.conversation_id
        msg.localId = localId; msg.id = event.message_id; msg.metadata.task_id = event.task_id
        selectedMessageId.value = msg.id
        loadConversations()
      } else if (event.type === 'token') msg.content += event.content
      else if (event.type === 'reset') msg.content = ''
      else if (event.type === 'status') statusText.value = statusMap[event.content] || '正在处理任务'
      else if (event.type === 'sources') {
        sources.value = event.metadata?.sources || []; msg.metadata.sources = sources.value
      } else if (event.type === 'tool') {
        const entry = event.metadata
        const index = msg.tool_calls.findIndex(t => t.id === entry.id)
        if (index >= 0) msg.tool_calls[index] = entry
        else msg.tool_calls.push(entry)
        activeTools.value = [...msg.tool_calls]
      } else if (event.type === 'done') {
        msg.metadata.status = 'completed'; currentConversationId.value = event.conversation_id
        isLoading.value = false; statusText.value = ''; controller = null
        loadConversations()
        if (mode.value === 'report') { panelTab.value = 'artifact'; panelOpen.value = true; selectionVersion.value++ }
      }
    }, message => {
      if (requestEpoch !== epoch) return
      const msg = find()
      if (msg) { msg.metadata.status = 'error'; msg.metadata.error = message }
      error.value = message; isLoading.value = false; statusText.value = ''; controller = null
    })
  }
  function retryMessage(message) {
    const index = messages.value.findIndex(m => m.id === message.id)
    const user = messages.value.slice(0, index).reverse().find(m => m.role === 'user')
    if (user) sendMessage(user.content)
  }
  async function deleteConversation(id) {
    try {
      await api.deleteConversation(id)
      if (currentConversationId.value === id) newConversation()
      await loadConversations()
    } catch (err) { error.value = errorText(err) }
  }
  return { conversations, currentConversationId, currentConversation, messages, isLoading, statusText, error,
    sidebarOpen, panelOpen, panelTab, panelWidth, artifactDrafts, selectedMessageId, selectedMessage, currentSources, page, mode, useWeb,
    documents, selectedDocumentIds, libraryError, sources, activeTools, loadingConversation, historyError, draft,
    selectionVersion, loadConversations, loadDocuments, selectConversation, newConversation, sendMessage,
    stopGeneration, retryMessage, deleteConversation, openPanel }
})
