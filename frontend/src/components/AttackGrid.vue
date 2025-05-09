<script setup>
import { computed } from 'vue';
import AttackCardDisplay from '@/components/AttackCardDisplay.vue';

const props = defineProps({
  attacks: {
    type: Array,
    required: true
  },
  mode: {
    type: String,
    default: 'display', // 'display', 'select', 'reveal', 'drag'
    validator: (value) => ['display', 'select', 'reveal', 'drag'].includes(value) // <-- Add 'drag'
  },
  // Props for 'select' mode
  selectedIds: { // Use v-model:selectedIds in parent
    type: Array,
    default: () => []
  },
  maxSelectable: {
    type: Number,
    default: Infinity
  },
  // Props for 'reveal' mode
  revealedIds: { // Pass Set directly
    type: Set,
    default: () => new Set()
  },
  // Props for 'drag' mode 
  draggableModel: { // Use v-model:draggableModel in parent
    type: Array, 
    default: () => [] 
  }, 
  groupName: { 
    type: String, 
    default: 'attacks' 
  },
  // Allow passing custom drag options if needed
  dragOptions: { 
    type: Object,
    default: () => ({ animation: 200, ghostClass: 'ghost' })
  },
  // Allow passing the :move validation function
  move: {
      type: Function,
      default: null
  },
  disabled: { // <-- Add disabled prop
    type: Boolean,
    default: false
  },
  allowDeletion: { // <-- Add prop
    type: Boolean,
    default: false
  },
  showFavoriteButton: { // <-- ADDED
    type: Boolean,
    default: false
  },
  favoriteAttackIds: { // <-- ADDED (Using Set for efficiency)
    type: Set,
    default: () => new Set()
  }
});

const emit = defineEmits([
  'update:selectedIds', // For v-model support
  'reveal',
  'update:draggableModel', // For v-model support with drag
  'attackClick', // <-- Add attackClick here
  'deleteAttack', // <-- Add emit
  'toggleFavorite' // <-- ADDED
]);

// --- Computed properties for styling/disabling --- 

const isSelected = (attackId) => {
  return props.mode === 'select' && props.selectedIds.includes(attackId);
};

// Rename this to distinguish from the main disabled prop
const isSelectionActionDisabled = (attackId) => {
  return props.mode === 'select' && 
         props.selectedIds.length >= props.maxSelectable && 
         !props.selectedIds.includes(attackId);
};

const isRevealed = (attackId) => {
  return props.mode === 'reveal' && props.revealedIds.has(attackId);
}

const isAttackFavorite = (attackId) => {
    return props.favoriteAttackIds.has(attackId);
};

// --- Draggable Setup --- 
// Emit update event when draggable model changes internally
const localDraggableModel = computed({
  get: () => props.draggableModel,
  set: (value) => {
    emit('update:draggableModel', value);
  }
});

// Define default draggable options (can be overridden by prop)
const computedDragOptions = computed(() => ({
    animation: 200,
    ghostClass: 'ghost', // Default ghost class
    ...props.dragOptions, // Merge prop options
    group: props.groupName // Ensure group name is set
}));

// --- Event Handlers --- 

// Combined click handler
function handleItemClick(attack) {
  // Prevent click if the whole grid is disabled
  if (props.disabled) {
      return;
  }
  // Prevent click if selection action is disabled (only in select mode)
  if (props.mode === 'select' && isSelectionActionDisabled(attack.id)) {
      return;
  }

  // Always emit the generic attackClick event for the parent
  emit('attackClick', attack);

  // Handle mode-specific logic internally if needed
  if (props.mode === 'select') {
    toggleSelection(attack.id);
  } else if (props.mode === 'reveal') {
    if (!isRevealed(attack.id)) {
      emit('reveal', attack.id);
    }
  }
}

// Keep toggleSelection for select mode logic
function toggleSelection(attackId) {
  const currentSelected = [...props.selectedIds];
  const index = currentSelected.indexOf(attackId);

  if (index > -1) {
    currentSelected.splice(index, 1);
  } else {
    if (currentSelected.length < props.maxSelectable) {
      currentSelected.push(attackId);
    }
  }
  emit('update:selectedIds', currentSelected);
}

// Optional: Add a checkMove function if needed (can be passed as prop later)
// function checkMove(evt) { ... }

</script>

<template>
  <div class="attack-grid-component" :class="[`mode-${mode}`, { 'grid-disabled': disabled }]">
    <!-- Basic Grid for Display/Select/Reveal/Action -->
    <!-- Combine conditions as the structure is the same -->
    <transition-group 
        v-if="mode === 'display' || mode === 'select' || mode === 'reveal' || mode === 'action'" 
        tag="div" 
        name="grid-fade" 
        class="attack-grid-layout"
    >
        <div 
            v-for="attack in attacks" 
            :key="attack.id" 
            class="attack-grid-item" 
            :class="{
                'is-selectable': mode === 'select',
                'is-revealable': mode === 'reveal',
                'is-actionable': mode === 'action', // Add class for action mode styling
                'selected': isSelected(attack.id),
                // Use specific select mode disabling for styling, main disable is on container
                'selection-disabled': isSelectionActionDisabled(attack.id),
                'revealed': isRevealed(attack.id)
            }"
            @click="handleItemClick(attack)"  
        >
             <!-- Reveal Mode: Wrapper for Flip -->
            <div v-if="mode === 'reveal'" class="reveal-card-wrapper" :class="{'is-flipped': isRevealed(attack.id)}">
                <!-- Face Down -->
                <div class="reveal-card-face reveal-card-back">
                    <span class="reveal-prompt">Click to Reveal</span>
                </div>
                <!-- Face Up (Attack Card) -->
                <div class="reveal-card-face reveal-card-front">
                    <AttackCardDisplay
                        :attack="attack"
                        :showDeleteButton="allowDeletion" 
                        :isFavorite="isAttackFavorite(attack.id)" 
                        :showFavoriteButton="showFavoriteButton"
                        @delete-clicked="$emit('deleteAttack', attack)"
                        @toggle-favorite="$emit('toggleFavorite', attack.id)"
                    />
                </div>
            </div>

            <!-- Default Display (Non-Reveal Modes, including Select) -->
            <AttackCardDisplay
                v-else
                :attack="attack"
                :showDeleteButton="allowDeletion && mode !== 'reveal'" 
                :isFavorite="isAttackFavorite(attack.id)" 
                :showFavoriteButton="showFavoriteButton"
                @delete-clicked="$emit('deleteAttack', attack)"
                @toggle-favorite="$emit('toggleFavorite', attack.id)"
            ></AttackCardDisplay>
        </div>
    </transition-group>

    <!-- Draggable Grid -->
    <draggable 
      v-if="mode === 'drag'" 
      v-model="localDraggableModel" 
      class="attack-grid-layout draggable-grid" 
      :group="groupName" 
      item-key="id" 
      :component-data="{ name: 'grid-fade' }" 
      v-bind="computedDragOptions"
      :move="move"
      :disabled="disabled"
    >
        <template #header>
           <div v-if="!localDraggableModel || localDraggableModel.length === 0" class="empty-grid-message">
               <slot name="empty">No attacks here.</slot> 
           </div>
        </template>
        <template #item="{element}">
             <div class="attack-grid-item is-draggable">
                <AttackCardDisplay 
                  :attack="element" 
                  :showDeleteButton="allowDeletion"
                  :isFavorite="isAttackFavorite(element.id)"
                  :showFavoriteButton="showFavoriteButton"
                  @delete-clicked="$emit('deleteAttack', element)"
                  @toggle-favorite="$emit('toggleFavorite', element.id)"
                ></AttackCardDisplay>
            </div>
        </template>
    </draggable>

    <!-- Empty State (Only for non-drag modes now) -->
    <div v-if="mode !== 'drag' && (!attacks || attacks.length === 0)" class="empty-grid-message">
        <slot name="empty">No attacks to display.</slot> 
    </div>
  </div>
</template>

<style scoped>
.attack-grid-layout {
  display: grid;
  /* Responsive columns with fixed pixel base for retro look */
  grid-template-columns: repeat(auto-fit, minmax(110px, 1fr)); /* Keep smaller min size */
  gap: var(--element-gap); /* Use theme gap */
  padding: 5px; /* Inner padding for the grid container */
  /* Remove background/border from here, apply to component or parent panel */
}

.attack-grid-item {
  /* Container for each AttackCardDisplay */
  /* Remove background/border, let AttackCardDisplay handle its own */
  background-color: transparent;
  border: none;
  padding: 0; /* No padding on the item itself */
  display: flex; /* Use flex for alignment */
  justify-content: center;
  align-items: stretch; /* Make children fill the height */
  transition: transform 0.1s ease;
  height: 180px; /* << SET FIXED HEIGHT */
}

/* --- Interaction Styles --- */

/* Hover effect ONLY if the grid is NOT disabled */
.attack-grid-component:not(.grid-disabled) .attack-grid-item:hover:not(.selection-disabled) {
    cursor: pointer;
    transform: scale(1.03); /* Keep slight scale effect */
}

/* Apply visual changes to the inner card on hover */
.attack-grid-component:not(.grid-disabled) .attack-grid-item:hover:not(.selection-disabled) > .attack-card-content {
    border-color: var(--color-accent-secondary); /* Highlight border */
    box-shadow: 2px 2px 0px var(--color-accent-secondary); /* Highlight shadow */
}

/* Selected Style (Applies regardless of disabled state?) */
.attack-grid-item.selected > .attack-card-content {
  /* Use primary accent for selected border */
  border-color: var(--color-accent); 
  box-shadow: 2px 2px 0px var(--color-accent); 
}

/* Style for specific selection disabled (e.g., max reached in select mode) */
.attack-grid-item.selection-disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.attack-grid-item.selection-disabled > .attack-card-content {
  border-color: var(--color-border);
  box-shadow: 1px 1px 0px var(--color-border); 
  transform: none;
}

/* NEW: Style for when the ENTIRE grid is disabled */
.attack-grid-component.grid-disabled .attack-grid-item {
    opacity: 0.5; /* Dim all items */
    cursor: default; /* Change cursor */
    transform: none; /* Prevent scaling */
}
.attack-grid-component.grid-disabled .attack-grid-item > .attack-card-content {
    border-color: var(--color-border); /* Reset border */
    box-shadow: 1px 1px 0px var(--color-border); /* Reset shadow */
}

/* --- Reveal Mode Styles --- */

/* NEW: Reveal Mode Flip Structure */
.reveal-card-wrapper {
  width: 100%;
  height: 100%;
  min-height: 150px; /* Match item min-height */
  position: relative;
  perspective: 1000px; /* Add perspective for 3D effect */
  transform-style: preserve-3d;
  transition: transform 0.6s;
}

.reveal-card-face {
  position: absolute;
  width: 100%;
  height: 100%;
  backface-visibility: hidden; /* Hide the back face when rotated */
  display: flex;
  justify-content: center;
  align-items: center;
}

/* Back face (visible initially) */
.reveal-card-back {
  background-color: var(--color-bg); 
  border: 2px dashed var(--color-border);
  color: var(--color-text);
  font-size: 0.9em;
  font-family: var(--font-primary);
  border-radius: 0;
  box-sizing: border-box; 
  text-transform: uppercase;
  transform: rotateY(0deg); /* Initial state */
}

/* Front face (hidden initially) */
.reveal-card-front {
  transform: rotateY(180deg); /* Rotated away initially */
}

/* Apply rotation when the card is flipped */
.reveal-card-wrapper.is-flipped {
  transform: rotateY(180deg);
}

/* OLD Face-down Styles (Remove or comment out) */
/*
.attack-card-face-down {
  width: 100%;
  height: 100%;
  min-height: 150px;
  background-color: var(--color-bg); 
  border: 2px dashed var(--color-border);
  display: flex;
  justify-content: center;
  align-items: center;
  color: var(--color-text);
  font-size: 0.9em;
  font-family: var(--font-primary);
  border-radius: 0;
  box-sizing: border-box; 
  transition: background-color 0.2s;
  text-transform: uppercase;
}
.attack-grid-component:not(.grid-disabled) .attack-card-face-down:hover {
  background-color: var(--color-panel-bg);
  border-color: var(--color-accent-secondary);
  color: var(--color-accent-secondary);
  cursor: pointer;
}
*/

.empty-grid-message {
  padding: 20px 10px;
  text-align: center;
  color: var(--color-log-system); /* Match log empty */
  font-style: italic;
  border: 1px dashed var(--color-border);
  border-radius: 0;
  margin-top: 5px;
  font-family: var(--font-primary);
  text-transform: uppercase;
  font-size: 1em;
}

/* Draggable Specific Styles */
.attack-grid-layout.draggable-grid {
  min-height: 150px; 
  background-color: rgba(0,0,0,0.1); /* Faint bg for dropzone */
  border: 1px dashed var(--color-border);
  border-radius: 0;
  transition: background-color 0.2s ease;
}

.attack-grid-layout.draggable-grid:has(.empty-grid-message) {
  background-color: transparent; /* No background when empty */
  border-style: dashed;
}

/* Style the draggable item itself */
.attack-grid-item.is-draggable {
  cursor: grab;
}

.attack-grid-item.is-draggable:active {
  cursor: grabbing;
}

/* Style the ghost element during drag */
.attack-grid-layout.draggable-grid .ghost {
  opacity: 0.4;
  background: var(--color-panel-bg);
  border: 2px dashed var(--color-accent-secondary);
  border-radius: 0;
}
.attack-grid-layout.draggable-grid .ghost > * {
    /* Hide the content of the ghost card */
    visibility: hidden;
}

/* Remove redundant interaction styles */

/* --- Transition Group Animations --- */
.grid-fade-move, /* moving */
.grid-fade-enter-active,
.grid-fade-leave-active {
  transition: all 0.3s ease; /* Adjust timing/easing as needed */
}

.grid-fade-enter-from,
.grid-fade-leave-to {
  opacity: 0;
  transform: scale(0.95); /* Optional scale */
}

/* Ensure leaving items are taken out of layout flow smoothly */
.grid-fade-leave-active {
  position: absolute; /* Important for layout shifts */
  /* Attempt to maintain size during leave */
  /* You might need to adjust this based on the actual grid item size */
   width: 110px; 
}

/* If using a background on items, you might need this */
.grid-fade-leave-active {
  z-index: 0; 
}
.grid-fade-enter-active {
    z-index: 1;
}

</style> 