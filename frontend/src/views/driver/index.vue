<template>
  <section class="page" data-module="driver">
    <header class="page-head">
      <div>
        <h2>司机管理管理</h2>
        <p class="page-desc">维护司机档案，围绕司机工号、司机姓名、联系电话、驾驶证号做登记、筛选与状态流转。</p>
      </div>
      <div class="page-actions">
        <button
          class="btn primary"
          type="button"
          :disabled="!permission?.canCreate"
          :title="permission && !permission.canCreate ? noWriteHint : ''"
          @click="openCreate"
        >
          登记司机档案
        </button>
        <button class="btn" type="button" @click="exportRows">导出司机管理清单</button>
      </div>
    </header>

    <div v-if="permission" class="permission-banner" :class="permission.role">
      <span class="permission-role">当前岗位：{{ permission.roleLabel }}</span>
      <span>{{ permission.notice }}</span>
    </div>

    <div class="stat-row">
      <article v-for="item in stats" :key="item.label" class="stat-card">
        <span class="stat-label">{{ item.label }}</span>
        <strong class="stat-value">{{ item.value }}</strong>
      </article>
    </div>

    <form class="filter-bar" @submit.prevent="reload">
      <label class="filter-item">
        <span>司机工号</span>
        <input v-model="keyword" placeholder="按司机工号检索" />
      </label>
      <label class="filter-item">
        <span>在岗状态</span>
        <select v-model="statusFilter">
          <option value="">全部状态</option>
          <option v-for="status in statuses" :key="status" :value="status">{{ status }}</option>
        </select>
      </label>
      <button class="btn" type="submit">查询</button>
      <button class="btn ghost" type="button" @click="resetFilters">重置条件</button>
    </form>

    <table class="data-table">
      <thead>
        <tr>
          <th v-for="field in visibleColumns" :key="field.name">
            {{ field.name }}
            <span v-if="field.mode === 'hidden'" class="lock-mark" title="当前岗位无权查看该字段">🔒</span>
          </th>
          <th>可执行动作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="String(row.id)">
          <td
            v-for="field in visibleColumns"
            :key="field.name"
            :class="{ 'cell-hidden': field.mode === 'hidden' }"
          >
            {{ displayValue(row, field, permission?.hiddenPlaceholder ?? '—') }}
          </td>
          <td class="row-actions">
            <button class="link" type="button" @click="openDetail(row)">查看档案</button>
            <button
              v-for="action in writeActions"
              :key="action.name"
              class="link"
              type="button"
              :disabled="!action.enabled"
              :title="!action.enabled ? noWriteHint : ''"
              @click="runAction(action.name, row)"
            >
              {{ action.name }}
            </button>
          </td>
        </tr>
        <tr v-if="!rows.length">
          <td :colspan="visibleColumns.length + 1" class="empty-state">暂无司机管理数据，可先登记司机档案</td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>共 {{ total }} 条司机管理记录</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>

    <!-- 登记司机档案：只有运营管理员能打开；无权限岗位的按钮为禁用态 -->
    <div v-if="creating" class="modal-mask" @click.self="closeCreate">
      <div class="modal-card">
        <h3>登记司机档案</h3>
        <form class="modal-form" @submit.prevent="submitCreate">
          <label v-for="field in formFields" :key="field.name" class="filter-item">
            <span>
              {{ field.name }}
              <em v-if="requiredFields.includes(field.name)" class="required-mark">*</em>
            </span>
            <input v-model="createForm[field.name]" :placeholder="`请输入${field.name}`" />
          </label>
          <p v-if="formError" class="error-text">{{ formError }}</p>
          <div class="modal-actions">
            <button class="btn" type="button" @click="closeCreate">取消</button>
            <button class="btn primary" type="submit" :disabled="submitting">
              {{ submitting ? '提交中…' : '确认登记' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import { readErrorDetail, request } from '@/api/client'
import { useSessionStore } from '@/stores/session'
import {
  displayValue,
  type ActionPermission,
  type DriverListPayload,
  type DriverPermission,
  type DriverRow,
  type FieldPermission,
} from '@/views/driver/shared'

const ENDPOINT = '/api/driver'
const statuses = ['待上岗', '在岗', '休息中', '已离职']
const requiredFields = ['司机工号', '司机姓名', '联系电话']

const session = useSessionStore()
const router = useRouter()

const rows = ref<DriverRow[]>([])
const total = ref(0)
const errorMessage = ref('')
const keyword = ref('')
const statusFilter = ref('')
const permission = ref<DriverPermission | null>(null)

const creating = ref(false)
const submitting = ref(false)
const formError = ref('')
const createForm = ref<Record<string, string>>({})

const visibleColumns = computed<FieldPermission[]>(() => permission.value?.fields ?? [])
const writeActions = computed<ActionPermission[]>(() => permission.value?.actions ?? [])
const formFields = computed<FieldPermission[]>(
  () => permission.value?.fields.filter((field) => field.mode === 'editable') ?? [],
)
const noWriteHint = computed(
  () =>
    `当前岗位「${permission.value?.roleLabel ?? ''}」只有查看权限，司机登记与上岗安排请联系运营管理员`,
)

const stats = computed(() => {
  const onDuty = rows.value.filter((row) => row.status === '在岗').length
  const resting = rows.value.filter((row) => row.status === '休息中').length
  return [
    { label: '在岗司机', value: onDuty },
    { label: '休息司机', value: resting },
    { label: '证照即将到期', value: 0 },
  ]
})

function resetFilters() {
  keyword.value = ''
  statusFilter.value = ''
  void reload()
}

function openDetail(row: DriverRow) {
  void router.push(`/driver/${row.id}`)
}

function openCreate() {
  if (!permission.value?.canCreate) {
    // 双保险：按钮已禁用，这里再挡一次并在页脚标明原因
    errorMessage.value = noWriteHint.value
    return
  }
  formError.value = ''
  createForm.value = Object.fromEntries(formFields.value.map((field) => [field.name, '']))
  creating.value = true
}

function closeCreate() {
  creating.value = false
  formError.value = ''
}

async function submitCreate() {
  formError.value = ''
  submitting.value = true
  try {
    const response = await request(ENDPOINT, {
      method: 'POST',
      body: JSON.stringify({ values: createForm.value }),
    })
    const payload = (await response.json()) as { ok?: boolean; message?: string }
    if (!response.ok) {
      throw new Error(await readErrorDetail(response, '司机档案登记未生效，请稍后重试'))
    }
    if (payload.ok === false) {
      throw new Error(payload.message || '司机档案登记未生效')
    }
    creating.value = false
    await reload()
  } catch (error) {
    formError.value = error instanceof Error ? error.message : '司机档案登记失败'
  } finally {
    submitting.value = false
  }
}

async function exportRows() {
  errorMessage.value = ''
  try {
    // 走统一请求头：导出同样按岗位裁剪敏感字段，window.open 无法携带岗位头
    const response = await request(`${ENDPOINT}/export`)
    if (!response.ok) {
      throw new Error(await readErrorDetail(response, '司机管理清单导出失败'))
    }
    const blob = await response.blob()
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `司机管理清单-${permission.value?.roleLabel ?? ''}.json`
    link.click()
    window.URL.revokeObjectURL(url)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '司机管理清单导出失败'
  }
}

async function runAction(action: string, row: DriverRow) {
  errorMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/${row.id}/actions`, {
      method: 'POST',
      body: JSON.stringify({ action }),
    })
    if (!response.ok) {
      // 越权提交被后端挡下时，把原因原样展示在页面上
      throw new Error(await readErrorDetail(response, '司机管理动作未生效，请稍后重试'))
    }
    const payload = (await response.json()) as { ok?: boolean; message?: string }
    if (payload.ok === false) {
      throw new Error(payload.message || '司机管理动作未生效')
    }
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '司机管理操作失败'
  }
}

async function reload() {
  errorMessage.value = ''
  const query = new URLSearchParams()
  if (keyword.value.trim()) {
    query.set('keyword', keyword.value.trim())
  }
  if (statusFilter.value) {
    query.set('status', statusFilter.value)
  }
  try {
    const response = await request(`${ENDPOINT}?${query.toString()}`)
    if (!response.ok) {
      throw new Error(await readErrorDetail(response, '司机档案列表读取失败'))
    }
    const payload = (await response.json()) as DriverListPayload
    rows.value = payload.items ?? []
    total.value = payload.total ?? rows.value.length
    permission.value = payload.permission ?? null
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '司机管理列表读取失败'
  }
}

// 岗位调整后无需手工刷新：按新归属重新拉取列表与字段权限
watch(
  () => session.role,
  () => {
    void reload()
  },
)

onMounted(reload)
</script>

<style scoped>
.page-actions {
  display: flex;
  gap: 8px;
}
.btn:disabled,
.link:disabled {
  color: #9aa6b2;
  cursor: not-allowed;
}
.permission-banner {
  display: flex;
  gap: 10px;
  align-items: center;
  border: 1px solid var(--border);
  border-left-width: 4px;
  border-radius: 6px;
  background: #fff;
  padding: 8px 12px;
  margin-bottom: 12px;
  font-size: 12px;
  color: var(--muted);
}
.permission-banner.ops_admin {
  border-left-color: #16a34a;
}
.permission-banner.dispatcher,
.permission-banner.other {
  border-left-color: #d97706;
}
.permission-role {
  font-weight: 600;
  color: #1f2937;
  white-space: nowrap;
}
.lock-mark {
  font-size: 11px;
}
.cell-hidden {
  color: #9aa6b2;
  background: #f1f5f9;
}
.filter-item select,
.filter-item input {
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 4px 8px;
  font-size: 13px;
}
.required-mark {
  color: #b42318;
  font-style: normal;
}
.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 20;
}
.modal-card {
  background: #fff;
  border-radius: 10px;
  width: 520px;
  max-width: calc(100vw - 32px);
  padding: 18px 20px;
}
.modal-card h3 {
  margin: 0 0 12px;
}
.modal-form {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px 14px;
}
.modal-form .filter-item span {
  display: block;
  margin-bottom: 4px;
}
.modal-form .filter-item input {
  width: 100%;
}
.modal-form .error-text {
  grid-column: 1 / -1;
  margin: 0;
}
.modal-actions {
  grid-column: 1 / -1;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
