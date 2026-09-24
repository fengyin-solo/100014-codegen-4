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
          :disabled="!policy?.can_create"
          :title="policy?.can_create ? '' : policy?.denied_reason"
          @click="openCreate"
        >
          登记司机档案
        </button>
        <button class="btn" type="button" @click="exportRows">导出司机管理清单</button>
      </div>
    </header>

    <p v-if="policy && !policy.can_create" class="notice-bar">{{ policy.denied_reason }}</p>

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
        <span>在途状态</span>
        <select v-model="statusFilter">
          <option value="">全部状态</option>
          <option v-for="item in statuses" :key="item" :value="item">{{ item }}</option>
        </select>
      </label>
      <button class="btn" type="submit">查询</button>
      <button class="btn ghost" type="button" @click="resetFilters">重置条件</button>
    </form>

    <table class="data-table">
      <thead>
        <tr>
          <th v-for="column in columns" :key="column">{{ column }}</th>
          <th v-if="policy?.can_run_actions">可执行动作</th>
          <th>档案</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="String(row.id)">
          <td v-for="column in columns" :key="column">{{ row[column] ?? '—' }}</td>
          <td v-if="policy?.can_run_actions" class="row-actions">
            <button
              v-for="action in actions"
              :key="action"
              class="link"
              type="button"
              @click="runAction(action, row)"
            >
              {{ action }}
            </button>
          </td>
          <td>
            <RouterLink class="link" :to="`/driver/${row.id}`">查看详情</RouterLink>
          </td>
        </tr>
        <tr v-if="!rows.length">
          <td :colspan="columns.length + (policy?.can_run_actions ? 2 : 1)" class="empty-state">暂无司机管理数据</td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>共 {{ total }} 条司机管理记录 · 当前岗位：{{ policy?.role_name ?? '加载中' }}</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>

    <div v-if="showCreate" class="modal-mask" @click.self="showCreate = false">
      <form class="modal" @submit.prevent="submitCreate">
        <h3>登记司机档案</h3>
        <label v-for="field in createFields" :key="field" class="form-item">
          <span>{{ field }}<em v-if="requiredFields.includes(field)">*</em></span>
          <input v-model="createForm[field]" :placeholder="`请输入${field}`" />
        </label>
        <p v-if="createError" class="error-text">{{ createError }}</p>
        <div class="modal-foot">
          <button class="btn ghost" type="button" @click="showCreate = false">取消</button>
          <button class="btn primary" type="submit">提交登记</button>
        </div>
      </form>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { readErrorDetail, request } from '@/api/client'

type Row = Record<string, string | number | null>

interface DriverPolicy {
  role: string
  role_name: string
  can_create: boolean
  can_run_actions: boolean
  visible_fields: string[]
  denied_reason: string
}

const ENDPOINT = '/api/driver'
const ALL_ACTIONS = ['安排上岗', '排班休息', '办理离职']
const statuses = ['待上岗', '在岗', '休息中', '已离职']

const policy = ref<DriverPolicy | null>(null)
const rows = ref<Row[]>([])
const total = ref(0)
const errorMessage = ref('')
const keyword = ref('')
const statusFilter = ref('')

const columns = computed(() => policy.value?.visible_fields ?? [])
const actions = computed(() => (policy.value?.can_run_actions ? ALL_ACTIONS : []))
const stats = computed(() => [
  { label: '在岗司机', value: rows.value.filter((row) => row.status === '在岗').length },
  { label: '休息司机', value: rows.value.filter((row) => row.status === '休息中').length },
  { label: '记录总数', value: total.value },
])

// 登记表单：必填字段以后端要求为准；运营管理员可见全部字段，可一并填写
const requiredFields = ['司机工号', '司机姓名', '联系电话']
const createFields = computed(() => policy.value?.visible_fields ?? requiredFields)
const showCreate = ref(false)
const createForm = ref<Record<string, string>>({})
const createError = ref('')

function resetFilters() {
  keyword.value = ''
  statusFilter.value = ''
  void reload()
}

function exportRows() {
  // 导出接口同样按岗位裁剪字段，敏感信息不会因导出外泄
  window.open(`${ENDPOINT}/export`, '_blank')
}

function openCreate() {
  if (!policy.value?.can_create) {
    errorMessage.value = policy.value?.denied_reason ?? '当前岗位无权登记司机档案'
    return
  }
  createError.value = ''
  createForm.value = {}
  showCreate.value = true
}

async function submitCreate() {
  createError.value = ''
  try {
    const response = await request(ENDPOINT, {
      method: 'POST',
      body: JSON.stringify({ values: createForm.value }),
    })
    const payload = (await response.json()) as { ok: boolean; message: string }
    if (!response.ok || !payload.ok) {
      throw new Error(payload.message || '司机档案登记未生效')
    }
    showCreate.value = false
    await reload()
  } catch (error) {
    createError.value = error instanceof Error ? error.message : '司机档案登记失败'
  }
}

async function runAction(action: string, row: Row) {
  errorMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/${row.id}/actions`, {
      method: 'POST',
      body: JSON.stringify({ values: { action } }),
    })
    if (!response.ok) {
      throw new Error(await readErrorDetail(response, '司机管理动作未生效，请稍后重试'))
    }
    const payload = (await response.json()) as { ok: boolean; message: string }
    if (!payload.ok) {
      throw new Error(payload.message)
    }
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '司机管理操作失败'
  }
}

async function loadPolicy() {
  const response = await request(`${ENDPOINT}/me`)
  if (!response.ok) {
    throw new Error('当前岗位权限读取失败')
  }
  policy.value = (await response.json()) as DriverPolicy
}

async function reload() {
  errorMessage.value = ''
  const params = new URLSearchParams()
  if (keyword.value) params.set('keyword', keyword.value)
  if (statusFilter.value) params.set('status', statusFilter.value)
  try {
    const response = await request(`${ENDPOINT}?${params.toString()}`)
    if (!response.ok) {
      throw new Error(await readErrorDetail(response, '司机档案列表读取失败'))
    }
    const payload = await response.json()
    rows.value = payload.items ?? []
    total.value = payload.total ?? rows.value.length
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '司机管理列表读取失败'
  }
}

onMounted(async () => {
  try {
    await loadPolicy()
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '司机管理页面加载失败'
  }
})
</script>
