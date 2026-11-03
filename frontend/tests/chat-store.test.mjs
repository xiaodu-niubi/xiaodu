import { test } from 'node:test'
import assert from 'node:assert/strict'
import { createPinia, setActivePinia } from 'pinia'
import api from '../src/api/index.js'
import { useChatStore } from '../src/stores/chat.js'

globalThis.window = { innerWidth: 1440 }
const setup = () => {
  setActivePinia(createPinia())
  const callbacks = []
  api.sendMessageStream = (payload, event, error) => {
    const entry = { payload, event, error, aborted: false }; callbacks.push(entry)
    return { abort() { entry.aborted = true } }
  }
  api.listConversations = async () => []
  return { store: useChatStore(), callbacks }
}

test('routing does not enable another send or remove the stop state', () => {
  const { store, callbacks } = setup()
  store.sendMessage('first')
  callbacks[0].event({ type: 'status', content: 'routing' })
  store.sendMessage('second')
  assert.equal(store.isLoading, true)
  assert.equal(callbacks.length, 1)
})
test('late events from a stopped task cannot mutate the next task', () => {
  const { store, callbacks } = setup()
  store.sendMessage('first'); const old = callbacks[0]
  store.newConversation(); store.sendMessage('second')
  old.event({ type: 'token', content: 'stale text' })
  old.event({ type: 'done', conversation_id: 'old-id' })
  old.error('stale failure')
  assert.equal(old.aborted, true)
  assert.equal(store.isLoading, true)
  assert.equal(store.currentConversationId, null)
  assert.equal(store.error, null)
  assert.equal(store.messages.at(-1).content, '')
  callbacks[1].event({ type: 'token', content: 'current' })
  assert.equal(store.messages.at(-1).content, 'current')
})
test('sources, server IDs and tools belong to the correct message', () => {
  const { store, callbacks } = setup()
  store.sendMessage('question'); const stream = callbacks[0]
  stream.event({ type: 'session', conversation_id: 'c', message_id: 42, task_id: 'task' })
  stream.event({ type: 'sources', metadata: { sources: [{ id: 's', number: 1 }] } })
  stream.event({ type: 'tool', metadata: { id: 't', status: 'running' } })
  stream.event({ type: 'tool', metadata: { id: 't', status: 'completed' } })
  stream.event({ type: 'token', content: 'preliminary' })
  stream.event({ type: 'reset' })
  stream.event({ type: 'token', content: 'final' })
  stream.event({ type: 'done', conversation_id: 'c' })
  const message = store.messages.at(-1)
  assert.equal(message.id, 42)
  assert.equal(message.content, 'final')
  assert.equal(message.tool_calls.length, 1)
  assert.equal(message.tool_calls[0].status, 'completed')
  assert.equal(message.metadata.sources[0].id, 's')
  assert.equal(message.metadata.status, 'completed')
  assert.equal(store.isLoading, false)
})
