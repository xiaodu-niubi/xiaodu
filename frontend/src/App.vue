<template>
  <div class="app-layout">
    <ConversationList
      v-if="chatStore.sidebarOpen"
      @toggle="chatStore.toggleSidebar"
    />
    <div class="main-area">
      <ChatView />
    </div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'
import { useChatStore } from './stores/chat.js'
import ConversationList from './components/ConversationList.vue'
import ChatView from './views/ChatView.vue'

const chatStore = useChatStore()

onMounted(() => {
  chatStore.loadConversations()
  chatStore.startHealthCheck()
})
onUnmounted(() => {
  chatStore.stopHealthCheck()
})
</script>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  width: 100%;
}

.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: var(--bg-primary);
}
</style>
