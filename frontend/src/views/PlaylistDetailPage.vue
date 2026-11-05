<!-- 集合详情页：展示集合信息并复用信息列表查看条目。 -->
<template>
  <section v-if="playlist" class="detail-page">
    <!-- 返回入口统一用 BackLink：造型与搜索框一致，且没有历史时能退回语义父级 -->
    <BackLink label="我的空间" :fallback="{ name: 'playlists' }" />
    <div class="page-header legacy-header">
      <div class="pl-info">
        <h2>{{ playlist.name }}</h2>
        <p class="desc">{{ playlist.description || '还没有添加描述' }}</p>
        <p class="meta">共 {{ playlist.song_count }} 首歌曲</p>
      </div>
    </div>
    <StatePanel
      v-if="playlist.songs.length === 0"
      title="歌单里还没有歌曲"
      message="去内容库收录一些条目吧"
    />
    <SongList v-else :songs="playlist.songs" variant="playlist" />
  </section>
  <section v-else class="detail-page">
    <BackLink label="我的空间" :fallback="{ name: 'playlists' }" />
    <div class="state-surface page-surface">
      <StatePanel v-if="loading" type="loading" title="正在加载歌单" />
      <StatePanel
        v-else
        type="error"
        title="歌单加载失败"
        message="歌单可能不存在，或你暂时没有访问权限"
      >
        <template #action
          ><el-button type="primary" @click="router.push('/playlists')"
            >返回我的歌单</el-button
          ></template
        >
      </StatePanel>
    </div>
  </section>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getPlaylist } from '../api/playlists'
import type { PlaylistDetail } from '../types/music'
import { showError } from '../utils/feedback'
import BackLink from '../components/BackLink.vue'
import StatePanel from '../components/StatePanel.vue'
import SongList from '../components/SongList.vue'
const route = useRoute()
const router = useRouter()
const playlist = ref<PlaylistDetail | null>(null)
const loading = ref(false)
// 读取歌单详情；失败时保留页面并显示返回/重试入口。
async function load() {
  loading.value = true
  try {
    const { data } = await getPlaylist(Number(route.params.id))
    playlist.value = data
  } catch (error) {
    showError(error, '歌单加载失败')
  } finally {
    loading.value = false
  }
}
onMounted(load)
</script>
<style scoped>
.detail-page {
  padding: var(--page-gutter);
}
.page-header {
  margin-bottom: 20px;
  padding: clamp(20px, 3vw, 28px);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
}
.pl-info h2 {
  color: var(--text);
  font-size: clamp(22px, 3vw, 28px);
  font-weight: 600;
  letter-spacing: -0.01em;
  margin: 0 0 6px;
}
.desc {
  color: var(--text-secondary);
  font-size: var(--fs-sm);
  margin: 0;
}
.meta {
  color: var(--text-muted);
  font-size: var(--fs-xs);
  margin: 12px 0 0;
}
.state-surface {
  min-height: 360px;
}
</style>
