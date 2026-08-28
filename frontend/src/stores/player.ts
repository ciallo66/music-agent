import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { SongSummary as SongBrief } from '../types/music'
import { recordPlay } from '../api/plays'

export const usePlayerStore = defineStore('player', () => {
  const currentSong = ref<SongBrief | null>(null)
  const queue = ref<SongBrief[]>([])
  const playing = ref(false)
  const audio = ref(new Audio())
  const currentTime = ref(0)
  const duration = ref(0)
  const volume = ref(1)

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

  async function playSong(song: SongBrief): Promise<void> {
    currentSong.value = song
    audio.value.pause()
    audio.value.currentTime = 0
    currentTime.value = 0
    duration.value = song.duration ?? 0
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

  function playNext() {
    if (!currentSong.value) return
    const idx = queue.value.findIndex((s) => s.id === currentSong.value!.id)
    if (idx >= 0 && idx < queue.value.length - 1) {
      void playSong(queue.value[idx + 1])
    }
  }

  function playPrev() {
    if (!currentSong.value) return
    const idx = queue.value.findIndex((s) => s.id === currentSong.value!.id)
    if (idx > 0) {
      void playSong(queue.value[idx - 1])
    }
  }

  function setVolume(v: number) {
    volume.value = v
    audio.value.volume = v
  }

  function seek(time: number) {
    audio.value.currentTime = time
  }

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
