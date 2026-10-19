<script setup>
import { computed, onMounted, ref } from 'vue'
import BaseModal from './components/BaseModal.vue'
import ContributionForm from './components/ContributionForm.vue'
import LoginModal from './components/LoginModal.vue'
import PledgeHistory from './components/PledgeHistory.vue'
import { api, getToken, setToken } from './api'
import { SITE_TITLE } from './config'
import { formatDate, formatMoney } from './format'

const items = ref([])
const totals = ref({ count: 0, amount: 0, paid: 0, balance: 0 })
const loading = ref(true)
const loadError = ref('')

const admin = ref(null)
const showLogin = ref(false)
const formItem = ref(undefined) // undefined: closed, null: new, object: editing
const toDelete = ref(null)
const deleting = ref(false)
const deleteError = ref('')
const expanded = ref(new Set())

function toggleHistory(id) {
  const next = new Set(expanded.value)
  next.has(id) ? next.delete(id) : next.add(id)
  expanded.value = next
}

function onHistoryChanged(updated) {
  const idx = items.value.findIndex((i) => i.id === updated.id)
  if (idx !== -1) items.value[idx] = updated
  load()
}

const search = ref('')
const filter = ref('all')
const filters = [
  { value: 'all', label: 'All' },
  { value: 'pledges', label: 'Pledges' },
  { value: 'balance', label: 'With balance' },
  { value: 'cleared', label: 'Fully paid' },
]

const visible = computed(() => {
  const q = search.value.trim().toLowerCase()
  return items.value.filter((i) => {
    if (q && !i.name.toLowerCase().includes(q)) return false
    if (filter.value === 'pledges') return i.pledged
    if (filter.value === 'balance') return i.balance > 0
    if (filter.value === 'cleared') return i.balance <= 0
    return true
  })
})

async function load() {
  loadError.value = ''
  try {
    const data = await api.list()
    items.value = data.items
    totals.value = data.totals
  } catch (e) {
    loadError.value = e.message
  } finally {
    loading.value = false
  }
}

async function restoreSession() {
  if (!getToken()) return
  try {
    admin.value = (await api.me()).username
  } catch {
    setToken(null)
  }
}

function onSignedIn(user) {
  admin.value = user
  showLogin.value = false
}

function signOut() {
  setToken(null)
  admin.value = null
}

function sessionExpired() {
  signOut()
  formItem.value = undefined
  toDelete.value = null
  showLogin.value = true
}

async function onSaved(saved) {
  formItem.value = undefined
  if (saved.pledged && !expanded.value.has(saved.id)) toggleHistory(saved.id)
  await load()
}

async function confirmDelete() {
  deleting.value = true
  deleteError.value = ''
  try {
    await api.remove(toDelete.value.id)
    toDelete.value = null
    await load()
  } catch (e) {
    if (e.status === 401) return sessionExpired()
    deleteError.value = e.message
  } finally {
    deleting.value = false
  }
}

const progress = computed(() => {
  const { amount, paid } = totals.value
  return amount > 0 ? Math.min(100, Math.round((paid / amount) * 100)) : 0
})

onMounted(() => {
  restoreSession()
  load()
})
</script>

<template>
  <header class="topbar">
    <div class="container topbar-inner">
      <div class="brand">
        <span class="logo" aria-hidden="true">
          <svg viewBox="0 0 32 32"><path d="M9 17l5 5 9-11" /></svg>
        </span>
        <span>{{ SITE_TITLE }}</span>
      </div>
      <div v-if="admin" class="admin-bar">
        <span class="who">Signed in as {{ admin }}</span>
        <button class="btn btn-sm btn-outline-light" @click="signOut">Sign out</button>
      </div>
      <button v-else class="btn btn-sm btn-primary" @click="showLogin = true">Sign in</button>
    </div>
  </header>

  <main class="container">
    <section class="stats">
      <div class="stat">
        <span class="label">Total contributions</span>
        <strong class="value num">{{ formatMoney(totals.amount) }}</strong>
        <span class="sub">{{ totals.count }} {{ totals.count === 1 ? 'entry' : 'entries' }}</span>
      </div>
      <div class="stat stat-paid">
        <span class="label">Paid</span>
        <strong class="value num">{{ formatMoney(totals.paid) }}</strong>
        <div class="bar" role="progressbar" :aria-valuenow="progress" aria-valuemin="0" aria-valuemax="100">
          <span :style="{ width: progress + '%' }" />
        </div>
        <span class="sub">{{ progress }}% of the total collected</span>
      </div>
      <div class="stat stat-balance">
        <span class="label">Outstanding balance</span>
        <strong class="value num">{{ formatMoney(totals.balance) }}</strong>
        <span class="sub">Still owed on pledges</span>
      </div>
    </section>

    <section class="panel">
      <div class="toolbar">
        <input
          v-model="search"
          class="input search"
          type="search"
          placeholder="Search by name"
          aria-label="Search by name"
        />
        <div class="chips" role="tablist">
          <button
            v-for="f in filters"
            :key="f.value"
            class="chip"
            :class="{ active: filter === f.value }"
            role="tab"
            :aria-selected="filter === f.value"
            @click="filter = f.value"
          >
            {{ f.label }}
          </button>
        </div>
        <button v-if="admin" class="btn btn-primary add" @click="formItem = null">+ Add contribution</button>
      </div>

      <p v-if="loading" class="empty">Loading contributions...</p>
      <div v-else-if="loadError" class="empty">
        <p class="error-box">{{ loadError }}</p>
        <button class="btn btn-ghost" @click="load">Try again</button>
      </div>
      <p v-else-if="!items.length" class="empty">
        No contributions yet.<template v-if="admin"> Add the first one above.</template>
      </p>
      <p v-else-if="!visible.length" class="empty">Nothing matches your search.</p>

      <div v-else class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Date</th>
              <th>Type</th>
              <th class="r">Amount</th>
              <th class="r">Paid</th>
              <th class="r">Balance</th>
              <th v-if="admin" class="r"><span class="sr-only">Actions</span></th>
            </tr>
          </thead>
          <tbody>
            <template v-for="i in visible" :key="i.id">
            <tr :class="{ open: expanded.has(i.id) }">
              <td class="name" data-label="Name">
                <button
                  v-if="i.pledged"
                  class="expander"
                  :aria-expanded="expanded.has(i.id)"
                  :aria-controls="`history-${i.id}`"
                  @click="toggleHistory(i.id)"
                >
                  <svg class="chevron" viewBox="0 0 16 16" aria-hidden="true"><path d="M6 3l5 5-5 5" /></svg>
                  <span>{{ i.name }}</span>
                </button>
                <span v-else class="plain-name">{{ i.name }}</span>
              </td>
              <td data-label="Date">{{ formatDate(i.date) }}</td>
              <td data-label="Type">
                <span class="badge" :class="i.pledged ? 'badge-pledge' : 'badge-paid'">
                  {{ i.pledged ? 'Pledge' : 'Paid' }}
                </span>
              </td>
              <td class="r num" data-label="Amount">{{ formatMoney(i.amount) }}</td>
              <td class="r num" data-label="Paid">
                <span class="paid-cell">
                  {{ formatMoney(i.paid) }}
                  <button v-if="i.pledged" class="count" @click="toggleHistory(i.id)">
                    {{ i.payments.length }} {{ i.payments.length === 1 ? 'payment' : 'payments' }}
                  </button>
                </span>
              </td>
              <td class="r num" data-label="Balance">
                <span v-if="!i.pledged" class="muted">None</span>
                <span v-else-if="i.balance > 0" class="owed">{{ formatMoney(i.balance) }}</span>
                <span v-else-if="i.overpaid > 0" class="cleared">Cleared, +{{ formatMoney(i.overpaid) }}</span>
                <span v-else class="cleared">Cleared</span>
              </td>
              <td v-if="admin" class="r actions">
                <div class="row-actions">
                  <button class="btn btn-sm btn-ghost" @click="formItem = i">Edit</button>
                  <button class="btn btn-sm btn-ghost danger" @click="toDelete = i; deleteError = ''">Delete</button>
                </div>
              </td>
            </tr>
            <tr v-if="i.pledged && expanded.has(i.id)" :id="`history-${i.id}`" class="history-row">
              <td :colspan="admin ? 7 : 6" class="history-cell">
                <PledgeHistory
                  :item="i"
                  :admin="!!admin"
                  @changed="onHistoryChanged"
                  @unauthorized="sessionExpired"
                />
              </td>
            </tr>
            </template>
          </tbody>
        </table>
      </div>
    </section>
  </main>

  <LoginModal v-if="showLogin" @close="showLogin = false" @signed-in="onSignedIn" />

  <ContributionForm
    v-if="formItem !== undefined"
    :item="formItem"
    @close="formItem = undefined"
    @saved="onSaved"
    @unauthorized="sessionExpired"
  />

  <BaseModal v-if="toDelete" title="Delete contribution" @close="toDelete = null">
    <p class="confirm-text">
      Delete the contribution from <strong>{{ toDelete.name }}</strong> on {{ formatDate(toDelete.date) }}?
      This cannot be undone.
    </p>
    <p v-if="deleteError" class="error-box">{{ deleteError }}</p>
    <div class="confirm-actions">
      <button class="btn btn-ghost" @click="toDelete = null">Cancel</button>
      <button class="btn btn-danger" :disabled="deleting" @click="confirmDelete">
        {{ deleting ? 'Deleting...' : 'Delete' }}
      </button>
    </div>
  </BaseModal>
</template>

<style scoped>
.topbar {
  background: var(--black);
  color: var(--white);
}
.topbar-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 64px;
}
.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 700;
  font-size: 1.1rem;
}
.logo {
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: var(--purple);
}
.logo svg {
  width: 20px;
  height: 20px;
  fill: none;
  stroke: var(--white);
  stroke-width: 3.5;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.admin-bar {
  display: flex;
  align-items: center;
  gap: 12px;
}
.who {
  font-size: 0.85rem;
  color: #c9c4d2;
}
.btn-outline-light {
  background: transparent;
  border-color: rgba(255, 255, 255, 0.35);
  color: var(--white);
}
.btn-outline-light:hover {
  border-color: var(--white);
}

main {
  padding-top: 24px;
  padding-bottom: 48px;
}

.stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}
.stat {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 20px;
  border-radius: var(--radius);
  background: var(--white);
  box-shadow: var(--shadow);
  border-top: 4px solid var(--black);
}
.stat-paid {
  border-top-color: var(--purple);
}
.stat-balance {
  border-top-color: var(--red);
}
.label {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--muted);
}
.value {
  font-size: 1.6rem;
  line-height: 1.2;
  overflow-wrap: anywhere;
}
.stat-paid .value {
  color: var(--purple);
}
.stat-balance .value {
  color: var(--red);
}
.sub {
  font-size: 0.85rem;
  color: var(--muted);
}
.bar {
  height: 6px;
  margin: 6px 0 2px;
  border-radius: 999px;
  background: var(--purple-soft);
  overflow: hidden;
}
.bar span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--purple);
  transition: width 0.3s;
}

.panel {
  border-radius: var(--radius);
  background: var(--white);
  box-shadow: var(--shadow);
  overflow: hidden;
}
.toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  padding: 16px;
  border-bottom: 1px solid var(--line);
}
.search {
  flex: 1 1 220px;
  max-width: 320px;
}
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.chip {
  min-height: 34px;
  padding: 0 14px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--white);
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
}
.chip:hover {
  border-color: var(--purple);
}
.chip.active {
  background: var(--black);
  border-color: var(--black);
  color: var(--white);
}
.add {
  margin-left: auto;
}

.empty {
  margin: 0;
  padding: 48px 16px;
  text-align: center;
  color: var(--muted);
}
div.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.table-wrap {
  overflow-x: auto;
}
table {
  width: 100%;
  border-collapse: collapse;
}
th,
td {
  padding: 12px 16px;
  text-align: left;
  white-space: nowrap;
}
th {
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--muted);
  background: var(--page);
}
td {
  border-top: 1px solid var(--line);
}
tbody tr:not(.history-row):hover {
  background: #fbfaff;
}
tr.open {
  background: #fbfaff;
}
.history-cell {
  padding: 0;
  border-top: 0;
  white-space: normal;
}
.expander {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin: -4px 0 -4px -6px;
  padding: 4px 6px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  font-weight: 600;
  text-align: left;
  cursor: pointer;
}
.expander:hover {
  color: var(--purple);
}
.expander:focus-visible,
.count:focus-visible {
  outline: 3px solid color-mix(in srgb, var(--purple) 40%, transparent);
}
.chevron {
  flex: none;
  width: 14px;
  height: 14px;
  fill: none;
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
  transition: transform 0.15s;
}
.open .chevron {
  transform: rotate(90deg);
  color: var(--purple);
}
.plain-name {
  padding-left: 14px;
}
.paid-cell {
  display: inline-flex;
  flex-direction: column;
  align-items: flex-end;
  line-height: 1.3;
}
.count {
  padding: 0;
  border: 0;
  background: none;
  color: var(--purple);
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
}
.count:hover {
  text-decoration: underline;
}
.r {
  text-align: right;
}
.name {
  font-weight: 600;
  white-space: normal;
  min-width: 140px;
}
.badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 700;
}
.badge-pledge {
  background: var(--purple-soft);
  color: var(--purple);
}
.badge-paid {
  background: #ececec;
  color: var(--black);
}
.owed {
  color: var(--red);
  font-weight: 700;
}
.cleared {
  color: var(--purple);
  font-weight: 600;
}
.muted {
  color: var(--muted);
}
.row-actions {
  display: inline-flex;
  gap: 6px;
}
.danger:hover:not(:disabled) {
  border-color: var(--red);
  color: var(--red);
}

.confirm-text {
  margin: 0 0 16px;
}
.confirm-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 16px;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
}

@media (max-width: 760px) {
  .stats {
    grid-template-columns: 1fr;
  }
  .who {
    display: none;
  }
  .search {
    max-width: none;
  }
  .add {
    width: 100%;
    margin-left: 0;
  }

  /* Stack each row into a card on phones. */
  thead {
    display: none;
  }
  table,
  tbody,
  tr,
  td {
    display: block;
  }
  tr {
    padding: 12px 16px;
    border-top: 1px solid var(--line);
  }
  td {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    padding: 4px 0;
    border: 0;
    text-align: right;
  }
  td::before {
    content: attr(data-label);
    color: var(--muted);
    font-size: 0.85rem;
    text-align: left;
  }
  td.name {
    font-size: 1.05rem;
    padding-bottom: 6px;
  }
  td.name::before {
    content: none;
  }
  td.actions {
    justify-content: flex-end;
    padding-top: 10px;
  }
  tr.history-row {
    padding: 0;
    border-top: 0;
  }
  td.history-cell {
    display: block;
    padding: 0;
    text-align: left;
  }
  td.history-cell::before {
    content: none;
  }
  .plain-name {
    padding-left: 0;
  }
  .paid-cell {
    flex-direction: row;
    align-items: baseline;
    gap: 8px;
  }
}
</style>
