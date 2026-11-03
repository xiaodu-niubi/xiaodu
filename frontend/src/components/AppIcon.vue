<template>
  <svg :width="size" :height="size" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <template v-if="name === 'plus'"><path d="M12 5v14M5 12h14" /></template>
    <template v-else-if="name === 'chat'"><path d="M21 11.5a8.5 8.5 0 0 1-8.5 8.5H4l-2 2V11.5a9.5 9.5 0 0 1 19 0Z" /></template>
    <template v-else-if="name === 'library'"><path d="M4 3h5v18H4zM12 3h4v18h-4zM19 4l3 16" /></template>
    <template v-else-if="name === 'file'"><path d="M14 2H5v20h14V7l-5-5Z"/><path d="M14 2v6h5M8 12h8M8 16h6"/></template>
    <template v-else-if="name === 'search'"><circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/></template>
    <template v-else-if="name === 'arrow'"><path d="M12 19V5m-6 6 6-6 6 6"/></template>
    <template v-else-if="name === 'right'"><path d="M5 12h14m-6-6 6 6-6 6"/></template>
    <template v-else-if="name === 'close'"><path d="m6 6 12 12M6 18 18 6"/></template>
    <template v-else-if="name === 'panel'"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M15 4v16"/></template>
    <template v-else-if="name === 'menu'"><path d="M4 6h16M4 12h16M4 18h16"/></template>
    <template v-else-if="name === 'globe'"><circle cx="12" cy="12" r="9"/><ellipse cx="12" cy="12" rx="4" ry="9"/><path d="M3 12h18"/></template>
    <template v-else-if="name === 'compare'"><rect x="3" y="3" width="7" height="18" rx="1.5"/><rect x="14" y="3" width="7" height="18" rx="1.5"/><path d="M6 8h1m-1 4h1m10-4h1m-1 4h1"/></template>
    <template v-else-if="name === 'check'"><path d="m5 12 4 4L19 6"/></template>
    <template v-else-if="name === 'copy'"><rect x="8" y="8" width="13" height="13" rx="2"/><path d="M16 8V3H3v13h5"/></template>
    <template v-else-if="name === 'download'"><path d="M12 3v12m-5-5 5 5 5-5M4 17v4h16v-4"/></template>
    <template v-else-if="name === 'edit'"><path d="m15 4 5 5M3 21l2-7L17 2l5 5-12 12-7 2Z"/></template>
    <template v-else-if="name === 'refresh'"><path d="M20 7a9 9 0 1 0 1 9M20 3v5h-5"/></template>
    <template v-else-if="name === 'upload'"><path d="M12 16V3m-5 5 5-5 5 5M4 15v6h16v-6"/></template>
    <template v-else-if="name === 'trash'"><path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7m4-7v7"/></template>
    <template v-else-if="name === 'sun'"><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1 1m12 12 1 1M5 19l1-1M18 6l1-1"/></template>
    <template v-else-if="name === 'moon'"><path d="M20 15a9 9 0 0 1-11-11 9 9 0 1 0 11 11Z"/></template>
    <template v-else-if="name === 'chevron'"><path d="m6 9 6 6 6-6"/></template>
    <template v-else-if="name === 'spark'"><path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5L12 3Z"/></template>
    <template v-else-if="name === 'stop'"><rect x="7" y="7" width="10" height="10" rx="1"/></template>
  </svg>
</template>
<script setup>
defineProps({ name: String, size: { type: [Number, String], default: 20 } })
</script>
