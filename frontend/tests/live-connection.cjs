// Opt-in acceptance against the running app; only delete this script's own task.
const { chromium } = require('@playwright/test')
const assert = require('node:assert/strict')

async function main() {
  const baseURL = process.env.WORKBENCH_URL || 'http://localhost:5173'
  const browser = await chromium.launch({ headless: true, channel: process.env.BROWSER_CHANNEL || 'msedge' })
  const page = await browser.newPage()
  const errors = []
  let conversationId
  page.on('pageerror', error => errors.push(error.message))
  page.on('response', response => {
    if (response.url().includes('/api/') && response.status() >= 400) {
      console.log('API error:', new URL(response.url()).pathname, response.status())
    }
  })
  try {
    await page.goto(baseURL)
    await page.waitForFunction(() => document.querySelector('.service-status')?.textContent.includes('资料服务已连接'))
    assert.equal(await page.getByText('历史记录加载失败', { exact: true }).count(), 0)
    console.log('Browser history and health: passed')
    // Ensure the test owns this conversation before asking the UI to execute it.
    const created = await page.request.post(baseURL + '/api/conversations', { data: { title: '浏览器连接验收-' + Date.now() } })
    assert.equal(created.status(), 200)
    conversationId = (await created.json()).id
    await page.getByRole('button', { name: '刷新历史任务', exact: true }).click()
    await page.locator('.conversation-select').filter({ hasText: '浏览器连接验收-' }).click()
    const input = page.getByLabel('描述你的任务')
    await input.fill('你是谁？请用一句话回答。')
    const responsePromise = page.waitForResponse(response => response.url().endsWith('/api/chat') && response.request().method() === 'POST')
    await input.press('Enter')
    const response = await responsePromise
    assert.equal(response.status(), 200)
    await page.waitForFunction(() => document.querySelector('.message-prose')?.textContent.trim().length > 0, null, { timeout: 185000 })
    await page.getByRole('button', { name: '停止生成', exact: true }).waitFor({ state: 'hidden', timeout: 185000 })
    console.log('Browser real model response:', (await page.locator('.message-prose').last().innerText()).slice(0, 300))
    assert.deepEqual(errors, [])
  } finally {
    if (conversationId) {
      const cleanup = await page.request.delete(baseURL + '/api/conversations/' + conversationId)
      console.log('Own test cleanup HTTP:', cleanup.status())
    }
    await browser.close()
  }
}
main().catch(error => { console.error(error); process.exitCode = 1 })
