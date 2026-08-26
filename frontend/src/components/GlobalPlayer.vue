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
  background: #111215;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
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
  color: #f0f1f3;
  font-size: 14px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.artist {
  color: #858a96;
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
  color: #c9cbd2;
  font-size: 20px;
  cursor: pointer;
}
.controls button:hover {
  color: #59e2a4;
}
.play-btn {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #59e2a4 !important;
  color: #07110c !important;
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
  accent-color: #59e2a4;
}
.time {
  color: #858a96;
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
  accent-color: #59e2a4;
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
