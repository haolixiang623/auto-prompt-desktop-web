import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './style.css'

console.log('Main.js loading...')

const app = createApp(App)

app.use(createPinia())
app.use(router)

app.config.errorHandler = (err, instance, info) => {
  console.error('Vue error:', err, info)
}

console.log('Mounting app...')
app.mount('#app')
console.log('App mounted!')
