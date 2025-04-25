<script setup>
import AttackCardDisplay from '@/components/AttackCardDisplay.vue';

const props = defineProps({
  attacks: {
    type: Array,
    required: true
  },
  mode: { 
    type: String, 
    default: 'display', // 'display', 'action'
    validator: (value) => ['display', 'action'].includes(value)
  },
  disabledIds: {
    type: Set,
    default: () => new Set()
  }
});

const emit = defineEmits(['attackClick']); 

function handleClick(attack) {
  if (props.mode !== 'action' || props.disabledIds.has(attack.id)) {
    return; 
  }
  emit('attackClick', attack);
}
</script>

<template>
  <div class="attack-list-mobile">
    <div 
      v-if="!attacks || attacks.length === 0" 
      class="empty-list-message"
    >
      <slot name="empty">No attacks to display.</slot>
    </div>
    <ul v-else class="attack-list">
      <li 
        v-for="attack in attacks" 
        :key="attack.id" 
        class="attack-list-item"
        :class="{ 
            'is-actionable': mode === 'action', 
            'is-disabled': disabledIds.has(attack.id)
        }"
        @click="handleClick(attack)"
      >
        <AttackCardDisplay :attack="attack" />
      </li>
    </ul>
  </div>
</template>

<style scoped>
.attack-list-mobile {
  width: 100%;
}

.attack-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.75rem;
}

.attack-list-item {
  background-color: var(--color-background);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  padding: 0.75rem;
  transition: background-color 0.2s;
  position: relative;
}

.attack-list-item.is-actionable {
  cursor: pointer;
}

.attack-list-item.is-actionable:hover {
  background-color: var(--color-background-mute);
}

/* Style for disabled items */
.attack-list-item.is-disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background-color: var(--color-background); /* Ensure default background */
}

.attack-list-item.is-disabled:hover {
  /* Prevent hover effect on disabled items */
  background-color: var(--color-background);
}

/* Add hover/selected styles if interaction is added */
/* .attack-list-item.selected { */
/*   border-left: 4px solid var(--primary-color); */
/*   background-color: rgba(var(--primary-color-rgb), 0.05); */
/* } */

.empty-list-message {
  padding: 1.5rem 1rem;
  text-align: center;
  color: var(--color-text-mute);
  font-style: italic;
  border: 1px dashed var(--color-border);
  border-radius: 6px;
  margin-top: 0.5rem;
}

/* Optional selection indicator styling */
/* .list-item-selection-indicator { ... } */

/* Style the AttackCardDisplay within the list item */
.attack-list-item :deep(.attack-card) {
  padding: 0.5rem; 
}
</style> 