<template>
  <div v-if="player.currentSong" class="player-bar">
    <div class="song-info">
      <span class="title">{{ player.currentSong.title }}</span>
      <span class="artist">{{ player.currentSong.artist.name }}</span>
    </div>
    <div class="controls">
      <button @click="player.playPrev">⏮</button>
      <button class="play-btn" @click="player.togglePlay">
        {{ player.playing ? '⏸' : '▶' }}
      </button>
      <button @click="player.playNext">⏭</button>
    </div>
    <div class="progress">
      <span class="time">{{ formatTime(player.currentTime) }}</span>
      <input
        type="range"
        min="0"
        :max="player.duration || 0"
        :value="player.currentTime"
        @input="(e) => player.seek(Number((e.target as HTMLInputElement).value))"
      />
      <span class="time">{{ formatTime(player.duration) }}</span>
    </div>
    <div class="volume">
      <span>🔊</span>
      <input
        type="range"
        min="0"
        max="1"
        step="0.01"
        :value="player.volume"
        @input="(e) => player.setVolume(Number((e.target as HTMLInputElement).value))"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { usePlayerStore } from '../stores/player'
const player = usePlayerStore()
function formatTime(s: number) {
  if (!s || isNaN(s)) return '0:00'
  const m = Math.floor(s / 60)
  const sec = Math.floor(s % 60)
    .toString()
    .padStart(2, '0')
  return `${m}:${sec}`
}
</script>

<style scoped>
.player-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 64px;
  background: linear-gradient(90deg, var(--surface-raised), var(--bg-elevated));
  border-top: 1px solid var(--border-strong);
  box-shadow: var(--shadow);
  display: flex;
  align-items: center;
  padding: 0 20px;
  gap: 20px;
  z-index: 1000;
}
.song-info {
  width: 200px;
  display: flex;
  flex-direction: column;
}
.title {
  color: var(--text);
  font-size: 14px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.artist {
  color: var(--text-secondary);
  font-size: 12px;
}
.controls {
  display: flex;
  align-items: center;
  gap: 12px;
}
.controls button {
  background: none;
  border: none;
  color: var(--text-secondary);
  font-size: 20px;
  cursor: pointer;
}
.controls button:hover {
  color: var(--accent);
}
.play-btn {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--accent) !important;
  color: var(--text-on-accent) !important;
  font-size: 16px !important;
  display: grid;
  place-items: center;
}
.progress {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 10px;
}
.progress input[type='range'] {
  flex: 1;
  accent-color: var(--accent);
}
.time {
  color: var(--text-secondary);
  font-size: 12px;
  width: 40px;
}
.volume {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 120px;
}
.volume input[type='range'] {
  width: 80px;
  accent-color: var(--accent);
}
@media (max-width: 640px) {
  .player-bar {
    flex-wrap: wrap;
    height: auto;
    padding: 12px 16px;
    gap: 10px;
  }
  .song-info {
    width: 100%;
  }
  .progress {
    order: 3;
    flex-basis: 100%;
  }
  .volume {
    display: none;
  }
}
</style>
