<template>
  <v-card v-if="processing">
    <v-card-title>
      <v-icon left>mdi-loading</v-icon>
      Обработка документа...
    </v-card-title>
    
    <v-card-text>
      <v-progress-linear
        :model-value="progress"
        color="primary"
        height="25"
        rounded
      >
        <template v-slot:default="{ value }">
          <strong>{{ Math.ceil(value) }}%</strong>
        </template>
      </v-progress-linear>

      <div class="mt-4">
        <div class="text-subtitle-1 mb-2">{{ currentStep }}</div>
        <div class="text-body-2 text-medium-emphasis">{{ message }}</div>
      </div>

      <v-list v-if="logs.length > 0" class="mt-4" density="compact">
        <v-list-item
          v-for="(log, index) in recentLogs"
          :key="index"
          :prepend-icon="getLogIcon(log.level)"
          :title="log.message"
          :subtitle="formatTime(log.timestamp)"
          density="compact"
        ></v-list-item>
      </v-list>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  processing: {
    type: Boolean,
    default: false
  },
  progress: {
    type: Number,
    default: 0
  },
  currentStep: {
    type: String,
    default: ''
  },
  message: {
    type: String,
    default: ''
  }
})

const logs = ref([])
let ws = null

const recentLogs = computed(() => {
  return logs.value.slice(-10).reverse()
})

const getLogIcon = (level) => {
  const icons = {
    INFO: 'mdi-information',
    WARNING: 'mdi-alert',
    ERROR: 'mdi-alert-circle',
    DEBUG: 'mdi-bug'
  }
  return icons[level] || 'mdi-circle'
}

const formatTime = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleTimeString('ru-RU')
}

const connectWebSocket = () => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${protocol}//${window.location.host}/ws/logs`

  try {
    ws = new WebSocket(wsUrl)

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.type === 'log') {
          logs.value.push({ level: data.level, message: data.message, timestamp: data.timestamp })
          if (logs.value.length > 100) logs.value.shift()
        }
      } catch {
        // Malformed message; skip
      }
    }

    ws.onerror = () => {}

    ws.onclose = () => {
      setTimeout(connectWebSocket, 3000)
    }
  } catch {
    // WebSocket connection failure is non-critical
  }
}

onMounted(() => {
  if (props.processing) {
    connectWebSocket()
  }
})

onUnmounted(() => {
  if (ws) {
    ws.close()
  }
})
</script>
