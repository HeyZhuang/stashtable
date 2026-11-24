<template><div class="kpi"><span class="kpi-icon">{{ icon }}</span><div><small>{{ label }}</small><div><b class="kpi-number">{{ displayValue }}</b><em>{{ unit }}</em></div></div><i class="kpi-line"></i></div></template>
<script setup>
import { ref, watch, onMounted } from 'vue'
const props = defineProps({ label: String, value: Number, unit: String, icon: String })
const displayValue = ref('0')
let animationId = null

function animateNumber(target) {
  if (animationId) cancelAnimationFrame(animationId)
  const start = parseInt(displayValue.value.replace(/,/g, '')) || 0
  const end = target || 0
  const duration = 800
  const startTime = performance.now()

  function tick(now) {
    const elapsed = now - startTime
    const progress = Math.min(elapsed / duration, 1)
    // easeOutQuart
    const ease = 1 - Math.pow(1 - progress, 4)
    const current = Math.floor(start + (end - start) * ease)
    displayValue.value = current.toLocaleString()
    if (progress < 1) animationId = requestAnimationFrame(tick)
  }
  animationId = requestAnimationFrame(tick)
}

watch(() => props.value, (v) => animateNumber(v), { immediate: true })
onMounted(() => animateNumber(props.value))
</script>
