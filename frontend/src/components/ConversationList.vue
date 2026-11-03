<template>
  <aside class="sidebar" aria-label="工作空间导航">
    <div class="sidebar-brand"><img src="@/image/deepseek.webp" alt="" /><div><strong>DeepSeek</strong><span>知识与研究工作台</span></div><button class="icon-button mobile-close" aria-label="关闭导航" @click="store.sidebarOpen = false"><AppIcon name="close" :size="18" /></button></div>
    <button class="button new-task" @click="store.newConversation()"><AppIcon name="plus" :size="18" />新任务<span class="new-task-hint">开始</span></button>
    <nav class="primary-navigation">
      <button v-for="item in navigation" :key="item.id" :class="{ active: store.page === item.id }" @click="navigate(item.id)"><AppIcon :name="item.icon" :size="18" />{{ item.label }}<span v-if="item.id === 'knowledge' && store.documents.length" class="nav-count">{{ store.documents.length }}</span></button>
    </nav>
    <div class="history-heading"><span>最近任务</span><button class="icon-button" aria-label="刷新历史任务" title="刷新" @click="store.loadConversations()"><AppIcon name="refresh" :size="14" /></button></div>
    <label class="sidebar-search"><AppIcon name="search" :size="14" /><input v-model="query" placeholder="搜索任务" aria-label="搜索历史任务" /></label>
    <div class="conversation-list">
      <p v-if="store.historyError" class="sidebar-empty">{{ store.historyError }}<button class="text-button" @click="store.loadConversations()">重试</button></p>
      <p v-else-if="!filtered.length" class="sidebar-empty">{{ query ? '没有匹配的任务' : '开始任务后，记录会出现在这里' }}</p>
      <div v-for="conv in filtered" :key="conv.id" class="conversation-item" :class="{ active: store.page === 'workspace' && conv.id === store.currentConversationId }">
        <div v-if="renaming === conv.id" class="rename-form"><input v-model="name" class="text-input" aria-label="任务名称" maxlength="120" @keydown.enter="rename(conv)" @keydown.esc="renaming = null" /><button class="icon-button" aria-label="保存名称" @click="rename(conv)"><AppIcon name="check" :size="14" /></button></div>
        <template v-else><button class="conversation-select" @click="store.selectConversation(conv.id)"><AppIcon name="chat" :size="15" /><span>{{ conv.title || '新任务' }}</span></button><div class="conversation-actions"><button class="icon-button" aria-label="重命名任务" title="重命名" @click="renaming = conv.id; name = conv.title"><AppIcon name="edit" :size="13" /></button><button class="icon-button" aria-label="删除任务" title="删除" @click="pendingDelete = conv.id"><AppIcon name="trash" :size="13" /></button></div></template>
        <div v-if="pendingDelete === conv.id" class="inline-confirm"><span>删除这项任务？</span><button class="text-button danger" @click="remove(conv.id)">删除</button><button class="text-button" @click="pendingDelete = null">取消</button></div>
      </div>
      <p v-if="localError" class="notice error">{{ localError }}</p>
    </div>
    <footer class="sidebar-footer"><div class="workspace-avatar">D</div><div><strong>个人工作空间</strong><button class="service-status" @click="checkHealth" :title="healthDetail"><span class="status-dot" :class="healthState" />{{ healthText }}</button></div></footer>
  </aside>
</template>
<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useChatStore } from '../stores/chat.js'
import api, { errorText } from '../api/index.js'
import AppIcon from './AppIcon.vue'
const store = useChatStore()
const query = ref(''), renaming = ref(null), name = ref(''), pendingDelete = ref(null), localError = ref('')
const healthState = ref('checking'), healthText = ref('正在连接服务'), healthDetail = ref('')
const filtered = computed(() => store.conversations.filter(c => (c.title || '').toLowerCase().includes(query.value.toLowerCase())))
const navigation = [{ id: 'workspace', label: '工作台', icon: 'chat' }, { id: 'knowledge', label: '知识库', icon: 'library' }, { id: 'artifacts', label: '成果', icon: 'file' }]
let timer
function navigate(id) { store.page = id; if (window.innerWidth <= 900) store.sidebarOpen = false }
async function checkHealth() {
  try {
    const result = await api.healthCheck()
    const ok = ['mysql', 'chroma'].every(key => result[key] === '正常')
    healthState.value = ok ? 'online' : 'degraded'; healthText.value = ok ? '资料服务已连接' : '部分服务未就绪'
    healthDetail.value = Object.entries(result).map(([k, v]) => k + '：' + (v === '正常' ? v : '未就绪')).join('\n')
  } catch { healthState.value = 'offline'; healthText.value = '服务未连接'; healthDetail.value = '点击重新检查连接' }
}
async function rename(conv) {
  if (!name.value.trim()) return
  try { await api.updateConversationTitle(conv.id, name.value.trim()); renaming.value = null; await store.loadConversations() }
  catch (err) { localError.value = errorText(err) }
}
async function remove(id) { await store.deleteConversation(id); pendingDelete.value = null }
onMounted(() => { checkHealth(); timer = setInterval(checkHealth, 30000) })
onUnmounted(() => clearInterval(timer))
</script>
