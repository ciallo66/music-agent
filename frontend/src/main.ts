// 创建应用、注册 Pinia 与路由，并挂载根组件。
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
// Element Plus 官方深色变量：不引入的话 el-table / el-dialog 这些组件
// 会用默认亮色（表格整块白底）。必须放在自己的 style.css 之前，
// 让 style.css 里的设计令牌与覆盖规则能盖上去。
import 'element-plus/theme-chalk/dark/css-vars.css'
import './style.css'
import App from './App.vue'

const app = createApp(App).use(createPinia()).use(router)
app.mount('#app')
