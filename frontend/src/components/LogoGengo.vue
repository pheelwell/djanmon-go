<template>
  <div class="gengo-logo">
    <span>GEN</span><span class="go-part">GO</span>
  </div>
</template>

<style scoped>
.gengo-logo {
  font-family: var(--font-primary); /* Use primary pixel font */
  font-size: 4em; /* Make it large */
  color: var(--color-accent-secondary); /* Use accent color */
  text-align: center;
  margin-bottom: 1.5rem; /* Space below the logo */
  text-transform: uppercase;
  letter-spacing: 2px;
  /* Add a retro pixel shadow effect */
  text-shadow: 3px 3px 0px var(--color-border);
  /* Optional: Add slight animation? */
  animation: pulse 2s infinite ease-in-out;
  position: relative; /* Needed for pseudo-element positioning */
}

/* Style the "GO" part */
.gengo-logo .go-part {
  color: var(--color-text); /* Or use #fff or another white variable */
}

/* Sparkle Pseudo-elements */
.gengo-logo::before,
.gengo-logo::after {
  content: '✨'; /* Use sparkle emoji or other character/shape */
  position: absolute;
  font-size: 0.4em; /* Size of the sparkle */
  opacity: 0;
  animation: sparkle 1.5s infinite ease-in-out;
  /* Prevent pseudo-elements interfering with text selection */
  pointer-events: none; 
}

.gengo-logo::before {
  top: 10%;
  left: 5%;
  animation-delay: 0.2s; /* Stagger the sparkles */
}

.gengo-logo::after {
  bottom: 15%;
  right: 5%;
  animation-delay: 0.7s; /* Stagger the sparkles */
}

/* Optional pulsing animation */
@keyframes pulse {
  0%, 100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.02);
    opacity: 0.95;
  }
}

/* Sparkle Animation */
@keyframes sparkle {
  0%, 100% {
    opacity: 0;
    transform: scale(0.8) rotate(0deg);
  }
  25%, 75% {
    opacity: 1;
    transform: scale(1.1) rotate(15deg);
  }
  50% {
     opacity: 0.7;
     transform: scale(1) rotate(-10deg);
  }
}
</style> 