import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { SongBrief } from '../api/playlists'

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

  function playSong(song: SongBrief) {
    currentSong.value = song
    if (song.audio_url) {
      audio.value.src = song.audio_url
      audio.value.play()
    }
  }

  function togglePlay() {
    if (!currentSong.value?.audio_url) return
    if (playing.value) {
      audio.value.pause()
    } else {
      audio.value.play()
    }
  }

  function playNext() {
    if (!currentSong.value) return
    const idx = queue.value.findIndex((s) => s.id === currentSong.value!.id)
    if (idx >= 0 && idx < queue.value.length - 1) {
      playSong(queue.value[idx + 1])
    }
  }

  function playPrev() {
    if (!currentSong.value) return
    const idx = queue.value.findIndex((s) => s.id === currentSong.value!.id)
    if (idx > 0) {
      playSong(queue.value[idx - 1])
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
