// 全局播放器状态：队列、播放进度、音量和浏览器 Audio 事件。
import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { SongSummary as SongBrief } from '../types/music'
import { recordPlay } from '../api/plays'

// 创建全局播放器状态，确保不同页面操作的是同一音频实例。
export const usePlayerStore = defineStore('player', () => {
  const currentSong = ref<SongBrief | null>(null)
  const queue = ref<SongBrief[]>([])
  const playing = ref(false)
  const audio = ref(new Audio())
  const currentTime = ref(0)
  const duration = ref(0)
  const volume = ref(1)

  // 事件监听集中在 store 内，页面只消费响应式状态，不直接操作 Audio。
  audio.value.addEventListener('timeupdate', () => {
    currentTime.value = audio.value.currentTime
  })
  audio.value.addEventListener('loadedmetadata', () => {
    duration.value = audio.value.duration
  })
  audio.value.addEventListener('ended', () => {
    playing.value = false
    playNext()
  })
  audio.value.addEventListener('play', () => {
    playing.value = true
  })
  audio.value.addEventListener('pause', () => {
    playing.value = false
  })

  // 切换歌曲、重置进度并尝试播放；浏览器拒绝自动播放时保持暂停。
  async function playSong(song: SongBrief): Promise<void> {
    currentSong.value = song
    audio.value.pause()
    audio.value.currentTime = 0
    currentTime.value = 0
    duration.value = song.duration ?? 0
    // 目录歌曲可能只有元数据；保留当前歌曲但不尝试播放空地址。
    if (!song.audio_url) return
    audio.value.src = song.audio_url
    void recordPlay(song.id).catch(() => undefined)
    try {
      await audio.value.play()
    } catch {
      // 浏览器自动播放策略或资源不可用时保持暂停状态，由用户再次点击播放。
      playing.value = false
    }
  }

  // 在当前歌曲上切换播放与暂停。
  function togglePlay() {
    if (!currentSong.value?.audio_url) return
    if (playing.value) {
      audio.value.pause()
    } else {
      void audio.value.play().catch(() => {
        playing.value = false
      })
    }
  }

  // 播放队列中的下一首，队列末尾不循环。
  function playNext() {
    if (!currentSong.value) return
    const idx = queue.value.findIndex((s) => s.id === currentSong.value!.id)
    // 队列到末尾时保持当前歌曲，避免无意循环播放或清空播放器。
    if (idx >= 0 && idx < queue.value.length - 1) {
      void playSong(queue.value[idx + 1])
    }
  }

  // 播放队列中的上一首，队列开头保持当前歌曲。
  function playPrev() {
    if (!currentSong.value) return
    const idx = queue.value.findIndex((s) => s.id === currentSong.value!.id)
    if (idx > 0) {
      void playSong(queue.value[idx - 1])
    }
  }

  // 同步响应式音量和原生 Audio 音量。
  function setVolume(v: number) {
    volume.value = v
    audio.value.volume = v
  }

  // 将播放器定位到指定秒数。
  function seek(time: number) {
    audio.value.currentTime = time
  }

  // 设置当前页面提供的播放队列。
  function setQueue(songs: SongBrief[]) {
    queue.value = songs
  }

  return {
    currentSong,
    queue,
    playing,
    currentTime,
    duration,
    volume,
    playSong,
    togglePlay,
    playNext,
    playPrev,
    setVolume,
    seek,
    setQueue,
  }
})
