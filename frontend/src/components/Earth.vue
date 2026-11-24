<template><div ref="container" class="earth"></div></template>
<script setup>
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
const props = defineProps({ iss: Object, satellites: Array })
const emit = defineEmits(['select-satellite', 'drag'])
const container = ref(null)
let scene, camera, renderer, earth, clouds, frame, observer, particles, controls
let satelliteMarkers = {}  // { noradId: {group, trail} }
let satelliteTrails = {}   // { noradId: [Vector3] }
let meteors = []           // 流星
let raycaster, mouse, hoverMarker = null

function latLng(lat, lng, radius = 2.06) {
  const phi = (90 - lat) * Math.PI / 180, theta = (lng + 180) * Math.PI / 180
  return new THREE.Vector3(-radius * Math.sin(phi) * Math.cos(theta), radius * Math.cos(phi), radius * Math.sin(phi) * Math.sin(theta))
}

function makeEarthTexture() {
  const canvas = document.createElement('canvas'); canvas.width = 1024; canvas.height = 512
  const c = canvas.getContext('2d'), g = c.createLinearGradient(0, 0, 0, 512)
  g.addColorStop(0, '#061526'); g.addColorStop(.48, '#0b3450'); g.addColorStop(1, '#05111f'); c.fillStyle = g; c.fillRect(0, 0, 1024, 512)
  c.strokeStyle = 'rgba(58,142,178,.17)'; c.lineWidth = 1
  for (let i = 0; i <= 24; i++) { c.beginPath(); c.moveTo(i * 1024 / 24, 0); c.lineTo(i * 1024 / 24, 512); c.stroke() }
  for (let i = 0; i <= 12; i++) { c.beginPath(); c.moveTo(0, i * 512 / 12); c.lineTo(1024, i * 512 / 12); c.stroke() }
  const continents = [
    [[80,105],[135,72],[192,78],[236,110],[260,156],[238,187],[213,187],[195,234],[167,264],[151,230],[126,211],[107,173],[82,158]],
    [[228,273],[263,282],[284,319],[275,353],[262,398],[243,441],[225,414],[216,368],[204,325]],
    [[480,125],[522,93],[574,100],[603,121],[649,120],[700,99],[759,115],[812,139],[848,173],[816,197],[775,186],[742,205],[705,185],[674,208],[638,196],[609,221],[580,206],[563,169],[530,164],[511,189],[486,171]],
    [[492,212],[535,198],[572,218],[591,264],[574,305],[552,358],[526,386],[503,345],[483,300],[467,256]],
    [[805,336],[843,319],[877,337],[887,369],[858,391],[822,380],[797,360]],
    [[329,97],[350,73],[374,86],[364,117],[342,134],[327,120]],
  ]
  continents.forEach(points => { c.beginPath(); points.forEach(([x,y], i) => i ? c.lineTo(x,y) : c.moveTo(x,y)); c.closePath(); const land = c.createLinearGradient(0,80,0,400); land.addColorStop(0,'#1a6475'); land.addColorStop(1,'#0b3d52'); c.fillStyle = land; c.fill(); c.strokeStyle = '#3b9fae'; c.lineWidth = 1.3; c.stroke() })
  let seed = 41; const random = () => { seed = (seed * 16807) % 2147483647; return seed / 2147483647 }
  for (let i = 0; i < 550; i++) { const x = random()*1024, y = 90+random()*310; c.fillStyle = `rgba(83,212,220,${random()*.32})`; c.fillRect(x,y,random()*1.6+.3,random()*1.6+.3) }
  const t = new THREE.CanvasTexture(canvas); t.colorSpace = THREE.SRGBColorSpace; return t
}

function makeCloudTexture() {
  const canvas = document.createElement('canvas'); canvas.width = 1024; canvas.height = 512
  const c = canvas.getContext('2d')
  c.clearRect(0, 0, 1024, 512)
  let seed = 42; const random = () => { seed = (seed * 16807) % 2147483647; return seed / 2147483647 }
  for (let i = 0; i < 200; i++) {
    const x = random() * 1024, y = random() * 512
    const r = random() * 40 + 10
    const g = c.createRadialGradient(x, y, 0, x, y, r)
    g.addColorStop(0, `rgba(255,255,255,${random() * .15})`)
    g.addColorStop(1, 'rgba(255,255,255,0)')
    c.fillStyle = g
    c.beginPath(); c.arc(x, y, r, 0, Math.PI * 2); c.fill()
  }
  return new THREE.CanvasTexture(canvas)
}

function makeNightTexture() {
  const canvas = document.createElement('canvas'); canvas.width = 1024; canvas.height = 512
  const c = canvas.getContext('2d')
  c.fillStyle = '#000'; c.fillRect(0, 0, 1024, 512)
  let seed = 43; const random = () => { seed = (seed * 16807) % 2147483647; return seed / 2147483647 }
  for (let i = 0; i < 300; i++) {
    const x = random() * 1024, y = 90 + random() * 310
    const brightness = random() * 0.8 + 0.2
    c.fillStyle = `rgba(255,220,100,${brightness})`
    c.fillRect(x, y, random() * 2 + .5, random() * 2 + .5)
  }
  return new THREE.CanvasTexture(canvas)
}

function createSatelliteMarker(color) {
  const group = new THREE.Group()
  const dot = new THREE.Mesh(new THREE.SphereGeometry(.05, 16, 16), new THREE.MeshBasicMaterial({ color }))
  group.add(dot)
  const halo = new THREE.Mesh(new THREE.RingGeometry(.07, .09, 32), new THREE.MeshBasicMaterial({ color, transparent: true, opacity: .65, side: THREE.DoubleSide }))
  group.add(halo)
  // 覆盖范围圆盘（初始隐藏，updateFootprint 设置）
  const disc = new THREE.Mesh(
    new THREE.CircleGeometry(0.3, 48),
    new THREE.MeshBasicMaterial({ color, transparent: true, opacity: .14, side: THREE.DoubleSide, depthWrite: false })
  )
  disc.visible = false
  group.add(disc)
  // 覆盖范围边界环
  const ring = new THREE.Mesh(
    new THREE.RingGeometry(.3, .3, 48),
    new THREE.MeshBasicMaterial({ color, transparent: true, opacity: .6, side: THREE.DoubleSide, depthWrite: false })
  )
  ring.visible = false
  group.add(ring)
  // 轨道线
  const orbitPts = []; for (let i = 0; i <= 150; i++) { const a = i / 150 * Math.PI * 2; orbitPts.push(new THREE.Vector3(Math.cos(a) * 2.32, Math.sin(a) * 2.32 * .28, Math.sin(a) * 2.32)) }
  const orbit = new THREE.Line(new THREE.BufferGeometry().setFromPoints(orbitPts), new THREE.LineBasicMaterial({ color, transparent: true, opacity: .4 }))
  orbit.rotation.z = .35
  group.add(orbit)
  // 卫星名称标签（Sprite，hover 时显示）
  const canvas = document.createElement('canvas'); canvas.width = 256; canvas.height = 48
  const ctx = canvas.getContext('2d'); ctx.font = '18px sans-serif'; ctx.fillStyle = '#e2f0ff'; ctx.textAlign = 'center'; ctx.fillText('', 128, 30)
  const labelTex = new THREE.CanvasTexture(canvas)
  const label = new THREE.Sprite(new THREE.SpriteMaterial({ map: labelTex, transparent: true, depthTest: false }))
  label.scale.set(1.2, .24, 1); label.visible = false; label.position.set(0, .28, 0)
  group.add(label)
  group.userData = { labelTex, canvas, ctx }
  return group
}

function updateFootprint(marker, sat) {
  if (!marker) return
  const disc = marker.children[2], ring = marker.children[3]
  const fpKm = sat.footprint || 0
  if (!Number.isFinite(fpKm) || fpKm <= 100) {
    disc.visible = false; ring.visible = false
    return
  }
  // 覆盖圆半径：footprint(直径km) -> 球面角半径 -> 场景半径
  const earthKm = 6371, sceneEarth = 2.0, alt = sat.alt || 0
  const halfAngle = Math.asin(Math.min(1, (fpKm / 2) / earthKm))  // 半角 rad
  const rScene = halfAngle * sceneEarth * (1 + alt / earthKm)  // 近似投影半径
  disc.scale.setScalar(rScene / 0.3)
  ring.scale.setScalar(rScene / 0.3)
  disc.visible = true
  ring.visible = true
  // 圆盘朝球心方向
  disc.lookAt(0, 0, 0)
  ring.lookAt(0, 0, 0)
}

function makeMeteor() {
  const pts = []; const segs = 14
  for (let i = 0; i <= segs; i++) pts.push(new THREE.Vector3(0, 0, -i * .5))
  const geo = new THREE.BufferGeometry().setFromPoints(pts)
  const mat = new THREE.LineBasicMaterial({ color: 0xaee9ff, transparent: true, opacity: .9 })
  const line = new THREE.Line(geo, mat)
  // 随机起点与方向
  const theta = Math.random() * Math.PI * 2
  const start = new THREE.Vector3(Math.cos(theta) * 8, (Math.random() - .5) * 5 + 2, (Math.random() - .5) * 8 - 2)
  line.position.copy(start)
  line.rotation.z = Math.random() * .6 - .3
  line.rotation.y = Math.random() * .4 - .2
  line.userData = { speed: .06 + Math.random() * .08, life: 0, maxLife: 90 + Math.random() * 60 }
  return line
}

function init() {
  scene = new THREE.Scene()
  camera = new THREE.PerspectiveCamera(36, 1, .1, 100)
  camera.position.set(0, .25, 7.2)
  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
  renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5))
  renderer.outputColorSpace = THREE.SRGBColorSpace
  container.value.appendChild(renderer.domElement)

  scene.add(new THREE.AmbientLight(0x79bbd4, 1.5))
  const light = new THREE.DirectionalLight(0x8de7ff, 2.8)
  light.position.set(-4, 3, 5)
  scene.add(light)

  earth = new THREE.Mesh(
    new THREE.SphereGeometry(2, 64, 64),
    new THREE.MeshPhongMaterial({ map: makeEarthTexture(), color: 0x83b7c7, shininess: 14, specular: 0x225577 })
  )
  earth.rotation.y = -1.4
  scene.add(earth)

  clouds = new THREE.Mesh(
    new THREE.SphereGeometry(2.02, 64, 64),
    new THREE.MeshLambertMaterial({ map: makeCloudTexture(), transparent: true, opacity: .6 })
  )
  scene.add(clouds)

  const night = new THREE.Mesh(
    new THREE.SphereGeometry(1.98, 64, 64),
    new THREE.MeshBasicMaterial({ map: makeNightTexture(), transparent: true, opacity: .4, blending: THREE.AdditiveBlending })
  )
  night.rotation.y = Math.PI
  scene.add(night)

  const atmosphere = new THREE.Mesh(
    new THREE.SphereGeometry(2.075, 64, 64),
    new THREE.ShaderMaterial({
      transparent: true, side: THREE.BackSide, blending: THREE.AdditiveBlending,
      vertexShader: 'varying vec3 vNormal; void main(){vNormal=normalize(normalMatrix*normal);gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}',
      fragmentShader: 'varying vec3 vNormal; void main(){float i=pow(0.68-dot(vNormal,vec3(0,0,1)),2.0);gl_FragColor=vec4(0.12,0.65,0.95,1.0)*i;}'
    })
  )
  scene.add(atmosphere)

  const glow = new THREE.Mesh(
    new THREE.SphereGeometry(2.15, 64, 64),
    new THREE.ShaderMaterial({
      transparent: true, side: THREE.BackSide, blending: THREE.AdditiveBlending,
      vertexShader: 'varying vec3 vNormal; void main(){vNormal=normalize(normalMatrix*normal);gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}',
      fragmentShader: 'varying vec3 vNormal; void main(){float i=pow(0.75-dot(vNormal,vec3(0,0,1)),3.0);gl_FragColor=vec4(0.0,0.9,1.0,1.0)*i*0.6;}'
    })
  )
  scene.add(glow)

  // 轨道环装饰
  const ringMat = new THREE.LineBasicMaterial({ color: 0x2baac8, transparent: true, opacity: .25 })
  ;[2.65, 2.85].forEach((r, idx) => {
    const pts = []; for (let i = 0; i <= 180; i++) { const a = i / 180 * Math.PI * 2; pts.push(new THREE.Vector3(Math.cos(a) * r, 0, Math.sin(a) * r)) }
    const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), ringMat)
    line.rotation.x = idx ? .55 : 1.12; line.rotation.z = .28
    scene.add(line)
  })

  // 星空粒子
  const starsGeo = new THREE.BufferGeometry(), positions = []
  for (let i = 0; i < 400; i++) positions.push((Math.random() - .5) * 18, (Math.random() - .5) * 12, -2 - Math.random() * 6)
  starsGeo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
  particles = new THREE.Points(starsGeo, new THREE.PointsMaterial({ color: 0x77bbd4, size: .018, transparent: true, opacity: .6 }))
  scene.add(particles)

  // ===== 轨道控制器（拖拽旋转 / 缩放，无人操作自动旋转）=====
  controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.dampingFactor = .06
  controls.minDistance = 3.2
  controls.maxDistance = 11
  controls.autoRotate = true
  controls.autoRotateSpeed = .5
  controls.enablePan = false
  controls.addEventListener('start', () => { controls.autoRotate = false; emit('drag', true) })
  controls.addEventListener('end', () => { setTimeout(() => { controls.autoRotate = true; emit('drag', false) }, 5000) })

  // ===== 点击 / 悬停交互（Raycaster）=====
  raycaster = new THREE.Raycaster()
  mouse = new THREE.Vector2()
  renderer.domElement.addEventListener('pointermove', onPointerMove)
  renderer.domElement.addEventListener('click', onClick)

  // ===== 流星装饰 =====
  for (let i = 0; i < 3; i++) { const m = makeMeteor(); scene.add(m); meteors.push(m) }

  observer = new ResizeObserver(resize)
  observer.observe(container.value)
  resize()
  animate()
}

function onPointerMove(e) {
  const rect = renderer.domElement.getBoundingClientRect()
  mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1
  mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1
  raycaster.setFromCamera(mouse, camera)
  const meshes = []
  Object.values(satelliteMarkers).forEach(m => { if (m?.children[0]) meshes.push(m.children[0]) })
  const hits = raycaster.intersectObjects(meshes, false)
  if (hits.length) {
    const g = hits[0].object.parent
    if (hoverMarker !== g) {
      if (hoverMarker?.userData?.label) hoverMarker.userData.label.visible = false
      hoverMarker = g
      if (hoverMarker?.userData?.label) hoverMarker.userData.label.visible = true
      renderer.domElement.style.cursor = 'pointer'
    }
  } else {
    if (hoverMarker?.userData?.label) hoverMarker.userData.label.visible = false
    hoverMarker = null
    renderer.domElement.style.cursor = 'grab'
  }
}

function onClick(e) {
  const rect = renderer.domElement.getBoundingClientRect()
  mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1
  mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1
  raycaster.setFromCamera(mouse, camera)
  const meshes = []
  Object.values(satelliteMarkers).forEach(m => { if (m?.children[0]) meshes.push(m.children[0]) })
  const hits = raycaster.intersectObjects(meshes, false)
  if (hits.length) {
    // 通过 color 找 noradId（color 与 sat.color 对应）
    const colorHex = hits[0].object.material.color.getHexString()
    const sat = (props.satellites || []).find(s => s.color && s.color.replace('#', '').toLowerCase() === colorHex)
    const iss = props.iss
    if (sat) emit('select-satellite', sat)
    else if (iss && iss.color && iss.color.replace('#', '').toLowerCase() === colorHex) emit('select-satellite', iss)
  }
}

function resize() {
  const w = container.value.clientWidth, h = container.value.clientHeight
  if (!w || !h) return
  renderer.setSize(w, h)
  camera.aspect = w / h
  camera.updateProjectionMatrix()
}

// 供父组件调用：视角复位
function resetView() {
  if (controls) {
    controls.target.set(0, 0, 0)
    camera.position.set(0, .25, 7.2)
    controls.update()
  }
}
defineExpose({ resetView })

function animate() {
  frame = requestAnimationFrame(animate)
  earth.rotation.y += .00035
  clouds.rotation.y += .00025
  // 更新所有卫星标记的脉冲动画
  Object.values(satelliteMarkers).forEach(m => {
    if (m?.children[1]) m.children[1].scale.setScalar(1 + Math.sin(Date.now() * .004) * .2)
  })
  // 流星动画
  meteors.forEach(m => {
    m.userData.life++
    if (m.userData.life > m.userData.maxLife) {
      scene.remove(m); m.geometry.dispose(); m.material.dispose()
      const idx = meteors.indexOf(m)
      if (idx > -1) { meteors.splice(idx, 1); const nm = makeMeteor(); scene.add(nm); meteors.push(nm) }
      return
    }
    m.position.x += m.userData.speed
    m.position.y -= m.userData.speed * .35
    m.material.opacity = Math.max(0, 1 - m.userData.life / m.userData.maxLife)
  })
  if (meteors.length < 2) { const nm = makeMeteor(); scene.add(nm); meteors.push(nm) }
  controls?.update()
  renderer.render(scene, camera)
}

function updateSatellites(sats) {
  if (!sats || !Array.isArray(sats)) return
  const activeIds = new Set(sats.map(s => s.noradId))

  // 移除消失的卫星
  Object.keys(satelliteMarkers).forEach(id => {
    if (!activeIds.has(Number(id))) {
      scene.remove(satelliteMarkers[id])
      if (satelliteTrails[id]) scene.remove(satelliteTrails[id])
      delete satelliteMarkers[id]
      delete satelliteTrails[id]
    }
  })

  // 更新/添加卫星
  sats.forEach(sat => {
    if (!Number.isFinite(sat.lat) || !Number.isFinite(sat.lng)) return
    const color = sat.color || '#00e4ff'

    if (!satelliteMarkers[sat.noradId]) {
      // 新卫星
      const marker = createSatelliteMarker(color)
      scene.add(marker)
      satelliteMarkers[sat.noradId] = marker
      satelliteTrails[sat.noradId] = []
    }

    const marker = satelliteMarkers[sat.noradId]
    const pos = latLng(sat.lat, sat.lng, 2.16)
    marker.position.copy(pos)
    marker.lookAt(0, 0, 0)

    // 更新名称标签（hover 时显示）
    if (marker.userData.labelTex) {
      const ctx = marker.userData.canvas.getContext('2d')
      ctx.clearRect(0, 0, 256, 48)
      ctx.font = 'bold 17px sans-serif'; ctx.textAlign = 'center'
      ctx.fillStyle = '#e2f0ff'; ctx.shadowColor = 'rgba(0,228,255,.8)'; ctx.shadowBlur = 8
      ctx.fillText(sat.name || `SAT-${sat.noradId}`, 128, 30)
      marker.userData.labelTex.needsUpdate = true
    }

    // 覆盖范围可视化
    updateFootprint(marker, sat)

    // 轨迹
    if (!satelliteTrails[sat.noradId]) satelliteTrails[sat.noradId] = []
    satelliteTrails[sat.noradId].push(pos.clone())
    if (satelliteTrails[sat.noradId].length > 40) satelliteTrails[sat.noradId].shift()

    // 更新轨迹线
    const trailId = `trail_${sat.noradId}`
    let trailLine = scene.getObjectByName(trailId)
    if (!trailLine) {
      trailLine = new THREE.Line(new THREE.BufferGeometry(), new THREE.LineBasicMaterial({ color, transparent: true, opacity: .5 }))
      trailLine.name = trailId
      scene.add(trailLine)
    }
    trailLine.geometry.dispose()
    trailLine.geometry = new THREE.BufferGeometry().setFromPoints(satelliteTrails[sat.noradId])
  })
}

watch(() => props.satellites, (sats) => {
  if (sats && sats.length > 0) updateSatellites(sats)
  else if (props.iss) updateSatellites([props.iss])  // 兼容单ISS模式
}, { deep: true })

watch(() => props.iss, (v) => {
  if (v && !props.satellites) updateSatellites([v])
}, { deep: true })

onMounted(init)
onBeforeUnmount(() => {
  cancelAnimationFrame(frame)
  observer?.disconnect()
  controls?.dispose()
  renderer.domElement.removeEventListener('pointermove', onPointerMove)
  renderer.domElement.removeEventListener('click', onClick)
  renderer?.dispose()
  container.value?.replaceChildren()
})
</script>
