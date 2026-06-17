<template>
  <div class="chat-view">
    <div class="messages-container" ref="messagesContainer">
      <div v-if="chatStore.messages.length === 0" class="welcome">
        <h2>多智能体系统</h2>
        <p class="welcome-desc">五大智能体分工协作，具备动态知识检索、ReAct 推理与函数调用能力</p>
        <div class="feature-grid">
          <div class="feature-card">
            <span class="feature-icon">🧠</span>
            <div class="feature-text">
              <strong>编排调度</strong>
              <span>智能分析意图，精准分发任务</span>
            </div>
          </div>
          <div class="feature-card">
            <span class="feature-icon">🔍</span>
            <div class="feature-text">
              <strong>动态检索</strong>
              <span>按需搜索知识库，精准定位</span>
            </div>
          </div>
          <div class="feature-card">
            <span class="feature-icon">🛠️</span>
            <div class="feature-text">
              <strong>工具调用</strong>
              <span>计算 / 代码 / 搜索 / 文件</span>
            </div>
          </div>
          <div class="feature-card">
            <span class="feature-icon">🔌</span>
            <div class="feature-text">
              <strong>MCP 协议</strong>
              <span>标准化工具生态，可扩展</span>
            </div>
          </div>
        </div>
        <div class="quick-actions">
          <span class="quick-label">试试问：</span>
          <button v-for="q in quickQuestions" :key="q" class="quick-btn" @click="chatStore.sendMessage(q)">
            {{ q }}
          </button>
        </div>
      </div>

      <ChatMessage v-for="msg in chatStore.messages" :key="msg.id" :message="msg" v-memo="[msg.id, msg.content]" />

      <div v-if="chatStore.isLoading || chatStore.statusText" class="loading-card">
        <div class="typing-indicator">
          <span></span><span></span><span></span>
        </div>
        <span>{{ chatStore.statusText || '思考中...' }}</span>
      </div>

      <div v-if="chatStore.error" class="error-banner">
        <span>⚠ {{ chatStore.error }}</span>
        <div class="error-actions">
          <button v-if="retryAction" class="error-retry" @click="handleRetry">重试</button>
          <button class="error-dismiss" @click="chatStore.error = null; retryAction = null">×</button>
        </div>
      </div>
    </div>

    <ChatInput :disabled="chatStore.isLoading" @send="chatStore.sendMessage" @stop="chatStore.stopGeneration()" />
  </div>
</template>

<script setup>
import { watch, ref, onMounted, onUnmounted } from 'vue'
import { useChatStore } from '../stores/chat.js'
import ChatMessage from '../components/ChatMessage.vue'
import ChatInput from '../components/ChatInput.vue'

const chatStore = useChatStore()
const messagesContainer = ref(null)
const retryAction = ref(null)

const quickQuestions = [
  '公司提供哪些产品？',
  'API 怎么调用？',
  '有哪些模型可用？',
  '如何申请退款？',
]

let scrollPending = false
watch(
  () => [chatStore.messages.length, chatStore.streamingContent],
  () => {
    if (!scrollPending) {
      scrollPending = true
      requestAnimationFrame(() => {
        scrollPending = false
        if (messagesContainer.value) {
          messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
        }
      })
    }
  }
)

// 离线检测
function handleOffline() {
  chatStore.error = '网络连接已断开，请检查网络'
}
function handleOnline() {
  if (chatStore.error === '网络连接已断开，请检查网络') {
    chatStore.error = null
  }
}
onMounted(() => {
  window.addEventListener('offline', handleOffline)
  window.addEventListener('online', handleOnline)
})
onUnmounted(() => {
  window.removeEventListener('offline', handleOffline)
  window.removeEventListener('online', handleOnline)
})

function handleRetry() {
  if (retryAction.value) {
    retryAction.value()
    retryAction.value = null
  }
  chatStore.error = null
}
</script>

<style scoped>
.chat-view {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background:
    radial-gradient(ellipse at 50% 0%, rgba(99,102,241,0.06) 0%, transparent 60%),
    var(--bg-primary);
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  scroll-behavior: smooth;
}

/* ---- 欢迎页 ---- */
.welcome {
  text-align: center;
  padding: 50px 20px 80px;
  max-width: 600px;
  margin: 0 auto;
}

.welcome h2 {
  font-size: 1.6rem;
  font-weight: 700;
  margin-bottom: 8px;
  background: linear-gradient(135deg, var(--text-primary), var(--accent-light));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.welcome-desc {
  color: var(--text-secondary);
  margin-bottom: 40px;
  line-height: 1.6;
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
  margin-bottom: 32px;
}

.feature-card {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 16px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  text-align: left;
  transition: all var(--transition);
}
.feature-card:hover {
  border-color: var(--accent);
  background: rgba(99,102,241,0.05);
}
.feature-icon {
  font-size: 1.4rem;
  flex-shrink: 0;
  margin-top: 1px;
}
.feature-text strong {
  display: block;
  font-size: 0.85rem;
  color: var(--text-primary);
  margin-bottom: 2px;
}
.feature-text span {
  font-size: 0.75rem;
  color: var(--text-dim);
}

/* 快捷提问 */
.quick-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
  align-items: center;
}
.quick-label {
  font-size: 0.8rem;
  color: var(--text-dim);
}
.quick-btn {
  padding: 6px 14px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 20px;
  color: var(--text-secondary);
  font-size: 0.8rem;
  cursor: pointer;
  transition: all var(--transition);
}
.quick-btn:hover {
  border-color: var(--accent);
  color: var(--accent-light);
  background: rgba(99,102,241,0.08);
}

/* ---- 加载态 ---- */
.loading-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  max-width: 200px;
  margin-top: 12px;
  animation: fadeInUp 0.3s ease;
}
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.typing-indicator {
  display: flex;
  gap: 3px;
}
.typing-indicator span {
  width: 6px; height: 6px;
  background: var(--accent-light);
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out;
}
.typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.4s; }
@keyframes bounce {
  0%, 80%, 100% { transform: scale(0.5); opacity: 0.3; }
  40% { transform: scale(1); opacity: 1; }
}

.loading-card > span {
  font-size: 0.85rem;
  color: var(--text-dim);
}

.error-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: rgba(248,113,113,0.08);
  border: 1px solid rgba(248,113,113,0.3);
  border-radius: var(--radius);
  color: var(--error);
  margin-top: 16px;
  font-size: 0.85rem;
}
.error-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.error-retry {
  padding: 4px 12px;
  background: rgba(248,113,113,0.15);
  border: 1px solid rgba(248,113,113,0.3);
  border-radius: var(--radius-sm);
  color: var(--error);
  cursor: pointer;
  font-size: 0.8rem;
  transition: all var(--transition);
}
.error-retry:hover {
  background: rgba(248,113,113,0.25);
}
.error-dismiss {
  background: none;
  border: none;
  color: var(--error);
  cursor: pointer;
  font-size: 1.2rem;
  opacity: 0.7;
}
.error-dismiss:hover { opacity: 1; }

@media (max-width: 768px) {
  .feature-grid { grid-template-columns: 1fr; }
  .messages-container { padding: 16px; }
}
</style>
