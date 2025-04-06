<script setup>
import { RouterLink, RouterView } from 'vue-router'
</script>

<template>
  <header>
    <nav>
      <RouterLink to="/">Home</RouterLink>
      <RouterLink to="/leaderboard">Leaderboard</RouterLink>
    </nav>
  </header>

  <RouterView />
</template>

<style scoped>
header {
  line-height: 1.5;
  padding: 1rem 0;
  border-bottom: 1px solid var(--color-border);
  margin-bottom: 2rem;
}

nav {
  width: 100%;
  font-size: 1rem; 
  text-align: center;
}

nav a.router-link-exact-active {
  color: var(--color-text);
  font-weight: bold; 
}

nav a.router-link-exact-active:hover {
  background-color: transparent;
}

nav a {
  display: inline-block;
  padding: 0 1rem;
}

</style>
