<template>
  <aside class="evidence-panel" :style="{ width: store.panelWidth + 'px' }" aria-label="来源与成果">
    <div class="panel-resizer" role="separator" tabindex="0" aria-label="调整任务详情宽度" aria-orientation="vertical" :aria-valuenow="store.panelWidth" :aria-valuemin="320" :aria-valuemax="640" @pointerdown="resizeStart" @keydown.left.prevent="store.panelWidth = Math.min(640, store.panelWidth + 20)" @keydown.right.prevent="store.panelWidth = Math.max(320, store.panelWidth - 20)" />
    <header class="panel-header"><strong>任务详情</strong><button class="icon-button" aria-label="关闭任务详情" @click="store.panelOpen = false"><AppIcon name="close" :size="18" /></button></header>
    <div class="panel-tabs" role="tablist">
      <button role="tab" :aria-selected="store.panelTab === 'sources'" :class="{ active: store.panelTab === 'sources' }" @click="store.panelTab = 'sources'">引用资料 <span>{{ store.currentSources.length }}</span></button>
      <button role="tab" :aria-selected="store.panelTab === 'artifact'" :class="{ active: store.panelTab === 'artifact' }" @click="store.panelTab = 'artifact'">成果</button>
    </div>
    <div v-if="store.panelTab === 'sources'" class="panel-content">
      <p class="panel-description">检索片段与原文供你核对。回答中的编号对应下方资料。</p>
      <div v-if="!store.currentSources.length" class="empty-state"><AppIcon name="library" :size="32" /><strong>暂无引用资料</strong><p>使用知识库提问后，检索到的原文会出现在这里。</p></div>
      <details v-for="source in store.currentSources" :key="source.id" :id="'source-' + source.number" class="source-card" open>
        <summary><span class="citation-number">{{ source.number }}</span><div><strong>{{ source.filename }}</strong><span>片段 {{ source.chunk_index + 1 }}</span></div><AppIcon name="chevron" :size="14" /></summary>
        <p class="source-snippet">{{ source.snippet }}</p>
        <button v-if="source.document_id" class="text-button" @click="preview = source">查看资料原文 <AppIcon name="right" :size="14" /></button>
      </details>
    </div>
    <div v-else class="panel-content artifact-content">
      <div v-if="!message?.content" class="empty-state"><AppIcon name="file" :size="32" /><strong>还没有成果</strong><p>生成回答后，可在这里编辑、保存和导出。</p></div>
      <template v-else>
        <div class="artifact-toolbar"><span class="badge">{{ dirty ? '尚未保存' : 'Markdown' }}</span><button class="text-button" :disabled="store.isLoading" @click="editing = !editing"><AppIcon :name="editing ? 'file' : 'edit'" :size="14" />{{ editing ? '预览' : '编辑' }}</button></div>
        <label class="field-label" for="artifact-title">成果名称</label>
        <input id="artifact-title" v-model="title" class="text-input" maxlength="120" :disabled="store.isLoading" />
        <textarea v-if="editing" v-model="content" class="artifact-editor" aria-label="编辑成果 Markdown" spellcheck="false" />
        <div v-else ref="previewElement" class="prose artifact-preview" v-html="renderMarkdown(content)" />
        <div v-if="feedback" class="notice" :class="{ error: failed }" role="status">{{ feedback }}</div>
        <p class="panel-description">保存后可在“成果”中再次打开；原始回答会保留。</p>
        <div class="artifact-footer"><button class="button primary" :disabled="saving || store.isLoading || !title.trim() || !content.trim() || !Number.isInteger(message.id)" @click="save"><AppIcon name="check" :size="16" />{{ saving ? '正在保存' : '保存成果' }}</button><button class="button" :disabled="store.isLoading" @click="downloadMarkdown(content, title, store.currentSources)"><AppIcon name="download" :size="16" />导出</button></div>
      </template>
    </div>
  </aside>
  <DocumentPreview v-if="preview" :key="preview.document_id" :id="preview.document_id" :title="preview.filename" @close="preview = null" />
</template>
<script setup>
import { ref, computed, watch, nextTick, onUnmounted } from 'vue'
import { useChatStore } from '../stores/chat.js'
import api, { errorText } from '../api/index.js'
import { renderMarkdown, downloadMarkdown, highlightCode } from '../utils/markdown.js'
import AppIcon from './AppIcon.vue'
import DocumentPreview from './DocumentPreview.vue'
const store = useChatStore(), message = computed(() => store.selectedMessage)
const content = ref(''), title = ref(''), editing = ref(false), saving = ref(false), feedback = ref(''), failed = ref(false)
const preview = ref(null), previewElement = ref(null)
const draftKey = computed(() => store.currentConversationId + ':' + message.value?.id)
const dirty = computed(() => !!store.artifactDrafts[draftKey.value])
let stopResize = null
function resizeStart(event) {
  if (window.innerWidth <= 900) return
  stopResize?.()
  const start = event.clientX, width = store.panelWidth
  const move = event => { store.panelWidth = Math.max(320, Math.min(640, width + start - event.clientX)) }
  const stop = () => {
    window.removeEventListener('pointermove', move); window.removeEventListener('pointerup', stop)
    document.body.style.userSelect = ''; stopResize = null
  }
  stopResize = stop; document.body.style.userSelect = 'none'
  window.addEventListener('pointermove', move); window.addEventListener('pointerup', stop)
}
onUnmounted(() => stopResize?.())
watch(() => [message.value?.id, store.selectionVersion], () => {
  const artifact = message.value?.metadata?.artifact
  const draft = store.artifactDrafts[draftKey.value]
  content.value = draft?.content ?? artifact?.content ?? message.value?.content ?? ''
  title.value = draft?.title || artifact?.title || store.currentConversation?.title || '研究成果'
  editing.value = !!draft; feedback.value = ''
}, { immediate: true })
watch(() => message.value?.content, value => { if (!editing.value && !dirty.value && !message.value?.metadata?.artifact) content.value = value || '' })
watch([content, title], () => {
  if (editing.value && message.value && !store.isLoading) store.artifactDrafts[draftKey.value] = { content: content.value, title: title.value }
})
watch(content, async () => { await nextTick(); if (!editing.value) highlightCode(previewElement.value) })
async function save() {
  saving.value = true; feedback.value = ''; failed.value = false
  const target = message.value
  const key = draftKey.value
  try {
    const result = await api.saveArtifact(store.currentConversationId, target.id, title.value.trim(), content.value)
    target.metadata = result.metadata; delete store.artifactDrafts[key]; feedback.value = '成果已保存'
  } catch (err) { failed.value = true; feedback.value = errorText(err) }
  finally { saving.value = false }
}
</script>
