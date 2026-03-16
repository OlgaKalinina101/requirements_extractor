/**
 * Pinia store for reference dictionaries (requirement types, priorities, statuses).
 * Loaded once after login, used everywhere instead of hardcoded lists.
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/services/api'

export const useDictionariesStore = defineStore('dictionaries', () => {
  const types               = ref([])  // requirement_types
  const priorities          = ref([])  // priorities
  const statuses            = ref([])  // statuses
  const disciplines         = ref([])  // disciplines
  const verificationMethods = ref([])  // verification_methods
  const linkTypes            = ref([])  // link_types
  const loaded               = ref(false)
  const loading              = ref(false)

  async function loadAll() {
    if (loaded.value || loading.value) return
    loading.value = true
    try {
      const [t, p, s, d, v, l] = await Promise.all([
        api.get('/api/dictionaries/requirement_types'),
        api.get('/api/dictionaries/priorities'),
        api.get('/api/dictionaries/statuses'),
        api.get('/api/dictionaries/disciplines'),
        api.get('/api/dictionaries/verification_methods'),
        api.get('/api/dictionaries/link_types'),
      ])
      types.value               = t.data.filter(i => i.is_active)
      priorities.value          = p.data.filter(i => i.is_active)
      statuses.value            = s.data.filter(i => i.is_active)
      disciplines.value         = d.data.filter(i => i.is_active)
      verificationMethods.value = v.data.filter(i => i.is_active)
      linkTypes.value           = l.data.filter(i => i.is_active)
      loaded.value = true
    } catch (e) {
      console.error('Failed to load dictionaries', e)
    } finally {
      loading.value = false
    }
  }

  function reset() {
    types.value = []
    priorities.value = []
    statuses.value = []
    disciplines.value = []
    verificationMethods.value = []
    linkTypes.value = []
    loaded.value = false
  }

  // ── Helpers ──────────────────────────────────────────────────────────────

  /** Display name for a type code (e.g. "Technical" → "Technical" or the DB name) */
  function typeName(code) {
    if (!code) return ''
    const item = types.value.find(i => i.code === code)
    return item ? item.name : code
  }

  /** Vuetify color for a type code */
  function typeColor(code) {
    if (!code) return 'grey'
    const item = types.value.find(i => i.code === code)
    return item?.color || 'grey'
  }

  /** Display name for a priority code */
  function priorityName(code) {
    if (!code) return ''
    const item = priorities.value.find(i => i.code === code)
    return item ? item.name : code
  }

  /** Vuetify color for a priority code */
  function priorityColor(code) {
    if (!code) return 'grey'
    const item = priorities.value.find(i => i.code === code)
    return item?.color || 'grey'
  }

  /** Display name for a status code */
  function statusName(code) {
    if (!code) return ''
    const item = statuses.value.find(i => i.code === code)
    return item ? item.name : code
  }

  /** Vuetify color for a status code */
  function statusColor(code) {
    if (!code) return 'grey'
    const item = statuses.value.find(i => i.code === code)
    return item?.color || 'grey'
  }

  // ── Computed select-options (for dropdowns / filters) ──────────────────

  /** [{ title, value }] for v-select — types */
  const typeOptions = computed(() =>
    types.value.map(i => ({ title: i.name, value: i.code }))
  )

  /** [{ title, value }] for v-select — priorities */
  const priorityOptions = computed(() =>
    priorities.value.map(i => ({ title: i.name, value: i.code }))
  )

  /** [{ title, value }] for v-select — statuses */
  const statusOptions = computed(() =>
    statuses.value.map(i => ({ title: i.name, value: i.code }))
  )

  /** [{ title, value }] for v-select — disciplines */
  const disciplineOptions = computed(() =>
    disciplines.value.map(i => ({ title: i.name, value: i.code }))
  )

  /** [{ title, value }] for v-select — verification methods */
  const verificationMethodOptions = computed(() =>
    verificationMethods.value.map(i => ({ title: i.name, value: i.code }))
  )

  /** [{ title, value }] for v-select — link types */
  const linkTypeOptions = computed(() =>
    linkTypes.value.map(i => ({ title: i.name, value: i.code }))
  )

  /** Display name for link type code */
  function linkTypeName(code) {
    if (!code) return ''
    const item = linkTypes.value.find(i => i.code === code)
    return item ? item.name : code
  }

  /** Only execution statuses (in_progress, done, blocked) with icon */
  const executionStatusOptions = computed(() =>
    statuses.value
      .filter(i => ['in_progress', 'done', 'blocked'].includes(i.code))
      .map(i => ({
        value: i.code,
        label: i.name,
        color: i.color,
        icon: { in_progress: 'mdi-progress-clock', done: 'mdi-check-circle', blocked: 'mdi-alert-circle' }[i.code],
      }))
  )

  return {
    types, priorities, statuses, disciplines, verificationMethods, linkTypes, loaded, loading,
    loadAll, reset,
    typeName, typeColor,
    priorityName, priorityColor,
    statusName, statusColor,
    linkTypeName,
    typeOptions, priorityOptions, statusOptions, disciplineOptions, verificationMethodOptions, linkTypeOptions, executionStatusOptions,
  }
})
