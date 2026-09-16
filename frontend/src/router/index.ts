// 路由表与认证守卫；守卫先等待认证恢复再决定页面访问权限。
import { createRouter, createWebHistory } from 'vue-router'
import { ref } from 'vue'
import { useAuthStore } from '../stores/auth'

export const isNavigating = ref(false)

// 资源版本失配时的自动恢复：记录上次重载时间，避免陷入无限刷新。
const CHUNK_RELOAD_KEY = 'music-agent:chunk-reload-at'
const CHUNK_RELOAD_COOLDOWN_MS = 10_000

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: () => import('../views/MainLayout.vue'),
      children: [
        { path: '', name: 'home', component: () => import('../views/HomePage.vue') },
        { path: 'songs', name: 'songs', component: () => import('../views/SongsPage.vue') },
        {
          path: 'songs/:id',
          name: 'song-detail',
          component: () => import('../views/SongDetailPage.vue'),
        },
        {
          path: 'playlists',
          name: 'playlists',
          component: () => import('../views/PlaylistsPage.vue'),
          meta: { requiresAuth: true },
        },
        {
          path: 'playlists/:id',
          name: 'playlist-detail',
          component: () => import('../views/PlaylistDetailPage.vue'),
          meta: { requiresAuth: true },
        },
        {
          path: 'favorites',
          name: 'favorites',
          component: () => import('../views/FavoritesPage.vue'),
          meta: { requiresAuth: true },
        },
        {
          path: 'profile',
          name: 'music-profile',
          component: () => import('../views/MusicProfilePage.vue'),
          meta: { requiresAuth: true },
        },
        {
          path: 'search',
          name: 'search',
          redirect: (to) => ({ name: 'songs', query: { q: to.query.q } }),
        },
        {
          path: 'agent',
          name: 'agent',
          component: () => import('../views/AgentPage.vue'),
          meta: { requiresAuth: true },
        },
        {
          path: 'admin/imports',
          name: 'admin-imports',
          component: () => import('../views/AdminImportsPage.vue'),
          meta: { requiresAuth: true, requiresAdmin: true },
        },
        {
          path: 'access-required',
          name: 'access-required',
          component: () => import('../views/AuthRequiredPage.vue'),
        },
      ],
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('../views/LoginPage.vue'),
    },
  ],
})

router.beforeResolve(() => {
  isNavigating.value = true
})

router.afterEach(() => {
  isNavigating.value = false
})

// 判断错误是否来自动态 import 失败：浏览器持有过期资源清单时，
// 服务器会返回 index.html，模块解析失败并抛出 SyntaxError。
function isChunkLoadError(error: unknown): boolean {
  if (error instanceof SyntaxError) return true
  const message = error instanceof Error ? error.message : String(error)
  return (
    message.includes('dynamically imported module') ||
    message.includes('Importing a module script failed')
  )
}

// 强制重载以拉取新的资源清单，让用户从版本失配中自动恢复。
function reloadForFreshAssets(target: string): void {
  try {
    const now = Date.now()
    const lastReloadAt = Number(window.sessionStorage.getItem(CHUNK_RELOAD_KEY) ?? 0)
    // 冷却期内不再重载，避免资源确实缺失时反复刷新。
    if (now - lastReloadAt < CHUNK_RELOAD_COOLDOWN_MS) return
    window.sessionStorage.setItem(CHUNK_RELOAD_KEY, String(now))
  } catch {
    // 存储不可用时仍执行一次重载，保证用户至少有一次恢复机会。
  }
  window.location.assign(target)
}

router.onError((error, to) => {
  isNavigating.value = false
  if (isChunkLoadError(error)) {
    reloadForFreshAssets(to.fullPath)
  }
})

// 所有受保护路由等待认证恢复，避免未登录页面短暂闪现。
router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!auth.initialized) {
    if (to.meta.requiresAuth === true) {
      await auth.initialize()
    } else {
      void auth.initialize()
    }
  }
  if (to.meta.requiresAuth === true && !auth.isAuthenticated) {
    return {
      name: 'access-required',
      query: {
        redirect: to.fullPath,
        title: to.meta.requiresAdmin ? '登录后进入管理工作区' : undefined,
      },
    }
  }
  if (to.path === '/login' && auth.isAuthenticated) {
    return '/'
  }
  if (to.meta.requiresAdmin === true && !auth.isAdmin) {
    return '/'
  }
})

export default router
