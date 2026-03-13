<template>
  <div>
    <RequirementCard
      v-for="requirement in requirements"
      :key="requirement.id"
      :requirement="requirement"
      @accept="$emit('accept', requirement.id)"
      @reject="$emit('reject', requirement.id, $event)"
      @edit="$emit('edit', requirement.id, $event.text, $event.reason, $event.type, $event.priority)"
      @view-page="$emit('view-page', $event)"
      @assigned="$emit('assigned', $event)"
      @status-changed="$emit('status-changed', $event)"
    />
  </div>
</template>

<script setup>
import RequirementCard from './RequirementCard.vue'

defineProps({
  requirements: { type: Array, required: true }
})

defineEmits(['accept', 'reject', 'edit', 'view-page', 'assigned', 'status-changed'])
</script>
