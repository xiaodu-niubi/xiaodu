<template>
  <div class="app-layout">
    <button v-if="store.sidebarOpen" class="sidebar-backdrop" aria-label="收起导航" @click="store.sidebarOpen = false" />
    <ConversationList v-if="store.sidebarOpen" />
    <main class="main-area">
      <header class="workspace-header">
        <div class="header-location"><button class="icon-button" :aria-label="store.sidebarOpen ? '收起导航' : '展开导航'" @click="store.sidebarOpen = !store.sidebarOpen"><AppIcon name="menu" :size="19" /></button><span class="workspace-name">个人工作空间</span><span class="breadcrumb-divider">/</span><strong>{{ pageTitles[store.page] }}</strong></div>
        <div class="header-actions"><span v-if="store.isLoading" class="running-indicator"><span class="spinner" />任务进行中</span><button class="icon-button" :aria-label="dark ? '切换浅色主题' : '切换深色主题'" @click="toggleTheme"><AppIcon :name="dark ? 'sun' : 'moon'" :size="18" /></button><button v-if="store.page === 'workspace'" class="button small" :class="{ selected: store.panelOpen }" @click="store.panelOpen = !store.panelOpen"><AppIcon name="panel" :size="16" /><span class="desktop-label">任务详情</span></button></div>
      </header>
      <div v-if="store.page === 'workspace'" class="workspace-body"><ChatView /><EvidencePanel v-if="store.panelOpen" /></div>
      <KnowledgeView v-else-if="store.page === 'knowledge'" />
      <ArtifactsView v-else />
    </main>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { useChatStore } from './stores/chat.js'
import ConversationList from './components/ConversationList.vue'
import ChatView from './views/ChatView.vue'
import KnowledgeView from './views/KnowledgeView.vue'
import ArtifactsView from './views/ArtifactsView.vue'
import EvidencePanel from './components/EvidencePanel.vue'
import AppIcon from './components/AppIcon.vue'
const store = useChatStore()
const pageTitles = { workspace: '工作台', knowledge: '知识库', artifacts: '成果' }
const dark = ref(false)
try { dark.value = localStorage.getItem('deepseek-theme') === 'dark' } catch {}
document.documentElement.classList.toggle('theme-dark', dark.value)
function toggleTheme() {
  dark.value = !dark.value; document.documentElement.classList.toggle('theme-dark', dark.value)
  try { localStorage.setItem('deepseek-theme', dark.value ? 'dark' : 'light') } catch {}
}
onMounted(() => { store.loadConversations(); store.loadDocuments() })
</script>
