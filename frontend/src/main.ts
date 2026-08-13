import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import 'element-plus/dist/index.css'
import './styles/base.css'
import App from './App.vue'
import router from './router'
import { installTableColumnSettings } from './directives/tableColumnSettings'
import { installTableStatusTabs } from './directives/tableStatusTabs'

const app = createApp(App)
installTableColumnSettings(app)
installTableStatusTabs(app)
app.use(createPinia()).use(router).use(ElementPlus, { locale: zhCn }).mount('#app')
