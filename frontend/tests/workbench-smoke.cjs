const { chromium } = require('@playwright/test')
const assert = require('node:assert/strict')
const fs = require('node:fs/promises')
const path = require('node:path')

const baseURL = process.env.WORKBENCH_URL || 'http://127.0.0.1:8000'
const output = path.resolve(__dirname, '../../outputs/workbench')
const source = { id: 'chunk-1', number: 1, document_id: 'doc-1', filename: '产品方案.md', chunk_index: 0, snippet: '产品支持知识检索、来源核对和可编辑报告。' }
const docs = ['产品方案.md', '采购要求.md'].map((filename, index) => ({ id: 'doc-' + (index + 1), filename, file_type: 'md', status: 'ready', chunk_count: 3, created_at: '2026-10-13T08:00:00Z' }))

async function main() {
  await fs.mkdir(output, { recursive: true })
  const browser = await chromium.launch({ headless: true, ...(process.env.BROWSER_CHANNEL ? { channel: process.env.BROWSER_CHANNEL } : {}) })
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 940 }, locale: 'zh-CN' })
    const errors = []
    page.on('pageerror', error => errors.push(error.message))
    let saved = null, chatRequests = 0, failNext = false, lastMessage = null
    await page.route(url => url.pathname.startsWith('/api/'), async route => {
      const request = route.request(), url = new URL(request.url()), endpoint = url.pathname
      const json = data => route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(data) })
      if (endpoint === '/api/health') return json({ mysql: '正常', chroma: '正常', redis: '未启用' })
      if (endpoint === '/api/knowledge/list') return json({ documents: docs })
      if (endpoint.endsWith('/content')) return json({ filename: source.filename, content: source.snippet, truncated: false })
      if (endpoint === '/api/conversations') return json({ conversations: lastMessage ? [{ id: 'conversation', title: '资料研究验收', updated_at: new Date().toISOString() }] : [] })
      if (endpoint === '/api/conversations/conversation') return json({ id: 'conversation', messages: lastMessage ? [{ id: 1, role: 'user', content: '介绍产品' }, lastMessage] : [] })
      if (endpoint === '/api/artifacts') return json({ artifacts: saved ? [{ id: 2, conversation_id: 'conversation', conversation_title: '资料研究验收', metadata: lastMessage.metadata }] : [] })
      if (endpoint === '/api/artifacts/conversation/2') {
        saved = request.postDataJSON(); lastMessage.metadata.artifact = saved
        return json({ id: 2, conversation_id: 'conversation', metadata: lastMessage.metadata })
      }
      if (endpoint === '/api/chat') {
        chatRequests++
        const payload = request.postDataJSON()
        if (failNext) {
          failNext = false
          return route.fulfill({ status: 200, contentType: 'text/event-stream', body: 'event: error\ndata: {"type":"error","content":"连接中断，请重试"}\n\n' })
        }
        const content = '## 产品能力\n\n支持知识检索、来源核对和可编辑报告 [1]。\n\n| 能力 | 用途 |\n| --- | --- |\n| 知识检索 | 查找依据 |\n\n<img src="x" onerror="window.__xss=1"><a href="javascript:window.__xss=2">链接</a>'
        lastMessage = { id: 2, role: 'assistant', content, tool_calls: [], metadata: { status: 'completed', mode: payload.mode, sources: [source] } }
        const events = [{ type: 'session', conversation_id: 'conversation', message_id: 2 }, { type: 'status', content: 'executing_search' },
          { type: 'sources', metadata: { sources: [source] } }, { type: 'token', content: '先查资料' }, { type: 'reset' },
          { type: 'tool', metadata: { id: 't', name: 'search_knowledge', status: 'running' } },
          { type: 'tool', metadata: { id: 't', name: 'search_knowledge', status: 'completed', result: source.snippet } },
          { type: 'token', content }, { type: 'done', conversation_id: 'conversation' }]
        return route.fulfill({ status: 200, contentType: 'text/event-stream', body: events.map(e => 'event: ' + e.type + '\ndata: ' + JSON.stringify(e) + '\n\n').join('') })
      }
      return json({})
    })
    await page.goto(baseURL)
    await page.getByRole('heading', { name: /把资料/ }).waitFor()
    await page.screenshot({ path: path.join(output, 'desktop.png'), fullPage: true })
    await page.locator('.starter-card').first().click()
    await page.getByLabel('描述你的任务').fill('介绍产品')
    await page.getByLabel('描述你的任务').press('Enter')
    await page.getByRole('heading', { name: '产品能力' }).waitFor()
    await page.getByRole('button', { name: '停止生成', exact: true }).waitFor({ state: 'hidden' })
    assert.equal(await page.locator('[onerror], a[href^="javascript:"]').count(), 0)
    assert.equal(await page.evaluate(() => window.__xss), undefined)
    assert.equal(await page.locator('.message-prose').getByText('先查资料').count(), 0)
    assert.equal(await page.locator('.tool-entry').count(), 1)
    await page.getByRole('button', { name: /查看来源 1/ }).click()
    await page.getByRole('button', { name: /查看资料原文/ }).click()
    await page.locator('.source-original').waitFor()
    await page.getByRole('button', { name: '关闭资料原文' }).click()
    await page.screenshot({ path: path.join(output, 'sources.png'), fullPage: true })
    await page.getByRole('tab', { name: '成果', exact: true }).click()
    await page.getByRole('button', { name: '编辑', exact: true }).click()
    await page.getByLabel('编辑成果 Markdown').fill('# 产品研究报告\n\n已核对资料，建议先进行试用。 [1]')
    await page.getByLabel('成果名称').fill('产品研究报告')
    await page.getByRole('button', { name: '关闭任务详情' }).click()
    await page.getByRole('button', { name: /编辑成果/, exact: true }).click()
    assert.ok((await page.getByLabel('编辑成果 Markdown').inputValue()).includes('建议先进行试用'))
    const handle = page.getByRole('separator', { name: '调整任务详情宽度' })
    await handle.focus(); await handle.press('ArrowLeft')
    assert.equal(await handle.getAttribute('aria-valuenow'), '390')
    await page.getByRole('button', { name: '保存成果', exact: true }).click()
    await page.getByText('成果已保存', { exact: true }).waitFor()
    assert.equal(saved.title, '产品研究报告')
    assert.ok(saved.content.includes('建议先进行试用'))
    await page.getByRole('button', { name: '导出', exact: true }).click()
    await page.getByRole('button', { name: '关闭任务详情' }).click()
    await page.locator('.primary-navigation').getByRole('button', { name: '成果', exact: true }).click()
    await page.getByRole('heading', { name: '产品研究报告', exact: true }).waitFor()
    await page.getByRole('button', { name: /继续编辑/ }).click()
    await page.getByLabel('成果名称').waitFor()
    assert.equal(await page.getByLabel('成果名称').inputValue(), '产品研究报告')
    await page.getByRole('button', { name: '关闭任务详情' }).click()
    await page.locator('.primary-navigation').getByRole('button', { name: /知识库/ }).click()
    await page.getByRole('heading', { name: '你的知识库' }).waitFor()
    assert.equal(await page.locator('.document-name').count(), 2)
    await page.getByLabel('搜索资料').fill('采购')
    assert.equal(await page.locator('.document-name').count(), 1)
    await page.getByRole('button', { name: /新任务/ }).click()
    await page.getByLabel('任务类型').selectOption('compare')
    await page.getByLabel('描述你的任务').fill('比较方案')
    await page.getByLabel('描述你的任务').press('Enter')
    await page.getByText('对比文档前，请选择至少两份已就绪的资料。', { exact: true }).waitFor()
    assert.equal(chatRequests, 1)
    await page.locator('.document-picker summary').click()
    await page.locator('.document-popover').getByLabel('产品方案.md', { exact: true }).check()
    await page.locator('.document-popover').getByLabel('采购要求.md', { exact: true }).check()
    await page.getByRole('button', { name: '完成', exact: true }).click()
    await page.getByLabel('描述你的任务').press('Enter')
    await page.getByRole('heading', { name: '产品能力' }).waitFor()
    assert.equal(chatRequests, 2)
    await page.getByRole('button', { name: /新任务/ }).click()
    await page.getByLabel('任务类型').selectOption('chat')
    failNext = true
    await page.getByLabel('描述你的任务').fill('测试错误')
    await page.getByLabel('描述你的任务').press('Enter')
    await page.locator('.chat-error').waitFor()
    await page.getByRole('button', { name: '发送任务', exact: true }).waitFor()
    assert.equal(await page.getByRole('button', { name: '停止生成', exact: true }).count(), 0)
    await page.getByRole('button', { name: /新任务/ }).click()
    await page.getByRole('button', { name: '切换深色主题' }).click()
    assert.equal(await page.locator('html.theme-dark').count(), 1)
    await page.screenshot({ path: path.join(output, 'dark.png'), fullPage: true })
    await page.getByRole('button', { name: '切换浅色主题' }).click()
    await page.setViewportSize({ width: 390, height: 844 })
    await page.getByRole('button', { name: '关闭导航', exact: true }).click()
    await page.screenshot({ path: path.join(output, 'mobile.png'), fullPage: true })
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true)
    await page.getByRole('button', { name: '展开导航', exact: true }).click()
    await page.locator('.primary-navigation').getByRole('button', { name: /知识库/ }).click()
    await page.getByRole('heading', { name: '你的知识库' }).waitFor()
    assert.equal(await page.locator('.sidebar').count(), 0)
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true)
    assert.deepEqual(errors, [])
    console.log('Browser checks passed: navigation, citations, original document, artifact editing/save/export/reopen, comparison scope, error recovery, themes, mobile layout and safe Markdown.')
  } finally { await browser.close() }
}
main().catch(error => { console.error(error); process.exitCode = 1 })
