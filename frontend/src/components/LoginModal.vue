<script setup>
import { ref } from 'vue'
import BaseModal from './BaseModal.vue'
import { api, setToken } from '../api'

const emit = defineEmits(['close', 'signed-in'])

const username = ref('')
const password = ref('')
const error = ref('')
const busy = ref(false)

async function submit() {
  error.value = ''
  busy.value = true
  try {
    const { token, username: user } = await api.login(username.value.trim(), password.value)
    setToken(token)
    emit('signed-in', user)
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <BaseModal title="Admin sign in" @close="emit('close')">
    <form class="form" @submit.prevent="submit">
      <div class="field">
        <label for="username">Username</label>
        <input id="username" v-model="username" class="input" autocomplete="username" required autofocus />
      </div>
      <div class="field">
        <label for="password">Password</label>
        <input
          id="password"
          v-model="password"
          class="input"
          type="password"
          autocomplete="current-password"
          required
        />
      </div>
      <p v-if="error" class="error-box">{{ error }}</p>
      <button class="btn btn-primary" type="submit" :disabled="busy">
        {{ busy ? 'Signing in...' : 'Sign in' }}
      </button>
    </form>
  </BaseModal>
</template>

<style scoped>
.form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
</style>
