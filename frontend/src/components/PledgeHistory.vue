<script setup>
import { reactive, ref } from 'vue'
import { api } from '../api'
import { formatDate, formatMoney, todayIso } from '../format'

const props = defineProps({
  item: { type: Object, required: true },
  admin: { type: Boolean, default: false },
})
const emit = defineEmits(['changed', 'unauthorized'])

const newPayment = reactive({ date: todayIso(), amount: '' })
const editing = reactive({ id: null, date: '', amount: '' })
const confirmingDelete = ref(null)
const busy = ref(false)
const error = ref('')

async function run(action) {
  error.value = ''
  busy.value = true
  try {
    const updated = await action()
    emit('changed', updated)
    return true
  } catch (e) {
    if (e.status === 401) emit('unauthorized')
    error.value = e.message
    return false
  } finally {
    busy.value = false
  }
}

async function addPayment() {
  const ok = await run(() =>
    api.addPayment(props.item.id, { date: newPayment.date, amount: Number(newPayment.amount) }),
  )
  if (ok) newPayment.amount = ''
}

function startEdit(p) {
  confirmingDelete.value = null
  Object.assign(editing, { id: p.id, date: p.date, amount: p.amount })
}

async function saveEdit() {
  const ok = await run(() =>
    api.updatePayment(editing.id, { date: editing.date, amount: Number(editing.amount) }),
  )
  if (ok) editing.id = null
}

async function removePayment(id) {
  const ok = await run(() => api.removePayment(id))
  if (ok) confirmingDelete.value = null
}
</script>

<template>
  <div class="history">
    <div class="head">
      <h3>Payment history</h3>
      <span v-if="item.overpaid > 0" class="pill pill-over">
        Paid {{ formatMoney(item.overpaid) }} more than pledged
      </span>
      <span v-else-if="item.balance <= 0" class="pill pill-done">Pledge fully paid</span>
      <span v-else class="pill pill-due">{{ formatMoney(item.balance) }} left to pay</span>
    </div>

    <p v-if="!item.payments.length" class="none">No payments recorded yet.</p>

    <ol v-else class="list" :class="{ 'with-actions': admin }">
      <li class="row row-head" aria-hidden="true">
        <span>#</span>
        <span>Date</span>
        <span class="r">Paid</span>
        <span class="r">Balance after</span>
        <span v-if="admin" />
      </li>
      <li v-for="(p, n) in item.payments" :key="p.id" class="row">
        <template v-if="editing.id === p.id">
          <span class="idx">{{ n + 1 }}</span>
          <input v-model="editing.date" class="input input-sm c-date" type="date" aria-label="Payment date" />
          <input
            v-model="editing.amount"
            class="input input-sm num c-paid"
            type="number"
            min="0.01"
            step="0.01"
            inputmode="decimal"
            aria-label="Amount paid"
          />
          <span class="c-gap" />
          <span class="btns c-act">
            <button class="btn btn-sm btn-primary" :disabled="busy" @click="saveEdit">Save</button>
            <button class="btn btn-sm btn-ghost" @click="editing.id = null">Cancel</button>
          </span>
        </template>
        <template v-else>
          <span class="idx">{{ n + 1 }}</span>
          <span class="c-date">{{ formatDate(p.date) }}</span>
          <span class="r num strong c-paid">{{ formatMoney(p.amount) }}</span>
          <span class="r num c-bal" :class="p.balance_after > 0 ? 'owed' : 'cleared'">
            {{ p.balance_after > 0 ? formatMoney(p.balance_after) : 'Cleared' }}
          </span>
          <span v-if="admin" class="btns c-act">
            <template v-if="confirmingDelete === p.id">
              <button class="btn btn-sm btn-danger" :disabled="busy" @click="removePayment(p.id)">Delete</button>
              <button class="btn btn-sm btn-ghost" @click="confirmingDelete = null">Keep</button>
            </template>
            <template v-else>
              <button class="btn btn-sm btn-ghost" @click="startEdit(p)">Edit</button>
              <button class="btn btn-sm btn-ghost danger" @click="confirmingDelete = p.id; editing.id = null">
                Delete
              </button>
            </template>
          </span>
        </template>
      </li>
    </ol>

    <div class="summary num">
      <span>Pledged <strong>{{ formatMoney(item.amount) }}</strong></span>
      <span>Paid <strong>{{ formatMoney(item.paid) }}</strong></span>
      <span>Balance <strong :class="{ owed: item.balance > 0 }">{{ formatMoney(item.balance) }}</strong></span>
    </div>

    <form v-if="admin" class="add" @submit.prevent="addPayment">
      <div class="field">
        <label :for="`pay-date-${item.id}`">Payment date</label>
        <input :id="`pay-date-${item.id}`" v-model="newPayment.date" class="input" type="date" required />
      </div>
      <div class="field">
        <label :for="`pay-amount-${item.id}`">Amount paid</label>
        <input
          :id="`pay-amount-${item.id}`"
          v-model="newPayment.amount"
          class="input num"
          type="number"
          min="0.01"
          step="0.01"
          inputmode="decimal"
          :placeholder="item.balance > 0 ? String(item.balance) : ''"
          required
        />
      </div>
      <button class="btn btn-primary" type="submit" :disabled="busy">
        {{ busy ? 'Saving...' : 'Record payment' }}
      </button>
    </form>

    <p v-if="error" class="error-box">{{ error }}</p>
  </div>
</template>

<style scoped>
.history {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 16px 20px 20px;
  border-left: 4px solid var(--purple);
  background: #fbfaff;
}
.head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
h3 {
  margin: 0;
  font-size: 1rem;
}
.pill {
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 0.8rem;
  font-weight: 700;
}
.pill-due {
  background: var(--red-soft);
  color: var(--red);
}
.pill-done {
  background: var(--purple-soft);
  color: var(--purple);
}
.pill-over {
  background: var(--purple);
  color: var(--white);
}
.none {
  margin: 0;
  color: var(--muted);
}

.list {
  margin: 0;
  padding: 0;
  list-style: none;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--white);
  overflow: hidden;
}
.row {
  display: grid;
  grid-template-columns: 32px 1fr 1fr 1fr;
  align-items: center;
  gap: 12px;
  min-height: 48px;
  padding: 6px 14px;
  border-top: 1px solid var(--line);
}
.with-actions .row {
  grid-template-columns: 32px 1fr 1fr 1fr 150px;
}
.row:first-child {
  border-top: 0;
}
.row-head {
  min-height: 36px;
  background: var(--page);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--muted);
}
.idx {
  display: grid;
  place-items: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--purple-soft);
  color: var(--purple);
  font-size: 0.75rem;
  font-weight: 700;
}
.r {
  text-align: right;
}
.strong {
  font-weight: 700;
}
.owed {
  color: var(--red);
  font-weight: 700;
}
.cleared {
  color: var(--purple);
  font-weight: 600;
}
.btns {
  display: inline-flex;
  justify-content: flex-end;
  gap: 6px;
}
.danger:hover:not(:disabled) {
  border-color: var(--red);
  color: var(--red);
}
.input-sm {
  min-height: 36px;
}

.summary {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 24px;
  font-size: 0.9rem;
  color: var(--muted);
}
.summary strong {
  color: var(--black);
}
.summary strong.owed {
  color: var(--red);
}

.add {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 12px;
  padding-top: 14px;
  border-top: 1px dashed var(--line);
}
.add .field {
  flex: 1 1 160px;
}

@media (max-width: 760px) {
  .history {
    padding: 14px 14px 16px;
  }
  .row-head {
    display: none;
  }
  .row,
  .with-actions .row {
    grid-template-columns: 32px 1fr auto;
    gap: 4px 10px;
    padding: 10px 12px;
  }
  .c-paid {
    grid-column: 3;
    grid-row: 1;
  }
  .c-bal {
    grid-column: 2 / 4;
    font-size: 0.85rem;
  }
  .c-bal::before {
    content: 'Balance after: ';
    color: var(--muted);
    font-weight: 400;
  }
  .c-gap {
    display: none;
  }
  .c-act {
    grid-column: 1 / 4;
    padding-top: 6px;
  }
  .add .btn {
    width: 100%;
  }
}
</style>
