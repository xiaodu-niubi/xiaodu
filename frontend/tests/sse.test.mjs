import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readEvents } from '../src/utils/sse.js'

const encoder = new TextEncoder()
const body = chunks => new ReadableStream({ start(controller) {
  for (const chunk of chunks) controller.enqueue(typeof chunk === 'string' ? encoder.encode(chunk) : chunk)
  controller.close()
} })
const collect = async chunks => { const events = []; for await (const event of readEvents(body(chunks))) events.push(event); return events }

test('frames spanning packets and CRLF survive intact', async () => {
  assert.deepEqual(await collect(['event: to', 'ken\r\ndata: {"type":"token",', '"content":"你好"}\r\n\r', '\n']),
    [{ event: 'token', data: '{"type":"token","content":"你好"}' }])
})
test('multibyte UTF-8 can be split in the middle of a character', async () => {
  const bytes = encoder.encode('data: 资料\n\n')
  assert.equal((await collect([bytes.slice(0,7), bytes.slice(7,9), bytes.slice(9)]))[0].data, '资料')
})
test('multiline frames, comments and multiple events parse correctly', async () => {
  assert.deepEqual(await collect([': heartbeat\n\nevent: token\ndata: one\ndata: two\n\ndata: three\n\n']),
    [{ event: 'token', data: 'one\ntwo' }, { event: 'message', data: 'three' }])
})
test('trailing data is flushed at EOF', async () => {
  assert.deepEqual(await collect(['event: done\ndata: {"type":"done"}']), [{ event: 'done', data: '{"type":"done"}' }])
})
test('reader cancellation is propagated when a consumer stops', async () => {
  let cancelled = false
  const stream = new ReadableStream({ start(controller) { controller.enqueue(encoder.encode('data: one\n\n')) }, cancel() { cancelled = true } })
  for await (const frame of readEvents(stream)) { assert.equal(frame.data, 'one'); break }
  assert.equal(cancelled, true)
})
