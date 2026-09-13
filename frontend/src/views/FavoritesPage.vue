<!-- 收藏页面：加载用户收藏并复用信息列表进行查看或取消收藏。 -->
<template>
  <section class="fav-page">
    <PageHeader
      eyebrow="FAVORITES"
      title="我的收藏"
      subtitle="把打动你的声音留在这里，随时回来重温"
    />
    <div v-if="loading" class="state-surface page-surface">
      <StatePanel type="loading" title="正在加载收藏" />
    </div>
    <div v-else-if="loadFailed" class="state-surface page-surface">
      <StatePanel type="error" title="收藏加载失败" message="服务暂时不可用，请稍后重新加载">
        <template #action><el-button type="primary" @click="load">重新加载</el-button></template>
      </StatePanel>
    </div>
    <div v-else-if="favSongs.length === 0" class="state-surface page-surface">
      <StatePanel title="还没有收藏任何歌曲" message="在歌曲详情页点击收藏即可添加">
        <template #action
          ><router-link class="browse-link" to="/songs">浏览音乐库</router-link></template
        >
      </StatePanel>
    </div>
    <SongList v-else :songs="favSongs" variant="favorites" @remove="remove" />
  </section>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { listFavorites, removeFavorite } from '../api/favorites'
import { getSong, type SongDetail } from '../api/songs'
import { showError, showSuccess } from '../utils/feedback'
import PageHeader from '../components/PageHeader.vue'
import StatePanel from '../components/StatePanel.vue'
import SongList from '../components/SongList.vue'
const favSongs = ref<SongDetail[]>([])
const loading = ref(false)
const loadFailed = ref(false)
// 先取收藏 ID，再并发加载歌曲详情；单条歌曲失效不影响其他收藏。
async function load() {
  loading.value = true
  loadFailed.value = false
  try {
    const { data } = await listFavorites()
    const songs = await Promise.all(
      data.items.map((i) =>
        getSong(i.song_id)
          .then((r) => r.data)
          .catch(() => null),
      ),
    )
    favSongs.value = songs.filter((s): s is SongDetail => s !== null)
  } catch (error) {
    favSongs.value = []
    loadFailed.value = true
    showError(error, '收藏加载失败')
  } finally {
    loading.value = false
  }
}
// 删除收藏并同步更新本地列表，避免等待再次查询。
async function remove(id: number) {
  try {
    await removeFavorite(id)
    favSongs.value = favSongs.value.filter((s) => s.id !== id)
    showSuccess('已取消收藏')
  } catch (error) {
    showError(error, '取消收藏失败')
  }
}
onMounted(load)
</script>
<style scoped>
.fav-page {
  padding: var(--page-gutter);
}
.state-surface {
  min-height: 330px;
}
.browse-link {
  display: inline-flex;
  min-height: 38px;
  align-items: center;
  padding: 0 16px;
  border-radius: 10px;
  color: var(--text-on-accent);
  background: var(--accent);
  font-size: 12px;
  font-weight: 700;
  text-decoration: none;
}
</style>
