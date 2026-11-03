<template>
  <dialog ref="dialog" class="document-dialog" @cancel="$emit('close')" @click="backdrop">
    <header class="dialog-header"><div><span class="eyebrow">资料原文</span><h3>{{ document?.filename || title || '正在读取' }}</h3></div><button class="icon-button" aria-label="关闭资料原文" @click="$emit('close')"><AppIcon name="close" /></button></header>
    <div class="dialog-body">
      <div v-if="loading" class="empty-state"><span class="spinner" />正在读取资料…</div>
      <div v-else-if="error" class="notice error">{{ error }}</div>
      <template v-else><p v-if="document.truncated" class="notice">资料较长，当前显示前 20 万字符。</p><pre class="source-original">{{ document.content }}</pre></template>
    </div>
  </dialog>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import api, { errorText } from '../api/index.js'
import AppIcon from './AppIcon.vue'
const props = defineProps({ id: String, title: String })
const emit = defineEmits(['close'])
const dialog = ref(null), document = ref(null), loading = ref(true), error = ref('')
const backdrop = event => { if (event.target === dialog.value) emit('close') }
onMounted(async () => {
  dialog.value.showModal()
  try { document.value = await api.readKnowledge(props.id) } catch (err) { error.value = errorText(err) }
  finally { loading.value = false }
})
</script>
