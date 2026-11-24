<template><div ref="el" class="chart" :style="{ height }"></div></template>
<script setup>
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import * as echarts from 'echarts'
const props = defineProps({ option: Object, height: { type: String, default: '100%' } })
const el = ref(null); let chart, observer
onMounted(() => { chart = echarts.init(el.value); chart.setOption(props.option); observer = new ResizeObserver(() => chart.resize()); observer.observe(el.value) })
watch(() => props.option, v => chart?.setOption(v, true), { deep: true })
onBeforeUnmount(() => { observer?.disconnect(); chart?.dispose() })
</script>
