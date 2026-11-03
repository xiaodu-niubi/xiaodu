// Parse SSE frames across arbitrary network boundaries, including CRLF and multiline data.
export async function* readEvents(body) {
  const reader = body.getReader()
  const decoder = new TextDecoder()
  let buffer = '', data = [], event = 'message'
  const take = (line) => {
    if (line === '') {
      if (!data.length) { event = 'message'; return null }
      const frame = { event, data: data.join('\n') }
      data = []; event = 'message'
      return frame
    }
    if (line.startsWith(':')) return null
    const separator = line.indexOf(':')
    const field = separator < 0 ? line : line.slice(0, separator)
    let value = separator < 0 ? '' : line.slice(separator + 1)
    if (value.startsWith(' ')) value = value.slice(1)
    if (field === 'data') data.push(value)
    if (field === 'event') event = value
    return null
  }
  try {
    while (true) {
      const { value, done } = await reader.read()
      buffer += done ? decoder.decode() : decoder.decode(value, { stream: true })
      let end
      while ((end = buffer.indexOf('\n')) >= 0) {
        const line = buffer.slice(0, end).replace(/\r$/, '')
        buffer = buffer.slice(end + 1)
        const frame = take(line)
        if (frame) yield frame
      }
      if (done) {
        if (buffer) take(buffer.replace(/\r$/, ''))
        const frame = take('')
        if (frame) yield frame
        break
      }
    }
  } finally {
    await reader.cancel().catch(() => {})
    reader.releaseLock()
  }
}
