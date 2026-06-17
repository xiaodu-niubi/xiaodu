<template>
  <Teleport to="body">
    <div v-if="visible" class="modal-overlay" @click.self="onCancel">
      <div class="modal-box">
        <div class="modal-header">{{ title }}</div>
        <div v-if="type === 'prompt'" class="modal-body">
          <input
            ref="inputRef"
            v-model="inputValue"
            class="modal-input"
            :placeholder="placeholder"
            @keydown.enter="onConfirm"
            @keydown.escape="onCancel"
          />
        </div>
        <div v-else class="modal-body">
          <p>{{ message }}</p>
        </div>
        <div class="modal-footer">
          <button class="modal-btn cancel" @click="onCancel">取消</button>
          <button class="modal-btn confirm" :class="{ danger: danger }" @click="onConfirm">
            {{ confirmText }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, nextTick, watch } from 'vue'

const props = defineProps({
  visible: { type: Boolean, default: false },
  type: { type: String, default: 'confirm' },
  title: { type: String, default: '确认' },
  message: { type: String, default: '' },
  placeholder: { type: String, default: '' },
  confirmText: { type: String, default: '确定' },
  danger: { type: Boolean, default: false },
  initialValue: { type: String, default: '' },
})

const emit = defineEmits(['confirm', 'cancel'])

const inputValue = ref(props.initialValue)
const inputRef = ref(null)

watch(() => props.visible, async (v) => {
  if (v && props.type === 'prompt') {
    inputValue.value = props.initialValue
    await nextTick()
    inputRef.value?.focus()
    inputRef.value?.select()
  }
})

function onConfirm() {
  emit('confirm', props.type === 'prompt' ? inputValue.value : true)
}

function onCancel() {
  emit('cancel')
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  backdrop-filter: blur(4px);
  animation: fadeIn 0.15s ease;
}
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.modal-box {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 24px;
  min-width: 360px;
  max-width: 480px;
  box-shadow: 0 16px 48px rgba(0,0,0,0.5);
  animation: slideUp 0.2s ease;
}
@keyframes slideUp {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.modal-header {
  font-size: 1rem;
  font-weight: 600;
  margin-bottom: 16px;
}

.modal-body {
  margin-bottom: 20px;
}

.modal-body p {
  color: var(--text-secondary);
  font-size: 0.9rem;
  line-height: 1.5;
}

.modal-input {
  width: 100%;
  padding: 10px 14px;
  background: var(--bg-primary);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text-primary);
  font-size: 0.9rem;
  outline: none;
  transition: border-color var(--transition);
}
.modal-input:focus {
  border-color: var(--accent);
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.modal-btn {
  padding: 8px 18px;
  border-radius: var(--radius-sm);
  font-size: 0.85rem;
  cursor: pointer;
  border: 1px solid var(--border);
  transition: all var(--transition);
}
.modal-btn.cancel {
  background: transparent;
  color: var(--text-secondary);
}
.modal-btn.cancel:hover {
  background: var(--surface);
}
.modal-btn.confirm {
  background: var(--accent);
  color: #fff;
  border-color: var(--accent);
  font-weight: 500;
}
.modal-btn.confirm:hover {
  opacity: 0.9;
}
.modal-btn.confirm.danger {
  background: var(--error);
  border-color: var(--error);
}
</style>
