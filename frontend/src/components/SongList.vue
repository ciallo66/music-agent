<!-- 可复用歌曲列表：通过 variant 适配目录、搜索、收藏和歌单场景。 -->
<template>
  <div class="song-list page-surface" :class="`variant-${variant}`">
    <div class="song-row header" aria-hidden="true">
      <span>歌曲</span>
      <span>歌手</span>
      <span>{{ variant === 'playlist' ? '时长' : '风格' }}</span>
      <span v-if="variant === 'catalog' || variant === 'search'">节拍 BPM</span>
      <span v-if="variant === 'catalog' || variant === 'search'">时长</span>
      <span
        v-if="variant === 'catalog'"
        title="按 AcousticBrainz 可舞动分类器的判定分档（低/中/高），鼠标悬停看精确分值"
        >律动</span
      >
      <span v-if="variant === 'favorites'"></span>
    </div>
    <div
      v-for="song in songs"
      :key="song.id"
      class="song-row"
      :aria-label="`查看 ${song.title}，歌手 ${song.artist.name}`"
    >
      <router-link class="track-cell" :to="`/songs/${song.id}`">
        <SongCover :song="song" size="sm" />
        <span class="track-copy">
          <strong>{{ song.title }}</strong>
          <small>{{ song.album || (song.music_key ? `${song.music_key} 调` : '特征数据') }}</small>
          <!-- 窄屏下隐藏了歌手/风格/BPM 列，这里补一条合并信息，避免只剩标题 -->
          <span class="track-mobile-meta"
            >{{ song.artist.name }}<template v-if="song.genre"> · {{ song.genre }}</template
            ><template v-if="song.bpm"> · {{ Math.round(song.bpm) }} BPM</template></span
          >
        </span>
      </router-link>
      <span class="artist">{{ song.artist.name }}</span>
      <span v-if="variant === 'playlist'" class="muted">{{ formatDuration(song.duration) }}</span>
      <span v-else class="muted">{{ genreText(song) }}</span>
      <span v-if="variant === 'catalog' || variant === 'search'" class="muted numeric">
        {{ song.bpm ? Math.round(song.bpm) : '-' }}
      </span>
      <span v-if="variant === 'catalog' || variant === 'search'" class="muted numeric">
        {{ song.duration ? formatDuration(song.duration) : '-' }}
      </span>
      <span v-if="variant === 'catalog'" class="muted" :title="danceabilityHint(song.danceability)">
        {{ danceabilityLabel(song.danceability) || '-' }}
      </span>
      <button
        v-if="variant === 'favorites'"
        class="remove-button"
        type="button"
        :aria-label="`取消收藏 ${song.title}`"
        title="取消收藏"
        @click.stop="emit('remove', song.id)"
      >
        <AppIcon name="close" :size="14" />
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { SongSummary } from '../types/music'
import { danceabilityHint, danceabilityLabel } from '../types/music'
import SongCover from './SongCover.vue'
import AppIcon from './AppIcon.vue'
import { fusedGenre } from '../utils/genre'

type SongListVariant = 'catalog' | 'search' | 'favorites' | 'playlist'

const { songs, variant = 'catalog' } = defineProps<{
  songs: SongSummary[]
  variant?: SongListVariant
}>()
// 列表里的流派：多体系投票优先，缺失时回退到库里的单一体系结果。
function genreText(song: SongSummary): string {
  const vote = fusedGenre(song.genre_labels ?? null)
  return vote?.name ?? song.genre ?? '-'
}

const emit = defineEmits<{
  remove: [songId: number]
}>()

// 将歌曲时长格式化为列表展示文本。
function formatDuration(duration: number | null): string {
  if (duration === null) return '-'
  const minutes = Math.floor(duration / 60)
  const seconds = (duration % 60).toString().padStart(2, '0')
  return `${minutes}:${seconds}`
}
</script>

<style scoped>
.song-list {
  display: flex;
  flex-direction: column;
  gap: 0;
  padding: 0;
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
}

.song-row {
  display: grid;
  min-height: 60px;
  align-items: center;
  padding: 8px 14px;
  border-top: 1px solid var(--border);
  color: var(--text-secondary);
}

.song-row.header {
  min-height: 36px;
  border-top: 0;
  color: var(--text-muted);
  cursor: default;
  font-size: var(--fs-xs);
}

.variant-catalog .song-row {
  grid-template-columns:
    minmax(200px, 2fr) minmax(120px, 1.2fr) minmax(84px, 0.8fr)
    62px 78px 58px;
}

.variant-search .song-row {
  grid-template-columns:
    minmax(200px, 2fr) minmax(120px, 1.2fr) minmax(84px, 0.8fr)
    62px 78px;
}

.variant-favorites .song-row {
  grid-template-columns: minmax(220px, 2fr) minmax(130px, 1.2fr) minmax(90px, 0.8fr) 38px;
}

.variant-playlist .song-row {
  grid-template-columns: minmax(220px, 2fr) minmax(130px, 1.2fr) 70px;
}

.song-row:not(.header):hover {
  background: var(--surface-hover);
}

.track-cell {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 12px;
  color: inherit;
  text-decoration: none;
  cursor: pointer;
}

.track-copy {
  min-width: 0;
}

.track-copy strong,
.track-copy small,
.track-mobile-meta {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.track-mobile-meta {
  display: none;
  margin-top: 2px;
  color: var(--text-muted);
  font-size: var(--fs-xs);
}

.track-copy strong {
  color: var(--text);
  font-size: var(--fs-sm);
  font-weight: 500;
}

.track-copy small {
  margin-top: 2px;
  color: var(--text-muted);
  font-size: var(--fs-xs);
}

.artist,
.muted {
  overflow: hidden;
  color: var(--text-secondary);
  font-size: var(--fs-xs);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.numeric {
  font-variant-numeric: tabular-nums;
}

.remove-button {
  display: grid;
  width: 32px;
  height: 32px;
  place-items: center;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  background: transparent;
  cursor: pointer;
}

.remove-button:hover {
  border-color: var(--danger);
  color: var(--danger);
}

@media (max-width: 860px) {
  .variant-catalog .song-row {
    grid-template-columns: minmax(190px, 2fr) minmax(110px, 1fr) minmax(80px, 0.8fr);
  }

  .variant-catalog .song-row > :nth-child(4),
  .variant-catalog .song-row > :nth-child(5),
  .variant-catalog .song-row > :nth-child(6),
  .variant-search .song-row > :nth-child(4) {
    display: none;
  }

  .variant-favorites .song-row {
    grid-template-columns: minmax(180px, 2fr) minmax(100px, 1fr) 38px 38px;
  }

  .variant-favorites .song-row > :nth-child(3) {
    display: none;
  }
}

@media (max-width: 560px) {
  .song-row {
    min-height: 56px;
    padding: 8px 10px;
  }

  .song-row.header {
    display: none;
  }

  .track-copy small {
    display: none;
  }

  .track-mobile-meta {
    display: block;
  }

  .variant-catalog .song-row,
  .variant-search .song-row,
  .variant-playlist .song-row {
    grid-template-columns: minmax(0, 1fr);
  }

  .variant-catalog .song-row > :not(.track-cell),
  .variant-search .song-row > :not(.track-cell),
  .variant-playlist .song-row > :not(.track-cell) {
    display: none;
  }

  .variant-favorites .song-row {
    grid-template-columns: minmax(0, 1fr) 36px;
  }

  .variant-favorites .artist {
    display: none;
  }
}
</style>
