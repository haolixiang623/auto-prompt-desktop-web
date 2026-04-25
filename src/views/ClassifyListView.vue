<template>
  <WorkspaceListView
    title="材料自动分类"
    subtitle="历史分类工作区列表，点击打开或新增分类任务"
    createRoute="/classify/new"
    createLabel="新增分类任务"
    iconBgClass="bg-indigo-100"
    iconClass="text-indigo-600"
    iconPath="M7 7h10M7 12h6m-6 5h10M5 3h14a2 2 0 012 2v14a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2z"
    module="classify"
    :showDownload="true"
    downloadLabel="下载结果ZIP"
    @open="handleOpen"
    @download="handleDownload"
  />
</template>

<script setup>
import { useRouter } from 'vue-router'
import WorkspaceListView from './WorkspaceListView.vue'
import { apiClient } from '../services/apiClient.js'

const router = useRouter()

function handleOpen(ws) {
  router.push({ path: '/classify/new', query: { workDir: ws.rootPath } })
}

function handleDownload(ws) {
  if (!ws?.rootPath) return
  apiClient.open('/api/classify/download-result', { workDir: ws.rootPath })
}
</script>
