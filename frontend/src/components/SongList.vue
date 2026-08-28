<template>
  <div class="song-list" :class="`variant-${variant}`">
    <div class="song-row header">
      <span>标题</span><span>歌手</span><span>{{ variant === 'playlist' ? '时长' : '风格' }}</span>
      <span v-if="variant === 'catalog'">BPM</span>
      <span v-if="variant === 'catalog'">Energy</span>
      <span v-if="variant === 'catalog'">Valence</span>
      <span v-if="variant === 'search'">BPM</span>
      <span></span><span v-if="variant === 'favorites'"></span>
    </div>
    <div
      v-for="song in songs"
      :key="song.id"
      class="song-row"
      role="button"
      tabindex="0"
      @click="emit('play', song)"
      @keydown.enter="emit('play', song)"
    >
      <span class="title">{{ song.title }}</span>
      <span class="artist">{{ song.artist.name }}</span>
      <span v-if="variant === 'playlist'" class="muted">{{ formatDuration(song.duration) }}</span>
      <span v-else class="muted">{{ song.genre || '-' }}</span>
      <span v-if="variant === 'catalog' || variant === 'search'" class="muted">
        {{ song.bpm ? Math.round(song.bpm) : '-' }}
      </span>
      <span v-if="variant === 'catalog'" class="muted">
        {{ song.energy !== null ? `${(song.energy * 100).toFixed(0)}%` : '-' }}
      </span>
      <span v-if="variant === 'catalog'" class="muted">
        {{ song.valence !== null ? `${(song.valence * 100).toFixed(0)}%` : '-' }}
      </span>
      <button class="play-btn" type="button" aria-label="播放歌曲" @click.stop="emit('play', song)">
        ▶
      </button>
      <button
        v-if="variant === 'favorites'"
        class="remove-btn"
        type="button"
        aria-label="取消收藏"
        @click.stop="emit('remove', song.id)"
      >
        ✕
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
  play: [song: SongSummary]
  remove: [songId: number]
}>()

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
  gap: 2px;
}
.song-row {
  display: grid;
  align-items: center;
  padding: 12px 16px;
  border-radius: 8px;
  cursor: pointer;
  background: var(--surface-raised);
  color: var(--text-secondary);
}
.variant-catalog .song-row {
  grid-template-columns: 2fr 1.5fr 1fr 60px 70px 70px 40px;
}
.variant-search .song-row {
  grid-template-columns: 2fr 1.5fr 1fr 60px 40px;
}
.variant-favorites .song-row {
  grid-template-columns: 2fr 1.5fr 1fr 40px 40px;
}
.variant-playlist .song-row {
  grid-template-columns: 2fr 1.5fr 80px 40px;
}
.song-row:hover {
  background: var(--surface-hover);
}
.song-row.header {
  cursor: default;
  background: transparent;
  color: var(--text-muted);
  font-size: 12px;
}
.song-row.header:hover {
  background: transparent;
}
.title {
  overflow: hidden;
  color: var(--text);
  font-size: 14px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.artist,
.muted {
  color: var(--text-secondary);
  font-size: 13px;
}
.play-btn,
.remove-btn {
  display: grid;
  width: 32px;
  height: 32px;
  place-items: center;
  border-radius: 50%;
  cursor: pointer;
}
.play-btn {
  border: 0;
  background: var(--accent);
  color: var(--text-on-accent);
  font-size: 12px;
}
.remove-btn {
  border: 1px solid var(--border-strong);
  background: transparent;
  color: var(--text-secondary);
  font-size: 12px;
}
.remove-btn:hover {
  border-color: var(--danger);
  color: var(--danger);
}
@media (max-width: 720px) {
  .song-row {
    padding: 10px;
  }
  .variant-catalog .song-row {
    grid-template-columns: 2fr 1.3fr 1fr 40px;
  }
  .variant-catalog .song-row > :nth-child(4),
  .variant-catalog .song-row > :nth-child(5),
  .variant-catalog .song-row > :nth-child(6),
  .variant-search .song-row > :nth-child(4) {
    display: none;
  }
  .variant-favorites .song-row {
    grid-template-columns: 2fr 1.3fr 40px 40px;
  }
  .variant-favorites .song-row > :nth-child(3) {
    display: none;
  }
}
</style>
