import { defineStore } from 'pinia'

/** 岗位编码与后端 app.services.driver_permission.ROLES 保持一致。 */
export const ROLE_OPTIONS = [
  { code: 'ops_admin', name: '运营管理员' },
  { code: 'dispatcher', name: '调度岗' },
  { code: 'other', name: '其它岗位' },
] as const

export type RoleCode = (typeof ROLE_OPTIONS)[number]['code']

const ROLE_STORAGE_KEY = 'operator-role'

function readStoredRole(): RoleCode {
  const stored = window.localStorage.getItem(ROLE_STORAGE_KEY)
  return ROLE_OPTIONS.some((item) => item.code === stored) ? (stored as RoleCode) : 'ops_admin'
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
    roleName: (state) => ROLE_OPTIONS.find((item) => item.code === state.role)?.name ?? state.role,
  },
  actions: {
    setShift(label: string) {
      this.shiftLabel = label
    },
    /** 调整岗位归属并持久化：重新进入页面后仍按新归属生效。 */
    setRole(role: RoleCode) {
      this.role = role
      window.localStorage.setItem(ROLE_STORAGE_KEY, role)
    },
  },
})
