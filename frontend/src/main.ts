// 创建应用、注册 Pinia 与路由，并挂载根组件。
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import './style.css'
import App from './App.vue'

const app = createApp(App).use(createPinia()).use(router)
app.mount('#app')
