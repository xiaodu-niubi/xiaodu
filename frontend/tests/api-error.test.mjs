import { test } from 'node:test'
import assert from 'node:assert/strict'
import { errorText, httpErrorText } from '../src/utils/api-error.js'

test('proxy failures include status and backend recovery instructions', () => {
  for (const status of [500, 502, 504]) {
    assert.match(httpErrorText(status), new RegExp(`HTTP ${status}`))
    assert.match(httpErrorText(status), /8000/)
  }
  assert.match(httpErrorText(404), /代理/)
})
test('server details remain visible for database and credential failures', () => {
  assert.equal(httpErrorText(503, 'MySQL 未连接'), 'MySQL 未连接')
  assert.equal(errorText({ response: { status: 401, data: { detail: '请更新密钥' } } }), '请更新密钥')
  assert.match(httpErrorText(503), /数据库/)
})
test('network errors give connection instructions without displaying raw HTML', () => {
  assert.match(errorText(new TypeError('Failed to fetch')), /无法连接服务/)
  assert.match(errorText({ code: 'ERR_NETWORK' }), /无法连接服务/)
  assert.match(errorText({ response: { status: 502, data: '<html>proxy failure</html>' } }), /HTTP 502/)
})
