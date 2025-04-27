<script setup>
import { computed } from 'vue';

const props = defineProps({
  attack: {
    type: Object,
    required: true
  },
  showDeleteButton: {
    type: Boolean,
    default: false
  },
  isFavorite: {
    type: Boolean,
    default: false
  },
  showFavoriteButton: {
    type: Boolean,
    default: false
  }
});
const emit = defineEmits(['delete-clicked', 'toggle-favorite']);

// You could add computed properties here if needed for display logic,
// e.g., formatting descriptions or determining icons.
const displayEmoji = computed(() => props.attack.emoji || '⚔️');

</script>

<template>
  <div class="attack-card-content">
    <!-- Delete Button (Top Left) -->
    <button
      v-if="showDeleteButton"
      @click.stop="$emit('delete-clicked')"
      class="delete-button"
      title="Delete Attack"
    >
      &times;
    </button>

    <!-- Favorite Button (Bottom Left) -->
    <button
      v-if="showFavoriteButton"
      @click.stop="$emit('toggle-favorite')" 
      class="favorite-button"
      :class="{ 'is-favorited': isFavorite }"
      :title="isFavorite ? 'Unfavorite Attack' : 'Favorite Attack'"
    >

      <!-- Always present, visibility controlled by CSS -->
      <span class="star-icon star-empty">☆</span>
      <span class="star-icon star-filled">★</span>
    </button>

    <!-- Top Right Cost Display -->
    <div v-if="attack.momentum_cost > 0" class="cost-display">
        <span class="energy-symbol">⚡️</span>
        <span class="cost-value">{{ attack.momentum_cost }}</span>
    </div>

    <!-- Main Content -->
    <span class="emoji">{{ attack.emoji || '⚔️' }}</span>
    <h4>{{ attack.name }}</h4>
    <p class="power" v-if="attack.power > 0">Power: {{ attack.power }}</p>
    <p class="desc">{{ attack.description || 'No description' }}</p>
  </div>
</template>

<style scoped>
.attack-card-content {
    position: relative;
    /* text-align: center; */
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
    align-items: center; 
    width: 100%; 
    height: 100%; 
    padding: 5px;
    font-family: var(--font-primary);
    line-height: 1.3;
    border: 2px solid var(--color-border);
    background-color: var(--color-panel-bg);
    box-shadow: 2px 2px 0px var(--color-border);
    border-radius: 0;
}

.cost-display {
    position: absolute;
    top: 3px;
    right: 3px;
    display: flex;
    align-items: center;
    gap: 2px;
    background-color: var(--color-bg);
    padding: 1px 4px;
    border: 1px solid var(--color-border);
    font-size: 0.8em;
    font-weight: normal;
    color: var(--color-momentum-user);
    z-index: 1;
    border-radius: 0;
}

.energy-symbol {
    font-size: 1em;
}

.emoji {
    font-size: 2.5em;
    margin-bottom: 4px;
    margin-top: 8px;
    line-height: 1;
}

h4 {
    margin: 2px 0 4px 0;
    font-size: 1em;
    color: var(--color-accent-secondary);
    font-weight: normal;
    line-height: 1.2;
    text-transform: uppercase;
    text-align: center;
}

.power {
    font-size: 0.9em;
    color: var(--color-stat-up);
    font-weight: normal;
    margin: 0 0 4px 0;
    text-align: center;
}

.desc {
    font-size: 1em;
    color: var(--color-log-system);
    line-height: 1.3;
    margin: auto 0;
    max-width: 95%;
    padding-bottom: 2px;
    text-align: center;
    font-family: 'Roboto', sans-serif;
}

.delete-button {
  position: absolute;
  top: 1px;
  left: 1px;
  /* background-color: #888; */ /* Muted gray background */
  background-color: transparent; /* Make transparent */
  color: #888; /* Muted gray color initially */
  /* border: 1px solid #555; */ /* Darker border */
  border: none; /* Remove border */
  border-radius: 0;
  width: 16px; /* Slightly smaller */
  height: 16px; /* Slightly smaller */
  font-size: 12px; /* Slightly smaller symbol */
  line-height: 14px; /* Adjust line height */
  text-align: center;
  padding: 0;
  cursor: pointer;
  z-index: 2;
  /* box-shadow: 1px 1px 0px var(--color-border); */ /* Removed shadow */
  box-shadow: none;
  transition: background-color 0.2s ease, transform 0.1s ease;
}

.delete-button:hover {
  /* background-color: #a04040; */ /* Muted red on hover */
  background-color: transparent; /* Keep transparent */
  color: #c0392b; /* Make color accent red on hover */
  transform: scale(1.1); /* Add slight scale on hover */
}
.delete-button:active {
   transform: translate(1px, 1px) scale(1.1); /* Keep scale during active click */
   /* box-shadow: none; */ /* Already none */
}

/* --- Favorite Button Styles --- */
.favorite-button {
  position: absolute;
  bottom: 3px; 
  left: 3px;
  background-color: transparent;
  border: none;
  font-size: 1.4em; /* Base size for dimensions */
  width: 1em; /* Size based on font-size */
  height: 1em; /* Size based on font-size */
  padding: 0;
  cursor: pointer;
  z-index: 2;
  box-shadow: none;
  outline: none; /* Remove focus outline */
}

/* Individual star icons */
.favorite-button .star-icon {
  background-color: transparent;
  position: absolute; /* Allow overlap */
  top: 0;
  left: 0;
  width: 100%; /* Fill the button */
  height: 100%; /* Fill the button */
  line-height: 1; /* Center vertically */
  text-align: center; /* Center horizontally */
  transition: opacity 0.2s ease, color 0.2s ease, transform 0.1s ease;
  color: #888; /* Default initial color */
}

.favorite-button:hover {
  background-color: transparent;
}

/* Filled star hidden by default */
.favorite-button .star-filled {
  opacity: 0;
}

/* --- State Logic --- */

/* When favorited: show filled star (yellow), hide empty */
.favorite-button.is-favorited .star-empty {
  opacity: 0;
}
.favorite-button.is-favorited .star-filled {
  opacity: 1;
  color: #f1c40f; /* Filled star color */
}

/* --- Hover Logic --- */

/* When hovering NOT favorited: hide empty, show filled (gold) */
.favorite-button:not(.is-favorited):hover .star-empty {
  opacity: 0;
  transform: scale(1.1); /* Scale effect on hover */
}
.favorite-button:not(.is-favorited):hover .star-filled {
  opacity: 1;
  color: #f39c12; /* Hover color */
  transform: scale(1.5); /* Scale effect on hover */
}

/* When hovering IS favorited: keep filled shown, change color (orange), scale */
.favorite-button.is-favorited:hover .star-filled {
  color: #e67e22; /* Slightly different hover for favorited */
  transform: scale(1.5);
}

/* OLD HOVER/FAVORITED RULES - REMOVE */
/*
.favorite-button:hover {
  color: #f39c12; 
  transform: scale(1.1);
}
.favorite-button.is-favorited {
  color: #f1c40f; 
}
.favorite-button.is-favorited:hover {
  color: #e67e22; 
}
*/
/* --- END Favorite Button Styles --- */
</style> 