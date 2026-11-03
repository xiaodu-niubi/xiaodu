<template>
  <div class="composer-container">
    <div class="task-status" v-if="store.isLoading" role="status"><span class="spinner" /><span>{{ store.statusText }}</span><span v-if="store.sources.length" class="muted">· 已找到 {{ store.sources.length }} 处资料</span></div>
    <form class="composer" @submit.prevent="send">
      <textarea ref="input" v-model="store.draft" :placeholder="placeholders[store.mode]" class="composer-textarea" rows="2" aria-label="描述你的任务" :disabled="store.loadingConversation" @keydown="keydown" @input="resize" />
      <div class="composer-toolbar">
        <div class="composer-controls">
          <label class="mode-select"><AppIcon :name="modeIcons[store.mode]" :size="16" /><select v-model="store.mode" aria-label="任务类型" :disabled="store.isLoading"><option value="knowledge">查阅资料</option><option value="compare">对比文档</option><option value="report">制作报告</option><option value="chat">自由对话</option></select><AppIcon name="chevron" :size="12" /></label>
          <details ref="picker" class="document-picker">
            <summary><AppIcon name="library" :size="16" /><span>{{ store.selectedDocumentIds.length ? store.selectedDocumentIds.length + ' 份资料' : '全部资料' }}</span><AppIcon name="chevron" :size="12" /></summary>
            <div class="document-popover"><strong>选择检索范围</strong><p>未选时检索全部资料，最多选择 20 份。</p><div v-if="!readyDocs.length" class="picker-empty">暂无就绪资料<button type="button" class="text-button" @click="store.page = 'knowledge'">导入资料</button></div><label v-for="doc in readyDocs" :key="doc.id"><input v-model="store.selectedDocumentIds" type="checkbox" :value="doc.id" :disabled="store.isLoading || (!store.selectedDocumentIds.includes(doc.id) && store.selectedDocumentIds.length >= 20)" /><span>{{ doc.filename }}</span></label><button type="button" class="text-button" :disabled="store.isLoading" @click="store.selectedDocumentIds = []">使用全部资料</button><button type="button" class="button small" @click="picker.open = false">完成</button></div>
          </details>
          <button type="button" class="composer-toggle" :class="{ active: store.useWeb }" :aria-pressed="store.useWeb" :disabled="store.isLoading" title="允许搜索互联网" @click="store.useWeb = !store.useWeb"><AppIcon name="globe" :size="16" /><span>联网</span></button>
        </div>
        <button v-if="store.isLoading" type="button" class="send-button stop" aria-label="停止生成" title="停止生成" @click="store.stopGeneration()"><AppIcon name="stop" :size="20" /></button>
        <button v-else type="submit" class="send-button" :disabled="!store.draft.trim() || store.loadingConversation" aria-label="发送任务" title="发送任务"><AppIcon name="arrow" :size="20" /></button>
      </div>
    </form>
    <div class="composer-footnote"><span>{{ store.mode === 'chat' ? '自由对话模式 · 可随时切换到资料检索' : '引用可在任务详情中核对 · 请确认关键结论' }}</span><span class="keyboard-hint">Enter 发送 · Shift + Enter 换行</span></div>
  </div>
</template>
<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { useChatStore } from '../stores/chat.js'
import AppIcon from './AppIcon.vue'
const store = useChatStore(), input = ref(null), picker = ref(null)
const readyDocs = computed(() => store.documents.filter(d => d.status === 'ready'))
const placeholders = { knowledge: '描述你的问题，我会从资料中寻找答案…', compare: '选择两份或更多资料，描述你想比较的维度…', report: '描述报告主题、用途与需要包含的内容…', chat: '描述你的问题或想法…' }
const modeIcons = { knowledge: 'search', compare: 'compare', report: 'file', chat: 'chat' }
function send() {
  if (store.isLoading) return
  store.sendMessage(store.draft)
  if (store.isLoading) { store.draft = ''; resize() }
}
function keydown(event) {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing && event.keyCode !== 229) {
    event.preventDefault(); send()
  }
}
async function resize() {
  await nextTick()
  if (!input.value) return
  input.value.style.height = 'auto'; input.value.style.height = Math.min(input.value.scrollHeight, 200) + 'px'
}
watch(() => store.draft, async () => { await resize(); if (store.draft) input.value?.focus() })
</script>
