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
  font-family: var(--font-primary);
}

.attack-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column; /* Stack items vertically */
  gap: var(--element-gap); /* Use theme gap */
}

.attack-list-item {
  /* Let AttackCardDisplay handle background and border */
  background-color: transparent;
  border: none;
  border-radius: 0;
  padding: 0; /* Remove padding */
  transition: transform 0.1s ease;
  position: relative;
}

.attack-list-item.is-actionable {
  cursor: pointer;
}

/* Apply hover style directly to the card */
.attack-list-item.is-actionable:hover:not(.is-disabled) > :deep(.attack-card-content) {
  transform: scale(1.02); /* Slight scale */
  border-color: var(--color-accent-secondary);
  box-shadow: 2px 2px 0px var(--color-accent-secondary);
}

/* Style for disabled items */
.attack-list-item.is-disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.attack-list-item.is-disabled > :deep(.attack-card-content) {
   border-color: var(--color-border);
   box-shadow: 1px 1px 0px var(--color-border); 
   transform: none;
}


/* Add selected styles if needed (e.g., for favorite selection) */
.attack-list-item.is-selected > :deep(.attack-card-content) { 
  border-color: var(--color-accent);
  box-shadow: 2px 2px 0px var(--color-accent);
}


.empty-list-message {
  padding: 20px 10px;
  text-align: center;
  color: var(--color-log-system);
  font-style: italic;
  border: 1px dashed var(--color-border);
  border-radius: 0;
  margin-top: 5px;
  text-transform: uppercase;
  font-size: 1em;
}

/* Remove deep selector if not needed */
/* .attack-list-item :deep(.attack-card) { ... } */

</style> 