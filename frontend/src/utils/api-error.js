export function httpErrorText(status, detail) {
  if (typeof detail === 'string' && detail.trim()) return detail
  if ([500, 502, 504].includes(status)) return `后端暂时不可用（HTTP ${status}）。请确认 8000 端口的服务已启动，再重试。`
  if (status === 503) return '后端依赖服务尚未就绪（HTTP 503），请检查数据库连接后重试。'
  if (status === 404) return '接口不存在（HTTP 404），请检查前端代理是否指向正确的后端。'
  return `请求失败（HTTP ${status}），请稍后重试。`
}

export function errorText(err) {
  if (err.response) return httpErrorText(err.response.status, err.response.data?.detail)
  if (err.code === 'ERR_NETWORK' || err instanceof TypeError && /fetch|network/i.test(err.message)) {
    return '无法连接服务，请检查后端和前端代理是否已启动，然后重试。'
  }
  return err.message || '服务暂时不可用，请重试。'
}
