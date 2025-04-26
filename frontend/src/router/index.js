import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import LoginView from '../views/LoginView.vue'
import RegisterView from '../views/RegisterView.vue'
import BattleView from '../views/BattleView.vue'
import OnboardingView from '../views/OnboardingView.vue'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
      meta: { requiresAuth: true },
      beforeEnter: (to, from, next) => {
        const authStore = useAuthStore();
        const user = authStore.currentUser;
        const tutorialCompleted = localStorage.getItem('gengoTutorialCompleted') === 'true';

        console.log("[Home Route Guard] Checking onboarding needs...");
        console.log(`[Home Route Guard] User Authenticated: ${authStore.isAuthenticated}`);
        console.log(`[Home Route Guard] User data available: ${!!user}`);
        console.log(`[Home Route Guard] Attacks count: ${user?.attacks?.length}`);
        console.log(`[Home Route Guard] Selected attacks count: ${user?.selected_attacks?.length}`);
        console.log(`[Home Route Guard] Tutorial completed: ${tutorialCompleted}`);

        const needsOnboarding = user && 
                              Array.isArray(user.attacks) && 
                              Array.isArray(user.selected_attacks) && 
                              user.attacks.length === 0 && 
                              user.selected_attacks.length === 0 && 
                              !tutorialCompleted;
        
        console.log(`[Home Route Guard] Needs Onboarding: ${needsOnboarding}`);

        if (needsOnboarding) {
          console.log("[Home Route Guard] Redirecting to /onboarding");
          next({ name: 'onboarding' });
        } else {
          console.log("[Home Route Guard] Proceeding to /home");
          next();
        }
      }
    },
    {
      path: '/onboarding',
      name: 'onboarding',
      component: OnboardingView,
      meta: { requiresAuth: true }
    },
    {
      path: '/login',
      name: 'login',
      component: LoginView,
      meta: { requiresGuest: true }
    },
    {
      path: '/register',
      name: 'register',
      component: RegisterView,
      meta: { requiresGuest: true }
    },
    {
      path: '/battle/:id',
      name: 'battle',
      component: BattleView,
      meta: { requiresAuth: true },
      props: true
    }
  ],
})

router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore();
  
  if (!authStore.currentUser && authStore.isAuthenticated && to.meta.requiresAuth) {
    console.log("[Global Guard] No user data, attempting fetch...");
    try {
      await authStore.fetchUserProfile();
      console.log("[Global Guard] User fetch successful.");
    } catch (error) {
      console.error("[Global Guard] Failed to fetch user on route guard:", error);
      authStore.logout();
      next({ name: 'login' });
      return;
    }
  }

  const isAuthenticated = authStore.isAuthenticated;

  if (to.meta.requiresAuth && !isAuthenticated) {
    console.log(`[Global Guard] Route ${to.path} requires auth, redirecting to login.`);
    next({ name: 'login' });
  } else if (to.meta.requiresGuest && isAuthenticated) {
    console.log(`[Global Guard] Route ${to.path} requires guest, redirecting to home.`);
    next({ name: 'home' });
  } else {
    if (to.name === 'onboarding') {
      console.log("[Global Guard] Allowing navigation to /onboarding.");
      next();
      return;
    }
    
    console.log(`[Global Guard] Allowing navigation to ${to.path}`);
    next();
  }
});

export default router
