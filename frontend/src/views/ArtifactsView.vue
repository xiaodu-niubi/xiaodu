<template>
  <section class="page-content">
    <div class="page-heading"><div><span class="eyebrow">OUTPUTS</span><h1>你的成果</h1><p>保存有价值的回答，把研究沉淀为可以继续使用的内容。</p></div><button class="button" @click="load"><AppIcon name="refresh" :size="16" />刷新</button></div>
    <div v-if="error" class="notice error">{{ error }}</div>
    <div v-if="loading" class="empty-state"><span class="spinner" />正在加载成果…</div>
    <div v-else-if="!artifacts.length" class="empty-state bordered"><AppIcon name="file" :size="36" /><strong>还没有保存的成果</strong><p>在回答下方点击“编辑成果”，保存后会出现在这里。</p><button class="button primary" @click="store.newConversation('report')">开始制作报告 <AppIcon name="right" :size="16" /></button></div>
    <div v-else class="artifact-grid">
      <article v-for="item in artifacts" :key="item.id" class="saved-artifact">
        <div class="saved-artifact-top"><AppIcon name="file" :size="23" /><span class="badge">Markdown</span></div>
        <h3>{{ item.metadata.artifact.title }}</h3>
        <p>{{ item.metadata.artifact.content.replace(/[#*\x60]/g, '').slice(0, 140) }}</p>
        <span class="muted small-text">来自 {{ item.conversation_title }}</span>
        <div class="saved-artifact-actions"><button class="text-button" @click="open(item)">继续编辑 <AppIcon name="right" :size="14" /></button><button class="icon-button" aria-label="导出成果" title="导出 Markdown" @click="downloadMarkdown(item.metadata.artifact.content, item.metadata.artifact.title, item.metadata.sources)"><AppIcon name="download" :size="18" /></button></div>
      </article>
    </div>
  </section>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { useChatStore } from '../stores/chat.js'
import api, { errorText } from '../api/index.js'
import { downloadMarkdown } from '../utils/markdown.js'
import AppIcon from '../components/AppIcon.vue'
const store = useChatStore(), artifacts = ref([]), loading = ref(true), error = ref('')
async function load() {
  loading.value = true; error.value = ''
  try { artifacts.value = await api.listArtifacts() } catch (err) { error.value = errorText(err) }
  finally { loading.value = false }
}
async function open(item) {
  await store.selectConversation(item.conversation_id)
  const message = store.messages.find(m => m.id === item.id)
  if (message) store.openPanel(message, 'artifact')
}
onMounted(load)
</script>
