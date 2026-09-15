<!-- 应用壳只负责承载路由视图，页面布局由路由页面决定。 -->
<template>
  <div
    class="route-progress"
    :class="{ 'route-progress-visible': isNavigating }"
    aria-hidden="true"
  >
    <span></span>
  </div>
  <router-view />
</template>

<script setup lang="ts">
import { isNavigating } from './router'
</script>

<style scoped>
.route-progress {
  position: fixed;
  z-index: 1000;
  top: 0;
  left: 0;
  width: 100%;
  height: 3px;
  pointer-events: none;
  opacity: 0;
  transition: opacity 120ms ease;
}

.route-progress-visible {
  opacity: 1;
}

.route-progress span {
  display: block;
  width: 42%;
  height: 100%;
  background: var(--accent);
  box-shadow: 0 0 14px rgba(110, 231, 210, 0.85);
  animation: route-progress 900ms ease-in-out infinite;
}

@keyframes route-progress {
  0% {
    transform: translateX(-110%);
  }

  100% {
    transform: translateX(260%);
  }
}
</style>
