<template>
  <WorkspaceListView
    title="审查规则生成"
    subtitle="历史工作区列表，点击打开或新增生成审查规则"
    createRoute="/review-rule/new"
    createLabel="新增审查规则生成"
    iconBgClass="bg-green-100"
    iconClass="text-green-600"
    iconPath="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
    module="review-rule"
    @open="handleOpen"
  />
</template>

<script setup>
import { useRouter } from 'vue-router'
import WorkspaceListView from './WorkspaceListView.vue'

const router = useRouter()

function handleOpen(ws) {
  router.push({ path: '/review-rule/new', query: { workDir: ws.rootPath } })
}
</script>
