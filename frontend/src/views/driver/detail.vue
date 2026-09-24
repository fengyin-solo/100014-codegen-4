<template>
  <section class="page" data-module="driver-detail">
    <header class="page-head">
      <div>
        <h2>司机档案详情</h2>
        <p class="page-desc">字段范围与司机列表页保持一致：无权限字段只读展示，不暴露敏感信息。</p>
      </div>
      <div class="page-actions">
        <button class="btn" type="button" @click="goBack">返回列表</button>
      </div>
    </header>

    <div v-if="permission" class="permission-banner" :class="permission.role">
      <span class="permission-role">当前岗位：{{ permission.roleLabel }}</span>
      <span>{{ permission.notice }}</span>
    </div>

    <div v-if="errorMessage" class="error-panel">
      <p class="error-text">{{ errorMessage }}</p>
      <button class="btn" type="button" @click="goBack">返回司机列表</button>
    </div>

    <template v-else-if="entry && permission">
      <div class="detail-card">
        <dl
          v-for="field in permission.fields"
          :key="field.name"
          class="detail-field"
          :class="{ 'is-hidden': field.mode === 'hidden' }"
        >
          <dt>
            {{ field.name }}
            <span v-if="field.sensitive" class="sensitive-tag" title="敏感字段，按岗位控制可见性">敏感</span>
            <span v-if="field.mode === 'hidden'" class="lock-mark">🔒 只读</span>
          </dt>
          <dd>
            <!-- 无权限时一律只读：用 disabled 输入框，避免看起来可改、提交才失败 -->
            <input
              :value="displayValue(entry, field, permission.hiddenPlaceholder)"
              type="text"
              readonly
              disabled
            />
          </dd>
        </dl>
      </div>

      <div class="action-bar">
        <button
          v-for="action in permission.actions"
          :key="action.name"
          class="btn"
          :class="{ primary: action.enabled }"
          type="button"
          :disabled="!action.enabled"
          :title="!action.enabled ? noWriteHint : ''"
          @click="runAction(action.name)"
        >
          {{ action.name }}
        </button>
      </div>
      <footer class="page-foot">
        <span v-if="actionMessage" :class="actionOk ? 'ok-text' : 'error-text'">{{ actionMessage }}</span>
      </footer>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { readErrorDetail, request } from '@/api/client'
import { useSessionStore } from '@/stores/session'
import {
  displayValue,
  type DriverDetailPayload,
  type DriverPermission,
  type DriverRow,
} from '@/views/driver/shared'

const route = useRoute()
const router = useRouter()
const session = useSessionStore()

const entry = ref<DriverRow | null>(null)
const permission = ref<DriverPermission | null>(null)
const errorMessage = ref('')
const actionMessage = ref('')
const actionOk = ref(false)

const entryId = computed(() => Number(route.params.id))
const noWriteHint = computed(
  () =>
    `当前岗位「${permission.value?.roleLabel ?? ''}」只有查看权限，司机上岗安排请联系运营管理员`,
)

function goBack() {
  void router.push('/driver')
}

async function runAction(action: string) {
  actionMessage.value = ''
  try {
    const response = await request(`/api/driver/${entryId.value}/actions`, {
      method: 'POST',
      body: JSON.stringify({ action }),
    })
    if (!response.ok) {
      throw new Error(await readErrorDetail(response, '司机管理动作未生效，请稍后重试'))
    }
    const payload = (await response.json()) as { ok?: boolean; message?: string }
    if (payload.ok === false) {
      throw new Error(payload.message || '司机管理动作未生效')
    }
    actionOk.value = true
    actionMessage.value = payload.message || '操作已生效'
    await load()
  } catch (error) {
    actionOk.value = false
    actionMessage.value = error instanceof Error ? error.message : '司机管理操作失败'
  }
}

async function load() {
  errorMessage.value = ''
  actionMessage.value = ''
  try {
    const response = await request(`/api/driver/${entryId.value}`)
    if (!response.ok) {
      throw new Error(await readErrorDetail(response, '司机档案详情读取失败'))
    }
    const payload = (await response.json()) as DriverDetailPayload
    entry.value = payload.entry
    permission.value = payload.permission
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '司机档案详情读取失败'
  }
}

watch(
  () => session.role,
  () => {
    void load()
  },
)

onMounted(load)
</script>

<style scoped>
.page-actions {
  display: flex;
  gap: 8px;
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
.error-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
  align-items: flex-start;
  background: #fff;
  border: 1px solid #f0b6ae;
  border-radius: 8px;
  padding: 14px;
}
.detail-card {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px 16px;
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px;
}
.detail-field {
  margin: 0;
}
.detail-field dt {
  font-size: 12px;
  color: var(--muted);
  margin-bottom: 4px;
}
.detail-field dd {
  margin: 0;
}
.detail-field input {
  width: 100%;
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 6px 8px;
  font-size: 13px;
  background: #fff;
  color: #1f2937;
}
.detail-field.is-hidden {
  opacity: 0.85;
}
.detail-field.is-hidden input {
  background: #f1f5f9;
  color: #9aa6b2;
}
.sensitive-tag {
  display: inline-block;
  margin-left: 4px;
  font-size: 11px;
  color: #b42318;
  border: 1px solid #f0b6ae;
  border-radius: 4px;
  padding: 0 4px;
}
.lock-mark {
  margin-left: 4px;
  font-size: 11px;
  color: #9aa6b2;
}
.action-bar {
  display: flex;
  gap: 8px;
  margin-top: 14px;
}
.btn:disabled {
  color: #9aa6b2;
  cursor: not-allowed;
}
.ok-text {
  color: #16a34a;
}
</style>
