<template>
  <div class="app-shell">
    <aside class="app-side">
      <h1 class="app-title">冷链物流温控运营平台</h1>
      <nav class="nav-list">
        <RouterLink v-for="item in navItems" :key="item.path" :to="item.path" class="nav-item">
          {{ item.label }}
        </RouterLink>
      </nav>
    </aside>
    <main class="app-main">
      <header class="app-head">
        <span class="head-desc">面向冷链订单、运单、冷藏车、温控监控、冷库仓储与结算的一体化运营后台。</span>
        <span class="head-user">
          当前值班：{{ store.operator }} · {{ store.shiftLabel }}
          <label class="role-switch">
            岗位
            <select :value="store.role" @change="changeRole">
              <option v-for="item in roleOptions" :key="item.code" :value="item.code">
                {{ item.label }}
              </option>
            </select>
          </label>
        </span>
      </header>
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
import { ROLE_OPTIONS, useSessionStore, type RoleCode } from '@/stores/session'

const store = useSessionStore()
const roleOptions = ROLE_OPTIONS

function changeRole(event: Event) {
  // 切换后写入本地存储；页面重新拉取权限，重新进入仍按新归属生效
  store.setRole((event.target as HTMLSelectElement).value as RoleCode)
}

const navItems = [{ label: "运营概览", path: "/" }, { label: "冷链订单", path: "/order" }, { label: "运单管理", path: "/waybill" }, { label: "冷藏车管理", path: "/vehicle" }, { label: "司机管理", path: "/driver" }, { label: "温控监控", path: "/temperature" }, { label: "温度异常", path: "/excursion" }, { label: "冷库管理", path: "/warehouse" }, { label: "入库管理", path: "/inbound" }, { label: "出库管理", path: "/outbound" }, { label: "库存管理", path: "/inventory" }, { label: "批次追溯", path: "/trace" }, { label: "质检管理", path: "/quality" }, { label: "线路管理", path: "/route" }, { label: "调度派单", path: "/dispatch" }, { label: "温控设备", path: "/device" }, { label: "维保工单", path: "/maint" }, { label: "告警中心", path: "/alarm" }, { label: "客户管理", path: "/customer" }, { label: "计费结算", path: "/billing" }, { label: "报表导出", path: "/report" }, { label: "系统设置", path: "/setting" }]
</script>

<style scoped>
.role-switch {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-left: 12px;
}
.role-switch select {
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 2px 4px;
  font-size: 12px;
}
</style>
