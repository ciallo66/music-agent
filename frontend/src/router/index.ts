import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

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
        },
        {
          path: 'playlists/:id',
          name: 'playlist-detail',
          component: () => import('../views/PlaylistDetailPage.vue'),
        },
        {
          path: 'favorites',
          name: 'favorites',
          component: () => import('../views/FavoritesPage.vue'),
        },
        { path: 'search', name: 'search', component: () => import('../views/SearchPage.vue') },
        { path: 'agent', name: 'agent', component: () => import('../views/AgentPage.vue') },
        {
          path: 'admin/imports',
          name: 'admin-imports',
          component: () => import('../views/AdminImportsPage.vue'),
          meta: { requiresAdmin: true },
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

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!auth.initialized) await auth.initialize()
  if (to.path !== '/login' && !auth.isAuthenticated) {
    return '/login'
  }
  if (to.path === '/login' && auth.isAuthenticated) {
    return '/'
  }
  if (to.meta.requiresAdmin === true && !auth.isAdmin) {
    return '/'
  }
})

export default router
