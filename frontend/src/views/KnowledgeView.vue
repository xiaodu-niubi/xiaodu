<template>
  <section class="page-content library-page">
    <div class="page-heading"><div><span class="eyebrow">LIBRARY</span><h1>你的知识库</h1><p>把资料放在这里，让每次回答有据可查。</p></div><button class="button primary" :disabled="busy" @click="fileInput.click()"><AppIcon name="upload" :size="17" />导入资料</button></div>
    <input ref="fileInput" type="file" accept=".txt,.md,.pdf,.docx" multiple hidden @change="upload" />
    <div class="upload-zone" :class="{ dragging }" @dragover.prevent="dragging = true" @dragleave="dragging = false" @drop.prevent="drop">
      <div class="upload-symbol"><AppIcon name="upload" :size="24" /></div>
      <div><strong>{{ busy ? progress : '拖入资料，或点击导入' }}</strong><p>支持 TXT、Markdown、PDF、Word · 单个文件最多 20 MB</p></div>
      <button class="button" :disabled="busy" @click="fileInput.click()">选择文件</button>
    </div>
    <div v-if="notice" class="notice" :class="{ error: failed }" role="status">{{ notice }}</div>
    <div v-if="store.libraryError" class="notice error">{{ store.libraryError }} <button class="text-button" @click="store.loadDocuments()">重试</button></div>
    <div class="library-toolbar"><label class="search-field"><AppIcon name="search" :size="17" /><input v-model="search" placeholder="搜索资料名称" aria-label="搜索资料" /></label><span class="muted">{{ store.documents.length }} 份资料</span><button class="button small" :disabled="busy" @click="reload"><AppIcon name="refresh" :size="15" />同步本地资料</button></div>
    <div v-if="!filtered.length" class="empty-state bordered"><AppIcon name="library" :size="36" /><strong>{{ search ? '没有找到匹配的资料' : '从第一份资料开始' }}</strong><p>{{ search ? '换个关键词试试。' : '导入文档，或同步项目 knowledge_base 中已有的资料。' }}</p></div>
    <div v-else class="document-list">
      <div class="document-row document-row-heading"><span>资料名称</span><span>索引状态</span><span>片段</span><span>操作</span></div>
      <div v-for="doc in filtered" :key="doc.id" class="document-row">
        <button class="document-name" @click="preview = doc"><span class="file-type">{{ doc.file_type?.toUpperCase() || 'TXT' }}</span><span><strong>{{ doc.filename }}</strong><small>{{ formatDate(doc.created_at) }}</small></span></button>
        <span class="badge" :class="doc.status">{{ labels[doc.status] || doc.status }}</span>
        <span class="chunk-count">{{ doc.chunk_count }}</span>
        <div class="row-actions"><button class="icon-button" aria-label="查看资料原文" title="查看原文" @click="preview = doc"><AppIcon name="file" :size="17" /></button><button class="icon-button" :disabled="busy" aria-label="重新索引资料" title="重新索引" @click="reindex(doc)"><AppIcon name="refresh" :size="17" /></button></div>
      </div>
    </div>
    <p class="library-note">文字版 PDF 可直接检索；扫描版 PDF 请先识别文字。同名资料会保留，通过重新索引更新检索内容。</p>
  </section>
  <DocumentPreview v-if="preview" :id="preview.id" :title="preview.filename" @close="preview = null" />
</template>
<script setup>
import { ref, computed, onMounted } from 'vue'
import { useChatStore } from '../stores/chat.js'
import api, { errorText } from '../api/index.js'
import AppIcon from '../components/AppIcon.vue'
import DocumentPreview from '../components/DocumentPreview.vue'
const store = useChatStore()
const fileInput = ref(null), search = ref(''), busy = ref(false), dragging = ref(false)
const notice = ref(''), failed = ref(false), progress = ref(''), preview = ref(null)
const labels = { ready: '可检索', processing: '索引中', error: '索引失败' }
const filtered = computed(() => store.documents.filter(d => d.filename.toLowerCase().includes(search.value.toLowerCase())))
const formatDate = date => date ? new Date(date).toLocaleDateString('zh-CN') : ''
onMounted(() => store.loadDocuments())
async function importFiles(files) {
  if (busy.value || !files.length) return
  busy.value = true; failed.value = false; notice.value = ''
  let completed = 0
  const failures = []
  for (const [index, file] of Array.from(files).entries()) {
    progress.value = '正在处理 ' + (index + 1) + '/' + files.length + '：' + file.name
    try {
      if (file.size > 20 * 1024 * 1024) throw new Error('文件超过 20 MB')
      if (!/\.(txt|md|pdf|docx)$/i.test(file.name)) throw new Error('不支持此文件格式')
      await api.uploadKnowledge(file); completed++
    } catch (err) { failures.push(file.name + '：' + errorText(err)) }
    await store.loadDocuments()
  }
  notice.value = '成功导入 ' + completed + ' 份资料。' + failures.join('；')
  failed.value = !!failures.length; busy.value = false
}
async function upload(event) { await importFiles(event.target.files); event.target.value = '' }
function drop(event) { dragging.value = false; importFiles(event.dataTransfer.files) }
async function reload() {
  busy.value = true; progress.value = '正在同步项目资料'; notice.value = ''; failed.value = false
  try {
    const result = await api.reloadKnowledge()
    const errors = result.documents.filter(d => d.status === 'error')
    failed.value = errors.length > 0
    notice.value = '已同步 ' + (result.loaded - errors.length) + ' 份资料。' + (errors.length ? errors.length + ' 份索引失败，请从列表重试。' : '')
  }
  catch (err) { failed.value = true; notice.value = errorText(err) }
  finally { busy.value = false; await store.loadDocuments() }
}
async function reindex(doc) {
  busy.value = true; progress.value = '正在索引 ' + doc.filename; failed.value = false
  try { await api.reindexKnowledge(doc.id); notice.value = doc.filename + ' 已重新索引。' }
  catch (err) { failed.value = true; notice.value = errorText(err) }
  finally { busy.value = false; await store.loadDocuments() }
}
</script>
