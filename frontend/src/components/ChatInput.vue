<template>
  <div class="chat-input-container">
    <div class="input-wrapper">
      <form @submit.prevent="handleSend" class="chat-input-form">
        <textarea
          ref="inputRef"
          v-model="inputText"
          :disabled="disabled"
          placeholder="向 DeepSeek 发送消息..."
          rows="1"
          class="chat-textarea"
          @keydown.enter.exact.prevent="handleSend"
          @keydown.enter.shift.exact="inputText += '\n'"
          @input="autoResize"
        />
        <button
          v-if="!disabled"
          type="submit"
          :disabled="!inputText.trim()"
          class="send-button"
          :class="{ active: inputText.trim() }"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <line x1="12" y1="19" x2="12" y2="5"></line>
            <polyline points="5 12 12 5 19 12"></polyline>
          </svg>
        </button>
        <button
          v-else
          type="button"
          class="stop-button"
          @click="$emit('stop')"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
            <rect x="4" y="4" width="16" height="16" rx="2" />
          </svg>
        </button>
      </form>
    </div>
    <div class="input-footer">
      <span class="hint">Enter 发送 · Shift+Enter 换行</span>
      <span class="hint char-count">{{ inputText.length }} 字</span>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted } from 'vue'

const props = defineProps({
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['send', 'stop'])

const inputText = ref('')
const inputRef = ref(null)

function handleSend() {
  if (!inputText.value.trim() || props.disabled) return
  emit('send', inputText.value.trim())
  inputText.value = ''
  nextTick(() => {
    if (inputRef.value) inputRef.value.style.height = 'auto'
  })
}

function autoResize() {
  const el = inputRef.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 180) + 'px'
}

onMounted(() => { inputRef.value?.focus() })
</script>

<style scoped>
.chat-input-container {
  padding: 16px 24px 20px;
  flex-shrink: 0;
  background:
    linear-gradient(to top, var(--bg-primary) 60%, transparent),
    var(--bg-primary);
}

.input-wrapper {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-xl);
  padding: 4px;
  transition: all var(--transition);
}
.input-wrapper:focus-within {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-glow);
}

.chat-input-form {
  display: flex;
  gap: 2px;
  align-items: flex-end;
}

.chat-textarea {
  flex: 1;
  padding: 12px 12px 12px 16px;
  background: transparent;
  border: none;
  color: var(--text-primary);
  font-size: 0.93rem;
  font-family: inherit;
  resize: none;
  outline: none;
  line-height: 1.55;
  max-height: 180px;
}
.chat-textarea::placeholder { color: var(--text-dim); }
.chat-textarea:disabled { opacity: 0.4; }

.send-button {
  width: 38px; height: 38px;
  border: none;
  border-radius: 50%;
  background: var(--border);
  color: var(--text-dim);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all var(--transition);
  margin: 4px;
}
.send-button.active {
  background: linear-gradient(135deg, var(--accent), #7c3aed);
  color: #fff;
  box-shadow: 0 2px 12px var(--accent-glow);
}
.send-button.active:hover {
  transform: scale(1.05);
  box-shadow: 0 4px 20px var(--accent-glow);
}
.send-button:disabled { opacity: 0.3; cursor: not-allowed; }

.stop-button {
  width: 38px; height: 38px;
  border: none;
  border-radius: 50%;
  background: var(--error);
  color: #fff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all var(--transition);
  margin: 4px;
  animation: stopPulse 1.2s ease-in-out infinite;
}
.stop-button:hover {
  transform: scale(1.08);
  box-shadow: 0 2px 16px rgba(248,113,113,0.4);
}
@keyframes stopPulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(248,113,113,0.4); }
  50% { box-shadow: 0 0 0 8px rgba(248,113,113,0); }
}

.spinner {
  width: 16px; height: 16px;
  border: 2px solid transparent;
  border-top-color: var(--text-dim);
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.input-footer {
  display: flex;
  justify-content: space-between;
  padding: 6px 8px 0;
}
.hint { font-size: 0.72rem; color: var(--text-dim); }
</style>
