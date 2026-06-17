<template>
  <div class="message" :class="message.role">
    <div class="message-avatar" :class="message.role">
      <img v-if="message.role === 'assistant'" src="@/image/deepseek.webp" alt="AI" class="avatar-img" @error="e => e.target.style.display='none'" />
      <img v-else src="@/image/user.png" alt="用户" class="avatar-img" @error="e => e.target.style.display='none'" />
    </div>
    <div class="message-body">
      <div class="message-role-name">{{ message.role === 'user' ? '你' : 'AI 助手' }}</div>
      <div class="message-bubble" :class="message.role">
        <div class="message-text" v-html="renderedContent" />
        <div v-if="message.tool_calls?.length" class="tool-calls">
          <details v-for="(tc, i) in message.tool_calls" :key="i" class="tool-call">
            <summary class="tool-name">🔧 调用工具：{{ tc.name }}</summary>
            <pre class="tool-args">{{ formatToolCall(tc) }}</pre>
          </details>
        </div>
      </div>
      <div class="message-time">{{ formatTime(message.created_at) }}</div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

marked.setOptions({ breaks: true, gfm: true })

const props = defineProps({
  message: { type: Object, required: true },
})

const renderedContent = computed(() => {
  const content = props.message.content || ''
  try { return DOMPurify.sanitize(marked.parse(content)) } catch { return content }
})

function formatToolCall(tc) {
  if (tc.result) return `返回结果：${tc.result}`
  return JSON.stringify(tc.args || tc, null, 2)
}

function formatTime(ts) {
  if (!ts) return ''
  return new Date(ts).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}
</script>

<style scoped>
.message {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
  animation: msgIn 0.35s ease;
}
.message.user {
  flex-direction: row-reverse;
}
@keyframes msgIn {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}


.message-avatar {
  width: 34px; height: 34px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  overflow: hidden;
}
.message-avatar.user {
  box-shadow: 0 2px 12px rgba(99,102,241,0.3);
}
.avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: inherit;
}

.message-body {
  flex: 1;
  min-width: 0;
  max-width: 85%;
}

.message-role-name {
  font-size: 0.75rem;
  color: var(--text-dim);
  margin-bottom: 4px;
  padding-left: 4px;
}
.message.user .message-role-name {
  text-align: right;
  padding-left: 0;
  padding-right: 4px;
}

.message-bubble {
  padding: 12px 18px;
  border-radius: var(--radius-lg);
  line-height: 1.7;
  font-size: 0.92rem;
  position: relative;
}
.message-bubble.user {
  background: linear-gradient(135deg, #6366f1, #7c3aed);
  color: #fff;
  border-bottom-left-radius: 4px;
}
.message-bubble.assistant {
  background: var(--surface);
  border: 1px solid var(--border);
  border-bottom-right-radius: 4px;
}

.message-text {
  word-break: break-word;
}
.message-text :deep(p) { margin-bottom: 6px; }
.message-text :deep(p:last-child) { margin-bottom: 0; }
.message-text :deep(ul), .message-text :deep(ol) { padding-left: 22px; margin: 4px 0; }
.message-text :deep(code) { font-size: 0.85em; }
.message-text :deep(pre) { margin: 10px 0; }

.message-time {
  font-size: 0.7rem;
  color: var(--text-dim);
  margin-top: 4px;
  padding-left: 4px;
}
.message.user .message-time {
  text-align: right;
  padding-left: 0;
  padding-right: 4px;
}

.tool-calls {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid rgba(255,255,255,0.1);
}
.message-bubble.user .tool-calls { border-color: rgba(255,255,255,0.2); }

.tool-call {
  background: rgba(0,0,0,0.15);
  border-radius: 6px;
  padding: 8px 10px;
  margin-bottom: 4px;
  cursor: pointer;
}
.message-bubble.user .tool-call { background: rgba(255,255,255,0.1); }

.tool-name {
  font-size: 0.8rem;
  color: var(--accent-light);
  font-weight: 600;
  list-style: none;
}
.message-bubble.user .tool-name { color: rgba(255,255,255,0.9); }

.tool-args {
  font-size: 0.72rem;
  margin-top: 6px;
  color: var(--text-dim);
  background: rgba(0,0,0,0.2);
  padding: 10px;
  border-radius: 4px;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-all;
}
.message-bubble.user .tool-args {
  color: rgba(255,255,255,0.7);
  background: rgba(0,0,0,0.15);
}
</style>
