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
  },
  selectedIdsSet: {
    type: Set,
    default: () => new Set()
  },
  allowDeletion: {
    type: Boolean,
    default: false
  },
  showFavoriteButton: {
    type: Boolean,
    default: false
  },
  favoriteAttackIds: {
    type: Set,
    default: () => new Set()
  }
});

const emit = defineEmits(['attackClick', 'deleteAttack', 'toggleFavorite']);

function handleClick(attack) {
  if (props.mode !== 'action' || props.disabledIds.has(attack.id)) {
    return; 
  }
  emit('attackClick', attack);
}

const isAttackFavorite = (attackId) => {
    return props.favoriteAttackIds.has(attackId);
};
</script>

<template>
  <div class="attack-list-mobile">
    <div 
      v-if="!attacks || attacks.length === 0" 
      class="empty-list-message"
    >
      <slot name="empty">No attacks to display.</slot>
    </div>
    <transition-group v-else tag="ul" name="list-fade" class="attack-list">
      <li 
        v-for="attack in attacks" 
        :key="attack.id" 
        class="attack-list-item"
        :class="{ 
            'is-actionable': mode === 'action', 
            'is-selected': selectedIdsSet.has(attack.id)
        }"
        @click="handleClick(attack)"
      >
        <AttackCardDisplay 
          :attack="attack" 
          :showDeleteButton="allowDeletion"
          :isFavorite="isAttackFavorite(attack.id)"
          :showFavoriteButton="showFavoriteButton"
          @delete-clicked="$emit('deleteAttack', attack)"
          @toggle-favorite="$emit('toggleFavorite', attack.id)"
        />
      </li>
    </transition-group>
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
.attack-list-item.is-actionable:hover:not(.is-selected) > :deep(.attack-card-content) {
  transform: scale(1.02); /* Slight scale */
  border-color: var(--color-accent-secondary);
  box-shadow: 2px 2px 0px var(--color-accent-secondary);
}

/* Style for selected items */
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

/* --- Transition Group Animations --- */
.list-fade-move,
.list-fade-enter-active,
.list-fade-leave-active {
  transition: all 0.3s ease;
}

.list-fade-enter-from,
.list-fade-leave-to {
  opacity: 0;
  transform: translateY(10px); /* Slide effect for list */
}

/* Ensure leaving items are taken out of layout flow smoothly */
.list-fade-leave-active {
  position: absolute;
  width: 100%; /* Ensure it takes full width while leaving */
  z-index: 0;
}

.list-fade-enter-active {
    z-index: 1;
}

</style> 