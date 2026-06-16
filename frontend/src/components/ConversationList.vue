<template>
  <aside class="sidebar">
    <div class="sidebar-header">
      <div class="sidebar-brand">
        <span class="brand-icon">
          <img src="@/image/deepseek.webp" alt="DeepSeek" class="brand-icon-img" />
        </span>
        <span class="brand-name">DeepSeek</span>
      </div>
      <button class="btn-new" @click="chatStore.newConversation()">
        <span>＋</span> 新对话
      </button>
    </div>

    <div class="conv-list">
      <template v-if="groupedConversations.length > 0">
        <template v-for="group in groupedConversations" :key="group.label">
          <div class="group-header">{{ group.label }}</div>
          <div
            v-for="conv in group.conversations"
            :key="conv.id"
            class="conv-item"
            :class="{ active: conv.id === chatStore.currentConversationId }"
            @click="chatStore.selectConversation(conv.id)"
          >
            <div class="conv-icon">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
              </svg>
            </div>
            <div class="conv-body">
              <div class="conv-title">{{ conv.title || '新对话' }}</div>
              <div class="conv-meta">{{ formatTime(conv.updated_at) }}</div>
            </div>
            <div class="conv-menu" @click.stop>
              <button class="btn-menu" @click="toggleMenu(conv.id)" title="更多">⋯</button>
              <div v-if="openMenuId === conv.id" class="menu-dropdown">
                <button class="menu-item" @click="handleRename(conv)">✏️ 重命名</button>
                <button class="menu-item danger" @click="handleDelete(conv.id)">🗑️ 删除</button>
              </div>
            </div>
          </div>
        </template>
      </template>

      <div v-if="chatStore.conversations.length === 0" class="empty-list">
        <div class="empty-icon">💭</div>
        <p>还没有对话</p>
        <p class="empty-sub">点击上方按钮开始</p>
      </div>
    </div>

    <div class="sidebar-footer">
      <span class="status-dot" :class="statusClass" />
      <span class="status-text">{{ statusText }}</span>
    </div>
  </aside>
</template>

<script setup>
import { useChatStore } from '../stores/chat.js'
import { ref, computed, onMounted, onUnmounted } from 'vue'
import api from '../api/index.js'

defineEmits(['toggle'])

const chatStore = useChatStore()
const statusClass = ref('checking')
const statusText = ref('检测中...')
const openMenuId = ref(null)

function toggleMenu(id) {
  openMenuId.value = openMenuId.value === id ? null : id
}

function handleRename(conv) {
  openMenuId.value = null
  const newTitle = prompt('请输入新标题', conv.title || '新对话')
  if (newTitle && newTitle.trim() && newTitle.trim() !== conv.title) {
    api.updateConversationTitle(conv.id, newTitle.trim()).then(() => {
      chatStore.loadConversations()
    })
  }
}

const groupedConversations = computed(() => {
  const now = new Date()
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const day7ago = new Date(todayStart.getTime() - 6 * 86400000)
  const day30ago = new Date(todayStart.getTime() - 29 * 86400000)

  const groups = [
    { label: '今天', conversations: [], test: (d) => d >= todayStart },
    { label: '7天内', conversations: [], test: (d) => d >= day7ago },
    { label: '一个月内', conversations: [], test: (d) => d >= day30ago },
    { label: '一个月以上', conversations: [], test: () => true },
  ]

  for (const conv of chatStore.conversations) {
    const d = new Date(conv.updated_at || conv.created_at)
    for (const g of groups) {
      if (g.test(d)) {
        g.conversations.push(conv)
        break
      }
    }
  }

  return groups.filter(g => g.conversations.length > 0)
})

async function checkHealth() {
  try {
    const health = await api.healthCheck()
    const allOk = Object.values(health).every(v => v === '正常')
    statusClass.value = allOk ? 'online' : 'degraded'
    statusText.value = allOk ? '全部服务正常' : '部分服务异常'
  } catch {
    statusClass.value = 'offline'
    statusText.value = '服务未连接'
  }
}

const healthInterval = setInterval(checkHealth, 30000)
onMounted(() => {
  chatStore.loadConversations()
  checkHealth()
  document.addEventListener('click', closeMenu)
})
onUnmounted(() => {
  clearInterval(healthInterval)
  document.removeEventListener('click', closeMenu)
})

function handleDelete(id) {
  openMenuId.value = null
  if (confirm('确定删除这个对话吗？')) {
    chatStore.deleteConversation(id)
  }
}

function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  const now = new Date()
  const diff = now - d
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`
  return d.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}
</script>

<style scoped>
.sidebar {
  width: 280px;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  height: 100vh;
}

.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 10px;
}
.brand-icon {
  width: 32px; height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}
.brand-icon-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: inherit;
}
.brand-name {
  font-size: 1rem;
  font-weight: 700;
  letter-spacing: -0.01em;
}

.btn-new {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 8px 0;
  background: var(--surface);
  color: var(--text-primary);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: 0.85rem;
  cursor: pointer;
  font-weight: 500;
  transition: all var(--transition);
}
.btn-new:hover {
  border-color: var(--accent);
  background: rgba(99,102,241,0.06);
}
.btn-new span { font-size: 1.1rem; }

.conv-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.group-header {
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--text-dim);
  padding: 10px 12px 6px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.conv-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition);
  position: relative;
}
.conv-item:hover { background: var(--surface); }
.conv-item.active {
  background: var(--surface);
  border: 1px solid rgba(99,102,241,0.3);
}

.conv-icon {
  flex-shrink: 0;
  opacity: 0.5;
  color: var(--text-dim);
  display: flex;
  align-items: center;
}
.conv-item.active .conv-icon { opacity: 0.9; color: var(--accent-light); }
.conv-item.active .conv-icon { opacity: 1; }

.conv-body { flex: 1; min-width: 0; }

.conv-title {
  font-size: 0.83rem;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 2px;
}
.conv-meta { font-size: 0.7rem; color: var(--text-dim); }

.conv-menu {
  position: relative;
  flex-shrink: 0;
}

.btn-menu {
  width: 24px; height: 24px;
  background: none;
  border: none;
  border-radius: 4px;
  color: var(--text-dim);
  cursor: pointer;
  font-size: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: all var(--transition);
}
.conv-item:hover .btn-menu { opacity: 1; }
.btn-menu:hover { color: var(--text-primary); background: rgba(255,255,255,0.08); }

.menu-dropdown {
  position: absolute;
  right: 0;
  top: 100%;
  margin-top: 4px;
  min-width: 120px;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  box-shadow: 0 8px 24px rgba(0,0,0,0.4);
  z-index: 50;
  padding: 4px;
  animation: fadeIn 0.15s ease;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-4px); }
  to { opacity: 1; transform: translateY(0); }
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  padding: 8px 10px;
  background: none;
  border: none;
  border-radius: 4px;
  color: var(--text-primary);
  font-size: 0.82rem;
  cursor: pointer;
  transition: background var(--transition);
}
.menu-item:hover { background: var(--surface); }
.menu-item.danger:hover { background: rgba(248,113,113,0.1); color: var(--error); }

.empty-list {
  text-align: center;
  padding: 48px 20px;
  color: var(--text-dim);
}
.empty-icon { font-size: 2.5rem; margin-bottom: 12px; opacity: 0.5; }
.empty-list p { font-size: 0.85rem; }
.empty-sub { font-size: 0.75rem; margin-top: 4px; opacity: 0.7; }

.sidebar-footer {
  padding: 12px 16px;
  border-top: 1px solid var(--border);
  display: flex;
  align-items: center;
  gap: 8px;
}
.status-dot {
  width: 7px; height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}
.status-dot.online { background: var(--success); box-shadow: 0 0 6px rgba(52,211,153,0.4); }
.status-dot.degraded { background: var(--warning); box-shadow: 0 0 6px rgba(251,191,36,0.4); }
.status-dot.offline { background: var(--error); }
.status-dot.checking { background: var(--text-dim); animation: pulse 1s infinite; }

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.status-text { font-size: 0.72rem; color: var(--text-dim); }
</style>
