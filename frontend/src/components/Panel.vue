<template><section class="panel"><div class="corners"><i></i><i></i><i></i><i></i></div><div class="panel-glow"></div><header><div><h2>{{ title }}</h2><small>{{ subtitle }}</small></div><span></span></header><div class="panel-body"><slot /></div></section></template>
<script setup>defineProps({ title: String, subtitle: String })</script>
