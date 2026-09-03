<!-- 固定播放器：只展示当前歌曲，进度与音量操作统一写入 Pinia。 -->
<template>
  <div v-if="player.currentSong" class="player-bar" aria-label="当前播放器">
    <router-link class="song-info" :to="`/songs/${player.currentSong.id}`">
      <span class="cover" aria-hidden="true">{{ player.currentSong.title.slice(0, 1) }}</span>
      <span class="song-copy">
        <strong>{{ player.currentSong.title }}</strong>
        <small>{{ player.currentSong.artist.name }}</small>
      </span>
    </router-link>

    <div class="transport">
      <div class="controls">
        <button type="button" aria-label="上一首" @click="player.playPrev">‹</button>
        <button
          class="play-button"
          type="button"
          :aria-label="player.playing ? '暂停' : '播放'"
          @click="player.togglePlay"
        >
          {{ player.playing ? 'Ⅱ' : '▶' }}
        </button>
        <button type="button" aria-label="下一首" @click="player.playNext">›</button>
      </div>
      <div class="progress">
        <span>{{ formatTime(player.currentTime) }}</span>
        <input
          aria-label="播放进度"
          type="range"
          min="0"
          :max="player.duration || 0"
          :value="player.currentTime"
          @input="(event) => player.seek(Number((event.target as HTMLInputElement).value))"
        />
        <span>{{ formatTime(player.duration) }}</span>
      </div>
    </div>

    <div class="volume">
      <span aria-hidden="true">⌁</span>
      <input
        aria-label="音量"
        type="range"
        min="0"
        max="1"
        step="0.01"
        :value="player.volume"
        @input="(event) => player.setVolume(Number((event.target as HTMLInputElement).value))"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { usePlayerStore } from '../stores/player'

const player = usePlayerStore()

// 将秒数格式化为播放器常用的分:秒。
function formatTime(seconds: number): string {
  if (!seconds || Number.isNaN(seconds)) return '0:00'
  const minutes = Math.floor(seconds / 60)
  const remainder = Math.floor(seconds % 60)
    .toString()
    .padStart(2, '0')
  return `${minutes}:${remainder}`
}
</script>

<style scoped>
.player-bar {
  position: fixed;
  right: 0;
  bottom: 0;
  left: 244px;
  z-index: 1000;
  display: grid;
  min-height: 78px;
  grid-template-columns: minmax(180px, 0.8fr) minmax(320px, 1.5fr) minmax(100px, 0.45fr);
  align-items: center;
  gap: 24px;
  padding: 10px clamp(18px, 3vw, 38px);
  border-top: 1px solid var(--border-strong);
  background: linear-gradient(100deg, rgba(36, 53, 80, 0.97), rgba(25, 36, 60, 0.98));
  box-shadow: 0 -14px 45px rgba(4, 10, 24, 0.28);
  backdrop-filter: blur(24px);
}

.song-info {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 12px;
  color: inherit;
  text-decoration: none;
}

.cover {
  display: grid;
  width: 48px;
  height: 48px;
  flex-shrink: 0;
  place-items: center;
  border: 1px solid rgba(255, 255, 255, 0.16);
  border-radius: 13px;
  color: #0b1d24;
  background: linear-gradient(145deg, var(--accent), var(--accent-blue));
  box-shadow: 0 9px 24px rgba(22, 186, 165, 0.18);
  font-size: 17px;
  font-weight: 800;
}

.song-copy {
  min-width: 0;
}

.song-copy strong,
.song-copy small {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.song-copy strong {
  color: var(--text);
  font-size: 13px;
}

.song-copy small {
  margin-top: 4px;
  color: var(--text-muted);
  font-size: 11px;
}

.transport {
  min-width: 0;
}

.controls {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
}

.controls button {
  display: grid;
  width: 30px;
  height: 30px;
  place-items: center;
  border: 0;
  border-radius: 50%;
  color: var(--text-secondary);
  background: transparent;
  cursor: pointer;
  font-size: 23px;
}

.controls button:hover {
  color: var(--accent);
  background: var(--accent-soft);
}

.controls .play-button {
  width: 38px;
  height: 38px;
  color: var(--text-on-accent);
  background: var(--accent);
  box-shadow: 0 8px 22px rgba(22, 186, 165, 0.22);
  font-size: 12px;
}

.controls .play-button:hover {
  color: var(--text-on-accent);
  background: var(--accent-strong);
  transform: scale(1.04);
}

.progress {
  display: flex;
  align-items: center;
  gap: 9px;
}

.progress span {
  width: 34px;
  color: var(--text-muted);
  font-size: 10px;
  font-variant-numeric: tabular-nums;
}

.progress span:last-child {
  text-align: right;
}

input[type='range'] {
  height: 3px;
  flex: 1;
  accent-color: var(--accent);
  cursor: pointer;
}

.volume {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  color: var(--text-muted);
}

.volume input {
  width: min(90px, 8vw);
}

@media (max-width: 800px) {
  .player-bar {
    left: 0;
    min-height: 100px;
    grid-template-columns: minmax(120px, 1fr) auto;
    gap: 10px 16px;
    padding: 10px 16px;
  }

  .transport {
    display: contents;
  }

  .controls {
    justify-content: flex-end;
  }

  .progress {
    grid-column: 1 / -1;
    grid-row: 2;
  }

  .volume {
    display: none;
  }

  .cover {
    width: 42px;
    height: 42px;
  }
}
</style>
