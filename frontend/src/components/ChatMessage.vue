<template>
  <article class="message" :class="message.role">
    <template v-if="message.role === 'user'"><div class="user-message">{{ message.content }}</div></template>
    <template v-else>
      <div class="assistant-label"><img src="@/image/deepseek.webp" alt="" /><strong>DeepSeek</strong><span v-if="message.metadata?.status === 'running'" class="badge">处理中</span></div>
      <details v-if="message.tool_calls?.length" class="tool-timeline">
        <summary><AppIcon name="check" :size="15" />使用了 {{ message.tool_calls.length }} 个工具<AppIcon name="chevron" :size="13" /></summary>
        <div v-for="tool in message.tool_calls" :key="tool.id" class="tool-entry"><div><span>{{ toolLabels[tool.name] || tool.name }}</span><span class="badge" :class="tool.status">{{ statuses[tool.status] || '已完成' }}</span></div><pre v-if="tool.result">{{ tool.result }}</pre></div>
      </details>
      <div v-if="!message.content && message.metadata?.status === 'running'" class="answer-placeholder"><span class="spinner" /><span>正在准备回答…</span></div>
      <div ref="body" class="prose message-prose" v-html="rendered" @click="citationClick" />
      <div v-if="message.metadata?.status === 'stopped' || message.metadata?.status === 'interrupted'" class="message-status">任务已停止，已保留收到的内容。</div>
      <div v-if="message.metadata?.status === 'error'" class="message-status danger">{{ message.metadata.error || '任务失败，请重试。' }}</div>
      <div v-if="message.content || message.metadata?.status !== 'running'" class="message-actions">
        <button v-if="message.content" class="icon-button" :aria-label="copied ? '已复制' : '复制回答'" :title="copied ? '已复制' : '复制回答'" @click="copy"><AppIcon :name="copied ? 'check' : 'copy'" :size="16" /></button>
        <button v-if="message.content" class="icon-button" aria-label="导出回答" title="导出 Markdown" @click="downloadMarkdown(message.content, store.currentConversation?.title, message.metadata?.sources)"><AppIcon name="download" :size="16" /></button>
        <button class="icon-button" :disabled="store.isLoading" aria-label="重新执行此任务" title="重新执行" @click="store.retryMessage(message)"><AppIcon name="refresh" :size="16" /></button>
        <span class="actions-divider" />
        <button v-if="message.metadata?.sources?.length" class="text-button" @click="store.openPanel(message, 'sources')"><AppIcon name="library" :size="15" />{{ message.metadata.sources.length }} 处来源</button>
        <button v-if="message.content" class="text-button" :disabled="store.isLoading" @click="store.openPanel(message, 'artifact')"><AppIcon name="edit" :size="15" />编辑成果</button>
        <span v-if="copyError" class="danger small-text" role="status">{{ copyError }}</span>
      </div>
    </template>
  </article>
</template>
<script setup>
import { computed, ref, watch, nextTick, onMounted } from 'vue'
import { useChatStore } from '../stores/chat.js'
import { renderMarkdown, highlightCode, downloadMarkdown } from '../utils/markdown.js'
import AppIcon from './AppIcon.vue'
const props = defineProps({ message: { type: Object, required: true } })
const store = useChatStore(), body = ref(null), copied = ref(false), copyError = ref('')
const rendered = computed(() => renderMarkdown(props.message.content || '', props.message.metadata?.sources || []))
const toolLabels = { calculator: '计算', unit_converter: '单位换算', search_knowledge: '检索资料', web_search: '搜索互联网', web_fetch: '读取网页', get_current_time: '查询时间', count_tokens: '统计文本' }
const statuses = { completed: '已完成', running: '进行中', error: '失败' }
async function copy() {
  try { await navigator.clipboard.writeText(props.message.content); copied.value = true; copyError.value = ''; setTimeout(() => copied.value = false, 2000) }
  catch { copyError.value = '无法自动复制，请选择文本复制。' }
}
async function citationClick(event) {
  const button = event.target.closest('[data-source-number]')
  if (!button) return
  store.openPanel(props.message, 'sources')
  await nextTick()
  document.getElementById('source-' + button.dataset.sourceNumber)?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
}
watch(() => props.message.metadata?.status, async () => { await nextTick(); if (props.message.metadata?.status !== 'running') highlightCode(body.value) })
onMounted(() => { if (props.message.metadata?.status !== 'running') highlightCode(body.value) })
</script>
