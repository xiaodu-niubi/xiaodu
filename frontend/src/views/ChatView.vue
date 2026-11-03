<template>
  <section class="chat-view">
    <div ref="scroller" class="messages-container" @scroll="trackScroll">
      <div v-if="store.loadingConversation" class="empty-state"><span class="spinner" />正在读取任务…</div>
      <div v-else-if="!store.messages.length" class="welcome">
        <div class="welcome-kicker"><span class="welcome-dot" />KNOWLEDGE STUDIO</div>
        <h1>把资料，变成<br />有依据的答案。</h1>
        <p class="welcome-description">查阅知识、比较方案、整理报告。<br class="mobile-break" />从一个问题开始，让研究更进一步。</p>
        <div class="starter-grid">
          <button v-for="task in tasks" :key="task.mode" class="starter-card" @click="start(task)"><span class="starter-icon"><AppIcon :name="task.icon" :size="22" /></span><strong>{{ task.title }}</strong><p>{{ task.description }}</p><span class="starter-link">开始 <AppIcon name="right" :size="14" /></span></button>
        </div>
        <div class="welcome-library"><AppIcon name="library" :size="17" /><span>{{ readyCount ? readyCount + ' 份资料已就绪，可以开始提问' : '导入你的资料，让回答有据可查' }}</span><button class="text-button" @click="store.page = 'knowledge'">管理资料 <AppIcon name="right" :size="14" /></button></div>
      </div>
      <div v-else class="message-thread">
        <div class="thread-heading"><span class="eyebrow">当前任务</span><h2>{{ store.currentConversation?.title || '新任务' }}</h2></div>
        <ChatMessage v-for="message in store.messages" :key="message.localId || message.id" :message="message" />
      </div>
      <div v-if="store.error" class="notice error chat-error" role="alert"><span>{{ store.error }}</span><button class="icon-button" aria-label="关闭错误提示" @click="store.error = null"><AppIcon name="close" :size="16" /></button></div>
    </div>
    <button v-if="!atBottom && store.messages.length" class="scroll-bottom button small" @click="goBottom(true)"><AppIcon name="arrow" :size="14" class="rotate-down" />查看最新内容</button>
    <ChatInput />
  </section>
</template>
<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { useChatStore } from '../stores/chat.js'
import ChatMessage from '../components/ChatMessage.vue'
import ChatInput from '../components/ChatInput.vue'
import AppIcon from '../components/AppIcon.vue'
const store = useChatStore(), scroller = ref(null), atBottom = ref(true)
const readyCount = computed(() => store.documents.filter(d => d.status === 'ready').length)
const tasks = [
  { mode: 'knowledge', icon: 'search', title: '查阅资料', description: '从知识库找到答案，核对原文依据。', prompt: '根据知识库资料，介绍产品的核心能力，并标明信息来源。' },
  { mode: 'compare', icon: 'compare', title: '对比文档', description: '梳理共同点、差异与需要补充的信息。', prompt: '请对比选定的资料，用表格梳理核心差异、各自优势与信息缺口，并给出建议。' },
  { mode: 'report', icon: 'file', title: '制作报告', description: '把资料整理成可以编辑与保存的成果。', prompt: '根据资料制作一份分析报告，包含摘要、关键发现、证据和行动建议。' },
]
function start(task) { store.mode = task.mode; store.draft = task.prompt }
function trackScroll() { const el = scroller.value; if (el) atBottom.value = el.scrollHeight - el.scrollTop - el.clientHeight < 90 }
async function goBottom(force = false) {
  await nextTick()
  if (scroller.value && (force || atBottom.value)) scroller.value.scrollTop = scroller.value.scrollHeight
}
watch(() => store.messages.at(-1)?.content, () => goBottom())
watch(() => store.messages.length, () => { atBottom.value = true; goBottom(true) })
watch(() => store.currentConversationId, () => { atBottom.value = true })
</script>
