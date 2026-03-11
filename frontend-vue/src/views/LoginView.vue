<template>
  <v-container class="fill-height" fluid>
    <v-row align="center" justify="center">
      <v-col cols="12" sm="8" md="5" lg="4">
        <v-card elevation="8" rounded="lg">
          <v-card-item class="pa-6 pb-2">
            <div class="d-flex align-center gap-3 mb-2">
              <v-icon size="36" color="primary">mdi-clipboard-check-multiple</v-icon>
              <div>
                <v-card-title class="text-h6 pa-0">Система управления требованиями</v-card-title>
                <v-card-subtitle class="pa-0">Войдите в систему</v-card-subtitle>
              </div>
            </div>
          </v-card-item>

          <v-card-text class="pa-6 pt-4">
            <v-form ref="form" @submit.prevent="handleLogin">
              <v-text-field
                v-model="email"
                label="Email"
                type="email"
                prepend-inner-icon="mdi-email-outline"
                variant="outlined"
                :rules="[v => !!v || 'Введите email']"
                :disabled="loading"
                class="mb-3"
                autofocus
              />
              <v-text-field
                v-model="password"
                label="Пароль"
                :type="showPassword ? 'text' : 'password'"
                prepend-inner-icon="mdi-lock-outline"
                :append-inner-icon="showPassword ? 'mdi-eye-off' : 'mdi-eye'"
                @click:append-inner="showPassword = !showPassword"
                variant="outlined"
                :rules="[v => !!v || 'Введите пароль']"
                :disabled="loading"
                class="mb-1"
              />

              <v-alert
                v-if="error"
                type="error"
                variant="tonal"
                density="compact"
                class="mb-4"
              >
                {{ error }}
              </v-alert>

              <v-btn
                type="submit"
                color="primary"
                size="large"
                block
                :loading="loading"
                class="mt-2"
              >
                Войти
              </v-btn>
            </v-form>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const form = ref(null)
const email = ref('')
const password = ref('')
const showPassword = ref(false)
const loading = ref(false)
const error = ref('')

async function handleLogin() {
  const { valid } = await form.value.validate()
  if (!valid) return

  loading.value = true
  error.value = ''
  try {
    await auth.login(email.value, password.value)
    const redirect = route.query.redirect || '/'
    router.push(redirect)
  } catch (e) {
    const msg = e.response?.data?.detail
    error.value = msg || 'Неверный email или пароль'
  } finally {
    loading.value = false
  }
}
</script>
