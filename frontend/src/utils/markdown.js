import { marked } from 'marked'
import DOMPurify from 'dompurify'
import hljs from 'highlight.js/lib/common'

marked.setOptions({ breaks: false, gfm: true })
export function renderMarkdown(content = '', sources = []) {
  const html = DOMPurify.sanitize(marked.parse(content), { USE_PROFILES: { html: true } })
  if (!sources.length) return html
  const root = document.createElement('div'); root.innerHTML = html
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT)
  const nodes = []
  while (walker.nextNode()) nodes.push(walker.currentNode)
  for (const node of nodes) {
    if (node.parentElement.closest('pre, code, a, button')) continue
    const text = node.textContent, pattern = /\[(\d+)\]/g
    let cursor = 0, match, found = false
    const fragment = document.createDocumentFragment()
    while ((match = pattern.exec(text))) {
      const source = sources.find(s => s.number === Number(match[1]))
      if (!source) continue
      fragment.append(document.createTextNode(text.slice(cursor, match.index)))
      const button = document.createElement('button')
      button.type = 'button'; button.className = 'inline-citation'
      button.dataset.sourceNumber = match[1]; button.textContent = match[1]
      button.setAttribute('aria-label', '查看来源 ' + match[1] + '：' + source.filename)
      fragment.append(button); cursor = match.index + match[0].length; found = true
    }
    if (found) { fragment.append(document.createTextNode(text.slice(cursor))); node.replaceWith(fragment) }
  }
  return root.innerHTML
}
export function highlightCode(element) {
  element?.querySelectorAll('pre code').forEach(code => {
    if (code.dataset.highlighted) return
    try { hljs.highlightElement(code) } catch { /* Plain text remains readable. */ }
  })
}
export function downloadMarkdown(content, title = '研究成果', sources = []) {
  const references = sources.length ? '\n\n---\n\n## 参考资料\n\n' + sources.map(s => `- [${s.number}] ${s.filename}（片段 ${s.chunk_index + 1}）`).join('\n') : ''
  const url = URL.createObjectURL(new Blob([content + references], { type: 'text/markdown;charset=utf-8' }))
  const a = document.createElement('a')
  a.href = url; a.download = title.replace(/[\\/:*?"<>|]/g, '_').slice(0, 100) + '.md'
  a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000)
}
