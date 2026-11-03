import axios from 'axios'
import { readEvents } from '../utils/sse.js'
import { errorText, httpErrorText } from '../utils/api-error.js'
export { errorText } from '../utils/api-error.js'

const client = axios.create({ baseURL: '/api', timeout: 180000 })

function sendMessageStream(payload, onEvent, onError) {
  const controller = new AbortController()
  let timedOut = false
  const timer = setTimeout(() => { timedOut = true; controller.abort() }, 195000)
  async function run() {
    let complete = false
    try {
      const response = await fetch('/api/chat', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...payload, stream: true }), signal: controller.signal,
      })
      if (!response.ok) {
        const body = await response.json().catch(() => ({}))
        throw new Error(httpErrorText(response.status, body.detail))
      }
      if (!response.body || !response.headers.get('content-type')?.includes('text/event-stream')) {
        throw new Error('服务没有返回有效的流式响应。')
      }
      for await (const frame of readEvents(response.body)) {
        let event
        try { event = JSON.parse(frame.data) }
        catch { throw new Error('收到无效响应，请重试。') }
        if (event.type === 'error') throw new Error(event.content || '任务执行失败。')
        onEvent(event)
        if (event.type === 'done') { complete = true; break }
      }
      if (!complete && !controller.signal.aborted) throw new Error('连接中断，已保留收到的内容。可以重试此任务。')
    } catch (err) {
      if (timedOut) onError('任务超时，已保留收到的内容。')
      else if (err.name !== 'AbortError') onError(errorText(err))
    } finally { clearTimeout(timer) }
  }
  run()
  return controller
}
export default {
  sendMessageStream,
  async listConversations() { return (await client.get('/conversations')).data.conversations || [] },
  async getConversation(id) { return (await client.get('/conversations/' + id)).data },
  async deleteConversation(id) { await client.delete('/conversations/' + id) },
  async updateConversationTitle(id, title) { await client.put('/conversations/' + id, { title }) },
  async listKnowledge() { return (await client.get('/knowledge/list')).data.documents || [] },
  async uploadKnowledge(file) {
    const form = new FormData(); form.append('file', file)
    return (await client.post('/knowledge/upload', form)).data
  },
  async reloadKnowledge() { return (await client.post('/knowledge/reload')).data },
  async reindexKnowledge(id) { return (await client.post('/knowledge/' + id + '/reindex')).data },
  async readKnowledge(id) { return (await client.get('/knowledge/' + id + '/content')).data },
  async listArtifacts() { return (await client.get('/artifacts')).data.artifacts || [] },
  async saveArtifact(conversationId, messageId, title, content) {
    return (await client.put('/artifacts/' + conversationId + '/' + messageId, { title, content })).data
  },
  async healthCheck() { return (await client.get('/health', { timeout: 12000 })).data },
}
