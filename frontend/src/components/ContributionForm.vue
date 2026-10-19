<script setup>
import { computed, reactive, ref } from 'vue'
import BaseModal from './BaseModal.vue'
import { api } from '../api'
import { formatMoney, todayIso } from '../format'

const props = defineProps({ item: { type: Object, default: null } })
const emit = defineEmits(['close', 'saved', 'unauthorized'])

const item = props.item
const editing = !!item
// An existing pledge keeps its payment history; payments are recorded from that panel.
const wasPledged = !!item?.pledged
const paymentCount = item?.payments?.length ?? 0

const form = reactive({
  name: item?.name ?? '',
  date: item?.date ?? todayIso(),
  pledged: item?.pledged ?? false,
  amount: item?.pledged ? item.amount : '',
  paid: item ? item.paid || '' : '',
  // Switching a one-off to a pledge: what they already gave becomes the first payment.
  firstPayment: item && !item.pledged ? item.amount : '',
})

const error = ref('')
const busy = ref(false)

const paidSoFar = computed(() => (wasPledged ? item.paid : Number(form.firstPayment) || 0))
const remaining = computed(() => (Number(form.amount) || 0) - paidSoFar.value)

async function submit() {
  error.value = ''
  busy.value = true
  const payload = { name: form.name.trim(), date: form.date, pledged: form.pledged }
  if (form.pledged) {
    payload.amount = Number(form.amount)
    if (!wasPledged) payload.first_payment = form.firstPayment === '' ? 0 : Number(form.firstPayment)
  } else {
    payload.paid = Number(form.paid)
  }
  try {
    const saved = editing ? await api.update(item.id, payload) : await api.create(payload)
    emit('saved', saved)
  } catch (e) {
    if (e.status === 401) emit('unauthorized')
    error.value = e.message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <BaseModal :title="editing ? 'Edit contribution' : 'Add contribution'" @close="emit('close')">
    <form class="form" @submit.prevent="submit">
      <div class="field">
        <label for="name">Name</label>
        <input id="name" v-model="form.name" class="input" maxlength="160" required autofocus />
      </div>

      <div class="field">
        <label for="date">{{ form.pledged ? 'Date pledged' : 'Date' }}</label>
        <input id="date" v-model="form.date" class="input" type="date" required />
      </div>

      <label class="toggle">
        <input v-model="form.pledged" type="checkbox" />
        <span class="track" aria-hidden="true"><span class="thumb" /></span>
        <span class="toggle-text">
          <strong>Pledged</strong>
          <small>{{ form.pledged ? 'Paid in installments, each one kept in the history' : 'A one-off payment' }}</small>
        </span>
      </label>

      <template v-if="form.pledged">
        <div class="field">
          <label for="amount">Pledged amount</label>
          <input
            id="amount"
            v-model="form.amount"
            class="input num"
            type="number"
            min="0.01"
            step="0.01"
            inputmode="decimal"
            required
          />
        </div>

        <div v-if="!wasPledged" class="field">
          <label for="first">First payment <span class="optional">(optional)</span></label>
          <input
            id="first"
            v-model="form.firstPayment"
            class="input num"
            type="number"
            min="0"
            step="0.01"
            inputmode="decimal"
          />
          <small class="hint">Add later payments from the pledge's payment history.</small>
        </div>
        <p v-else class="note">
          Paid so far: <strong class="num">{{ formatMoney(item.paid) }}</strong>
          across {{ paymentCount }} {{ paymentCount === 1 ? 'payment' : 'payments' }}.
          Record new payments from the payment history.
        </p>

        <div class="balance" :class="{ due: remaining > 0 }">
          <span>{{ remaining < 0 ? 'Paid over the pledge by' : 'Balance' }}</span>
          <strong class="num">{{ formatMoney(Math.abs(remaining)) }}</strong>
        </div>
      </template>

      <template v-else>
        <div class="field">
          <label for="paid">Paid</label>
          <input
            id="paid"
            v-model="form.paid"
            class="input num"
            type="number"
            min="0.01"
            step="0.01"
            inputmode="decimal"
            required
          />
        </div>
        <p v-if="wasPledged && paymentCount" class="error-box">
          Turning off Pledged deletes the {{ paymentCount }} recorded
          {{ paymentCount === 1 ? 'payment' : 'payments' }} for this pledge.
        </p>
      </template>

      <p v-if="error" class="error-box">{{ error }}</p>

      <div class="actions">
        <button class="btn btn-ghost" type="button" @click="emit('close')">Cancel</button>
        <button class="btn btn-primary" type="submit" :disabled="busy">
          {{ busy ? 'Saving...' : editing ? 'Save changes' : 'Add contribution' }}
        </button>
      </div>
    </form>
  </BaseModal>
</template>

<style scoped>
.form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.toggle {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border: 1px solid var(--line);
  border-radius: 10px;
  cursor: pointer;
}
.toggle input {
  position: absolute;
  opacity: 0;
  width: 1px;
  height: 1px;
}
.track {
  flex: none;
  position: relative;
  width: 44px;
  height: 26px;
  border-radius: 999px;
  background: #cfcbd6;
  transition: background 0.15s;
}
.thumb {
  position: absolute;
  top: 3px;
  left: 3px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--white);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.25);
  transition: transform 0.15s;
}
.toggle input:checked + .track {
  background: var(--purple);
}
.toggle input:checked + .track .thumb {
  transform: translateX(18px);
}
.toggle-text {
  display: flex;
  flex-direction: column;
  line-height: 1.3;
}
.toggle-text small {
  color: var(--muted);
}
.balance {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  border-radius: 10px;
  background: var(--purple-soft);
  color: var(--purple);
}
.balance.due {
  background: var(--red-soft);
  color: var(--red);
}
.optional {
  font-weight: 400;
  color: var(--muted);
}
.hint {
  color: var(--muted);
}
.note {
  margin: 0;
  padding: 12px;
  border-radius: 10px;
  background: var(--page);
  font-size: 0.9rem;
}
.actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
}
</style>
