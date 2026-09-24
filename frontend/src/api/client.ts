/** 统一请求封装：拼后端地址、带当前岗位、抛网络错误、给页脚留一句可读的说明。 */
const API_BASE = import.meta.env.VITE_API_BASE ?? ''
const ROLE_STORAGE_KEY = 'driver-module-role'

function currentRole(): string {
  // 直接读本地存储，保证岗位调整后下一次请求立即按新归属判定
  return window.localStorage.getItem(ROLE_STORAGE_KEY) ?? 'ops_admin'
}

export function request(path: string, init?: RequestInit): Promise<Response> {
  const url = path.startsWith('http') ? path : `${API_BASE}${path}`
  const headers = new Headers(init?.headers ?? { 'Content-Type': 'application/json' })
  if (!headers.has('X-Operator-Role')) {
    headers.set('X-Operator-Role', currentRole())
  }
  return fetch(url, { ...init, headers }).catch((error: unknown) => {
    const detail = error instanceof Error ? error.message : '请求未送达'
    throw new Error(`接口请求失败：${detail}`)
  })
}

/** 提取后端校验/越权原因（FastAPI 错误体形如 {"detail": "..."}）。 */
export async function readErrorDetail(response: Response, fallback: string): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown }
    if (typeof payload.detail === 'string' && payload.detail.trim()) {
      return payload.detail
    }
  } catch {
    // 非 JSON 错误体时回退到通用提示
  }
  return fallback
}

export async function fetchJson<T>(path: string): Promise<T> {
  const response = await request(path)
  if (!response.ok) {
    throw new Error(`接口返回 ${response.status}，数据未更新`)
  }
  return (await response.json()) as T
}
