<script setup>
import { onMounted, onBeforeUnmount } from 'vue'

defineProps({ title: { type: String, required: true } })
const emit = defineEmits(['close'])

const onKey = (e) => e.key === 'Escape' && emit('close')
onMounted(() => document.addEventListener('keydown', onKey))
onBeforeUnmount(() => document.removeEventListener('keydown', onKey))
</script>

<template>
  <div class="backdrop" @mousedown.self="emit('close')">
    <div class="modal" role="dialog" aria-modal="true" :aria-label="title">
      <header>
        <h2>{{ title }}</h2>
        <button class="close" type="button" aria-label="Close" @click="emit('close')">&times;</button>
      </header>
      <slot />
    </div>
  </div>
</template>

<style scoped>
.backdrop {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  background: rgba(0, 0, 0, 0.55);
}
.modal {
  width: 100%;
  max-width: 440px;
  max-height: calc(100vh - 32px);
  overflow-y: auto;
  padding: 24px;
  border-radius: 16px;
  background: var(--white);
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.25);
}
header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}
h2 {
  margin: 0;
  font-size: 1.25rem;
}
.close {
  width: 36px;
  height: 36px;
  border: 0;
  border-radius: 50%;
  background: transparent;
  font-size: 1.6rem;
  line-height: 1;
  cursor: pointer;
}
.close:hover {
  background: var(--page);
}
</style>
