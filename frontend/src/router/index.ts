// 路由表与认证守卫；守卫先等待认证恢复再决定页面访问权限。
import { createRouter, createWebHistory } from 'vue-router'
import { ref } from 'vue'
import { useAuthStore } from '../stores/auth'

export const isNavigating = ref(false)

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

router.onError(() => {
  isNavigating.value = false
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
