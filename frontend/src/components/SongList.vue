<!-- 可复用歌曲列表：通过 variant 适配目录、搜索、收藏和歌单场景。 -->
<template>
  <div class="song-list page-surface" :class="`variant-${variant}`">
    <div class="song-row header" aria-hidden="true">
      <span>歌曲</span>
      <span>歌手</span>
      <span>{{ variant === 'playlist' ? '时长' : '风格' }}</span>
      <span v-if="variant === 'catalog'">BPM</span>
      <span v-if="variant === 'catalog'">能量</span>
      <span v-if="variant === 'catalog'">愉悦度</span>
      <span v-if="variant === 'search'">BPM</span>
      <span v-if="variant === 'favorites'"></span>
    </div>
    <div
      v-for="(song, index) in songs"
      :key="song.id"
      class="song-row"
      :aria-label="`查看 ${song.title}，歌手 ${song.artist.name}`"
    >
      <router-link class="track-cell" :to="`/songs/${song.id}`">
        <span class="cover" aria-hidden="true">
          <span class="track-number">{{ String(index + 1).padStart(2, '0') }}</span>
        </span>
        <span class="track-copy">
          <strong>{{ song.title }}</strong>
          <small>{{ song.language || '信息条目' }}</small>
        </span>
      </router-link>
      <span class="artist">{{ song.artist.name }}</span>
      <span v-if="variant === 'playlist'" class="muted">{{ formatDuration(song.duration) }}</span>
      <span v-else class="muted">{{ song.genre || '-' }}</span>
      <span v-if="variant === 'catalog' || variant === 'search'" class="muted numeric">
        {{ song.bpm ? Math.round(song.bpm) : '-' }}
      </span>
      <span v-if="variant === 'catalog'" class="muted numeric">
        {{ song.energy !== null ? `${(song.energy * 100).toFixed(0)}%` : '-' }}
      </span>
      <span v-if="variant === 'catalog'" class="muted numeric">
        {{ song.valence !== null ? `${(song.valence * 100).toFixed(0)}%` : '-' }}
      </span>
      <button
        v-if="variant === 'favorites'"
        class="remove-button"
        type="button"
        :aria-label="`取消收藏 ${song.title}`"
        @click.stop="emit('remove', song.id)"
      >
        ×
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { SongSummary } from '../types/music'

type SongListVariant = 'catalog' | 'search' | 'favorites' | 'playlist'

const { songs, variant = 'catalog' } = defineProps<{
  songs: SongSummary[]
  variant?: SongListVariant
}>()
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
  gap: 3px;
  padding: 8px;
  overflow: hidden;
}

.song-row {
  display: grid;
  min-height: 64px;
  align-items: center;
  padding: 8px 12px;
  border: 1px solid transparent;
  border-radius: 12px;
  color: var(--text-secondary);
  cursor: pointer;
}

.variant-catalog .song-row {
  grid-template-columns:
    minmax(220px, 2fr) minmax(120px, 1.2fr) minmax(90px, 0.8fr)
    64px 68px 68px;
}

.variant-search .song-row {
  grid-template-columns: minmax(220px, 2fr) minmax(130px, 1.2fr) minmax(90px, 0.8fr) 64px;
}

.variant-favorites .song-row {
  grid-template-columns: minmax(220px, 2fr) minmax(130px, 1.2fr) minmax(90px, 0.8fr) 38px;
}

.variant-playlist .song-row {
  grid-template-columns: minmax(220px, 2fr) minmax(130px, 1.2fr) 70px;
}

.song-row:not(.header):hover {
  border-color: var(--border);
  background: linear-gradient(100deg, rgba(110, 231, 210, 0.09), rgba(169, 162, 255, 0.07));
  transform: translateY(-1px);
}

.song-row.header {
  min-height: 38px;
  color: var(--text-muted);
  cursor: default;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
}

.track-cell {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 12px;
  color: inherit;
  text-decoration: none;
}

.cover {
  position: relative;
  display: grid;
  width: 44px;
  height: 44px;
  flex-shrink: 0;
  place-items: center;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 12px;
  color: var(--text-secondary);
  background: linear-gradient(145deg, rgba(110, 231, 210, 0.26), rgba(169, 162, 255, 0.26));
  font-size: 10px;
  font-variant-numeric: tabular-nums;
}

.track-copy {
  min-width: 0;
}

.track-copy strong,
.track-copy small {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.track-copy strong {
  color: var(--text);
  font-size: 13px;
  font-weight: 650;
}

.track-copy small {
  margin-top: 4px;
  color: var(--text-muted);
  font-size: 10px;
}

.artist,
.muted {
  overflow: hidden;
  color: var(--text-secondary);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.numeric {
  font-variant-numeric: tabular-nums;
}

.remove-button {
  display: grid;
  width: 31px;
  height: 31px;
  place-items: center;
  border-radius: 50%;
  cursor: pointer;
}

.remove-button {
  border: 1px solid var(--border);
  color: var(--text-muted);
  background: transparent;
  font-size: 17px;
}

.remove-button:hover {
  border-color: var(--danger);
  color: var(--danger);
  background: rgba(255, 135, 149, 0.08);
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
  .song-list {
    padding: 5px;
  }

  .song-row {
    min-height: 59px;
    padding: 7px 8px;
  }

  .song-row.header {
    display: none;
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

  .cover {
    width: 40px;
    height: 40px;
  }
}
</style>
