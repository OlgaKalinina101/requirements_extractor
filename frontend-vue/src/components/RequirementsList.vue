<template>
  <div>
    <div
      v-for="requirement in requirements"
      :key="requirement.id"
      :id="`req-${requirement.id}`"
    >
      <RequirementCard
        :requirement="requirement"
      @accept="$emit('accept', requirement.id)"
      @reject="$emit('reject', requirement.id, $event)"
      @edit="$emit('edit', requirement.id, $event.text, $event.reason, $event.type, $event.priority, $event.discipline, $event.verification_method, $event.deadline)"
      @view-page="$emit('view-page', $event)"
      @assigned="$emit('assigned', $event)"
      @status-changed="$emit('status-changed', $event)"
    />
    </div>
  </div>
</template>

<script setup>
import RequirementCard from './RequirementCard.vue'

defineProps({
  requirements: { type: Array, required: true }
})

defineEmits(['accept', 'reject', 'edit', 'view-page', 'assigned', 'status-changed'])
</script>
