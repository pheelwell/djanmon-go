<script setup>
import { computed } from 'vue';
import AttackCardDisplay from '@/components/AttackCardDisplay.vue';
import draggable from 'vuedraggable'; // <-- Import draggable

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
  }
});

const emit = defineEmits([
  'update:selectedIds', // For v-model support
  'reveal',
  'update:draggableModel' // For v-model support with drag
]);

// --- Computed properties for styling/disabling --- 

const isSelected = (attackId) => {
  return props.mode === 'select' && props.selectedIds.includes(attackId);
};

const isSelectionDisabled = (attackId) => {
  return props.mode === 'select' && 
         props.selectedIds.length >= props.maxSelectable && 
         !props.selectedIds.includes(attackId);
};

const isRevealed = (attackId) => {
  return props.mode === 'reveal' && props.revealedIds.has(attackId);
}

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

function handleClick(attack) {
  if (props.mode === 'select') {
    toggleSelection(attack.id);
  } else if (props.mode === 'reveal') {
    if (!isRevealed(attack.id)) {
        emit('reveal', attack.id);
    }
  }
  // Add other mode handlers later (e.g., drag start)
}

function toggleSelection(attackId) {
  const currentSelected = [...props.selectedIds];
  const index = currentSelected.indexOf(attackId);

  if (index > -1) {
    // Deselect
    currentSelected.splice(index, 1);
  } else {
    // Select if not exceeding max
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
  <div class="attack-grid-component" :class="[`mode-${mode}`]">
    <!-- Basic Grid for Display/Select/Reveal -->
    <div v-if="mode === 'display' || mode === 'select' || mode === 'reveal'" class="attack-grid-layout">
        <div 
            v-for="attack in attacks" 
            :key="attack.id" 
            class="attack-grid-item" 
            :class="{
                'is-selectable': mode === 'select',
                'is-revealable': mode === 'reveal',
                'selected': isSelected(attack.id),
                'disabled': isSelectionDisabled(attack.id),
                'revealed': isRevealed(attack.id)
            }"
            @click="handleClick(attack)"
        >
             <!-- Reveal Mode: Face-down Card -->
            <div v-if="mode === 'reveal' && !isRevealed(attack.id)" class="attack-card-face-down">
                 <span class="reveal-prompt">Click to Reveal</span>
            </div>
            <!-- Default: Attack Card Display -->
            <AttackCardDisplay 
                v-else
                :attack="attack" 
            />
        </div>
    </div>

    <!-- Draggable Grid -->
    <draggable 
      v-if="mode === 'drag'" 
      v-model="localDraggableModel" 
      class="attack-grid-layout draggable-grid" 
      :group="groupName" 
      item-key="id" 
      :component-data="{ name: 'fade' }" 
      v-bind="computedDragOptions"
      :move="move"
    >
        <template #header>
           <div v-if="!localDraggableModel || localDraggableModel.length === 0" class="empty-grid-message">
               <slot name="empty">No attacks here.</slot> 
           </div>
        </template>
        <template #item="{element}">
             <div class="attack-grid-item is-draggable">
                <AttackCardDisplay :attack="element"/>
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
.attack-grid-component {
  /* Basic container styling */
}

.attack-grid-layout {
  display: grid;
  /* Responsive columns */
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 1rem;
  padding: 0.5rem; /* Padding around the grid */
  /* Center the grid items horizontally - may not be needed with auto-fit/minmax */
  /* justify-content: center; */ 
}

.attack-grid-item {
  position: relative; /* For indicators */
  background-color: var(--color-background);
  border: 1px solid var(--color-border-hover);
  border-radius: 8px;
  /* REMOVED fixed width */
  /* width: 180px; */
  height: 180px; /* <-- Increased height (Keep for now, maybe adjust later) */
  padding: 0.5rem; /* Padding inside the card wrapper */
  display: flex; 
  flex-direction: column; 
  justify-content: center; 
  align-items: center; 
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
  overflow: hidden; 
}

/* --- Interaction Styles --- */

.attack-grid-item.is-selectable,
.attack-grid-item.is-revealable {
  cursor: pointer;
}

.attack-grid-item.is-selectable:hover:not(.disabled) {
  transform: translateY(-3px);
  box-shadow: 0 4px 8px rgba(0,0,0,0.1);
  border-color: var(--vt-c-indigo); 
}

.attack-grid-item.selected {
  border-color: var(--primary-color); 
  background-color: rgba(var(--primary-color-rgb), 0.1); 
}

.attack-grid-item.disabled {
  opacity: 0.5; 
  cursor: not-allowed;
  border-color: var(--color-border-hover); /* Reset border */
  background-color: var(--color-background); /* Reset background */
  transform: none;
  box-shadow: none;
}

/* --- Reveal Mode Styles --- */
.attack-card-face-down {
  width: 100%;
  height: 100%;
  background-color: var(--color-background-mute);
  border: 2px dashed var(--color-border-hover);
  display: flex;
  justify-content: center;
  align-items: center;
  color: var(--color-text-muted);
  font-size: 0.9em;
  font-style: italic;
  border-radius: 6px; 
  box-sizing: border-box; 
  transition: background-color 0.2s;
}

.attack-card-face-down:hover {
  background-color: var(--color-background-soft);
}

.empty-grid-message {
  padding: 2rem 1rem;
  text-align: center;
  color: var(--color-text-mute);
  font-style: italic;
  border: 1px dashed var(--color-border);
  border-radius: 6px;
  margin-top: 0.5rem;
}

/* Ensure draggable grid also gets layout styles */
.attack-grid-layout.draggable-grid {
  min-height: 150px; /* Ensure dropzone has min height */
  /* Add other specific styles for the draggable area if needed */
  background-color: var(--color-background-mute); /* Example background */
  border: 1px solid var(--color-border); /* Example border */
  border-radius: 8px;
  /* NEW: Add transition for background change */
  transition: background-color 0.2s ease;
}

/* NEW: Style when draggable grid is empty */
.attack-grid-layout.draggable-grid:has(.empty-grid-message) {
  background-color: var(--color-background-soft); /* Slightly different bg when empty */
  border-style: dashed; /* Dashed border when empty */
}

.attack-grid-item {
  overflow: hidden; 
}

/* --- Interaction Styles --- */

.attack-grid-item.is-draggable {
  cursor: grab;
}

.attack-grid-item.is-draggable:active {
  cursor: grabbing;
}

/* Add styles for vuedraggable ghost/chosen if needed */
.attack-grid-layout.draggable-grid .ghost {
  opacity: 0.4;
  background: var(--color-background-soft);
  border: 2px dashed var(--vt-c-indigo);
  border-radius: 8px;
}

/* Add other draggable styles if needed */

/* --- Selection Styles --- */

.attack-grid-item.is-selectable,
.attack-grid-item.is-revealable {
  cursor: pointer;
}

.attack-grid-item.is-selectable:hover:not(.disabled) {
  transform: translateY(-3px);
  box-shadow: 0 4px 8px rgba(0,0,0,0.1);
  border-color: var(--vt-c-indigo); 
}

.attack-grid-item.selected {
  border-color: var(--primary-color); 
  background-color: rgba(var(--primary-color-rgb), 0.1); 
}

.attack-grid-item.disabled {
  opacity: 0.5; 
  cursor: not-allowed;
  border-color: var(--color-border-hover); /* Reset border */
  background-color: var(--color-background); /* Reset background */
  transform: none;
  box-shadow: none;
}

</style> 