<template>
  <section class="page" data-module="driver-detail">
    <header class="page-head">
      <div>
        <h2>司机档案详情</h2>
        <p class="page-desc">展示单条司机档案。字段范围与司机列表一致，随当前岗位归属变化。</p>
      </div>
      <div class="page-actions">
        <RouterLink class="btn" to="/driver">返回列表</RouterLink>
      </div>
    </header>

    <p v-if="policy && !policy.can_run_actions" class="notice-bar">{{ policy.denied_reason }}</p>

    <div v-if="entry" class="detail-list">
      <div v-for="field in fields" :key="field" class="detail-row">
        <span class="detail-label">{{ field }}</span>
        <span class="detail-value">{{ entry[field] ?? '—' }}</span>
      </div>
      <div class="detail-row">
        <span class="detail-label">当前状态</span>
        <span class="detail-value">{{ entry.status ?? '—' }}</span>
      </div>
    </div>

    <div v-if="entry && policy?.can_run_actions" class="page-actions" style="margin-top: 12px;">
      <button
        v-for="action in actions"
        :key="action"
        class="btn"
        type="button"
        @click="runAction(action)"
      >
        {{ action }}
      </button>
    </div>

    <footer class="page-foot">
      <span>当前岗位：{{ policy?.role_name ?? '加载中' }}</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

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

const route = useRoute()
const policy = ref<DriverPolicy | null>(null)
const entry = ref<Row | null>(null)
const errorMessage = ref('')

// 与列表页完全相同的字段口径，均来自后端 /me 的 visible_fields
const fields = computed(() => policy.value?.visible_fields ?? [])
const actions = computed(() => (policy.value?.can_run_actions ? ALL_ACTIONS : []))

async function runAction(action: string) {
  errorMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/${route.params.id}/actions`, {
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
    await loadEntry()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '司机管理操作失败'
  }
}

async function loadEntry() {
  const response = await request(`${ENDPOINT}/${route.params.id}`)
  if (!response.ok) {
    throw new Error(await readErrorDetail(response, '司机档案读取失败'))
  }
  entry.value = (await response.json()) as Row
}

onMounted(async () => {
  try {
    const meResponse = await request(`${ENDPOINT}/me`)
    if (!meResponse.ok) {
      throw new Error('当前岗位权限读取失败')
    }
    policy.value = (await meResponse.json()) as DriverPolicy
    await loadEntry()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '司机详情加载失败'
  }
})
</script>
