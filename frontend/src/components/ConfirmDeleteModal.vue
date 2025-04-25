<script setup>
import AttackCardDisplay from './AttackCardDisplay.vue';

const props = defineProps({
  isOpen: {
    type: Boolean,
    required: true
  },
  attack: {
    type: Object,
    default: null // Allow null when closed
  }
});

const emit = defineEmits(['update:isOpen', 'confirm']);

function closeModal() {
  emit('update:isOpen', false);
}

function confirmDelete() {
  emit('confirm');
  // Optionally close modal here, or let parent handle it after confirm logic
  // closeModal(); 
}
</script>

<template>
  <transition name="modal-fade">
    <div v-if="isOpen" class="modal-overlay" @click.self="closeModal">
      <div class="modal-panel">
        <h3 class="modal-title">Confirm Deletion</h3>

        <div class="modal-content">
          <p>Are you sure you want to permanently delete this attack?</p>
          
          <!-- Attack Preview -->
          <div v-if="attack" class="attack-preview-container">
            <AttackCardDisplay :attack="attack" />
          </div>
          
          <p class="warning-text">This action cannot be undone.</p>
        </div>

        <div class="modal-actions">
          <button @click="closeModal" class="button button-secondary">Keep</button>
          <button @click="confirmDelete" class="button button-danger">Delete</button>
        </div>
      </div>
    </div>
  </transition>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.6);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000; /* Ensure it's on top */
  font-family: var(--font-primary);
}

.modal-panel {
  background-color: var(--color-panel-bg);
  border: var(--border-width) solid var(--color-border);
  padding: var(--panel-padding);
  box-shadow: inset 0 0 0 2px var(--color-bg), 5px 5px 0px var(--color-border);
  border-radius: 0;
  min-width: 300px;
  max-width: 90vw; /* Limit width */
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.modal-title {
  font-size: 1.2em;
  color: var(--color-accent-secondary);
  margin: -15px -15px 0 -15px; /* Match panel title style */
  padding: 8px 15px;
  text-align: center;
  border-bottom: var(--border-width) solid var(--color-border);
  text-transform: uppercase;
  background-color: var(--color-border);
  color: var(--color-text);
  box-shadow: inset 0 0 0 1px var(--color-panel-bg);
}

.modal-content {
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  color: var(--color-text);
  font-size: 1em;
}

.attack-preview-container {
  width: 180px; /* Set a fixed width for the preview */
  margin: 10px 0;
}

.warning-text {
  font-size: 0.9em;
  color: var(--color-accent);
  font-style: italic;
}

.modal-actions {
  display: flex;
  justify-content: space-around; /* Space out buttons */
  gap: 15px;
  margin-top: 10px;
}

/* Button Styles - Assuming global .button, .button-secondary, .button-danger */
.button { /* Base style if not global */
    font-family: var(--font-primary);
    font-size: 0.9em;
    padding: 8px 12px;
    border: var(--border-width) solid var(--color-border);
    background-color: var(--color-accent-secondary);
    color: var(--color-panel-bg);
    cursor: pointer;
    text-align: center;
    transition: background-color 0.2s ease, color 0.2s ease, transform 0.1s ease;
    box-shadow: 2px 2px 0px var(--color-border);
    text-transform: uppercase;
    border-radius: 0;
}
.button:active {
    transform: translate(1px, 1px);
    box-shadow: 1px 1px 0px var(--color-border);
}
.button-secondary { /* Example style */
    background-color: var(--color-border);
    color: var(--color-text);
}
.button-secondary:hover {
     background-color: #555; /* Example hover */
}
.button-danger { /* Example style */
    background-color: var(--color-accent);
    color: var(--color-text);
}
.button-danger:hover {
     background-color: #c0392b; /* Darker red */
}


/* Modal Fade Animation */
.modal-fade-enter-active, .modal-fade-leave-active {
  transition: opacity 0.3s ease;
}
.modal-fade-enter-from, .modal-fade-leave-to {
  opacity: 0;
}
.modal-fade-enter-active .modal-panel, .modal-fade-leave-active .modal-panel {
  transition: transform 0.3s ease;
}
.modal-fade-enter-from .modal-panel, .modal-fade-leave-to .modal-panel {
  transform: scale(0.95);
}

</style> 