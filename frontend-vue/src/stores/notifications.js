import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useNotificationsStore = defineStore('notifications', () => {
  const snackbar = ref({
    show: false,
    text: '',
    color: 'error',
    timeout: 4000,
  })

  function notify(text, color = 'error', timeout = 4000) {
    snackbar.value = { show: true, text, color, timeout }
  }

  function notifyError(text) {
    notify(text, 'error')
  }

  function notifySuccess(text) {
    notify(text, 'success')
  }

  function notifyInfo(text) {
    notify(text, 'info')
  }

  return { snackbar, notify, notifyError, notifySuccess, notifyInfo }
})
