/** 司机档案模块共享类型：与后端 app.security / DriverListResult 的口径对齐。 */

export type FieldMode = 'editable' | 'readonly' | 'hidden'

export interface FieldPermission {
  name: string
  mode: FieldMode
  sensitive: boolean
}

export interface ActionPermission {
  name: string
  enabled: boolean
}

export interface DriverPermission {
  role: string
  roleLabel: string
  fields: FieldPermission[]
  canCreate: boolean
  canExport: boolean
  actions: ActionPermission[]
  notice: string
  hiddenPlaceholder: string
}

export type DriverRow = Record<string, string | number | null>

export interface DriverListPayload {
  items: DriverRow[]
  total: number
  page: number
  size: number
  permission: DriverPermission
}

export interface DriverDetailPayload {
  entry: DriverRow
  permission: DriverPermission
}

/** 列表页与详情页共用的字段取值：隐藏字段显示占位文案，保证两处范围一致。 */
export function displayValue(
  row: DriverRow,
  field: FieldPermission,
  placeholder: string,
): string {
  if (field.mode === 'hidden') {
    return placeholder
  }
  const value = row[field.name]
  return value === null || value === undefined || value === '' ? '—' : String(value)
}

/** 没有权限时用只读样式：输入框 disabled、操作按钮禁用。 */
export function isReadonly(mode: FieldMode): boolean {
  return mode !== 'editable'
}
