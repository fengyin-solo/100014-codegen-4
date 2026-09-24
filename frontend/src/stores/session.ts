import { defineStore } from 'pinia'

export type RoleCode = 'ops_admin' | 'dispatcher' | 'other'

export interface RoleOption {
  code: RoleCode
  label: string
}

// 与后端 app.security.ROLE_LABELS 保持一致
export const ROLE_OPTIONS: RoleOption[] = [
  { code: 'ops_admin', label: '运营管理员' },
  { code: 'dispatcher', label: '调度员' },
  { code: 'other', label: '其它岗位' },
]

const ROLE_STORAGE_KEY = 'driver-module-role'

function readStoredRole(): RoleCode {
  const stored = window.localStorage.getItem(ROLE_STORAGE_KEY)
  return ROLE_OPTIONS.some((item) => item.code === stored)
    ? (stored as RoleCode)
    : 'ops_admin'
}

export const useSessionStore = defineStore('session', {
  state: () => ({
    operator: '值班管理员',
    shiftLabel: '白班 08:00-20:00',
    scope: '冷链物流温控运营平台',
    role: readStoredRole() as RoleCode,
  }),
  getters: {
    canOperate: (state) => state.operator.length > 0,
    roleLabel: (state) =>
      ROLE_OPTIONS.find((item) => item.code === state.role)?.label ?? '其它岗位',
  },
  actions: {
    setShift(label: string) {
      this.shiftLabel = label
    },
    setRole(role: RoleCode) {
      this.role = role
      // 权限调整写入本地：重新进入页面仍按新的岗位归属生效
      window.localStorage.setItem(ROLE_STORAGE_KEY, role)
    },
  },
})
