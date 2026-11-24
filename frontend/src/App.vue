<template>
  <div class="viewport">
    <div class="stage" ref="stage">
      <div class="space-bg"></div>
      <div class="scanline"></div>
      <header class="topbar">
        <div class="brand"><span class="brand-mark">S</span><div><b>星轨</b><small>SATELLITE INTELLIGENCE</small></div></div>
        <div class="title"><i></i><h1>卫星数据可视化大屏系统</h1><i></i></div>
        <div class="top-actions"><span class="clock">{{ clock }}</span><button class="ghost" @click="toggleMusic" :class="{active: musicOn}">{{ musicOn ? '♪ 音乐开' : '♪ 音乐关' }}</button><button class="ghost" @click="resetView">视角复位</button><button class="ghost" @click="openReplay">轨迹回放</button><button class="ghost" @click="openRecords">观测台账</button><button class="ghost" @click="exit">退出</button></div>
      </header>
      <div v-if="weatherClass === 'danger' || weatherClass === 'warn'" :class="['alert-bar', weatherClass]">
        <span class="alert-icon">⚠</span>
        <b>空间天气告警：{{ summary.spaceWeather?.level }}</b>
        <span>当前 Kp={{ (summary.spaceWeather?.kp || 0).toFixed(1) }}，地磁活动活跃，可能影响卫星轨道与通信链路</span>
      </div>

      <main class="dashboard">
        <section class="column left">
          <Panel title="轨道高度分布" subtitle="ORBIT DISTRIBUTION">
            <VChart :option="orbitOption" />
            <div class="legend-note"><span class="dot cyan"></span>基于当前在轨卫星 TLE / SatCat 目录</div>
          </Panel>
          <Panel title="国家 / 地区占比" subtitle="OPERATOR SHARE">
            <VChart :option="countryOption" />
          </Panel>
          <Panel title="空间天气 · Kp 指数" subtitle="SPACE WEATHER">
            <div class="weather-state"><span :class="['weather-lamp', weatherClass]"></span><b>{{ summary.spaceWeather?.level || '读取中' }}</b><strong>{{ (summary.spaceWeather?.kp || 0).toFixed(1) }}</strong><small>Kp</small></div>
            <VChart :option="weatherOption" height="122px" />
          </Panel>
        </section>

        <section class="column center">
          <div class="kpis">
            <Kpi label="在轨目标" :value="summary.total" unit="颗" icon="◎" />
            <Kpi label="有效轨道数据" :value="summary.active" unit="组" icon="⌁" />
            <Kpi label="运营国家 / 地区" :value="summary.countries" unit="个" icon="◇" />
            <Kpi label="ISS 历史采样" :value="summary.issHistory" unit="条" icon="↗" />
          </div>
          <div class="earth-panel">
            <div class="earth-caption"><span>LIVE ORBITAL VIEW</span><b>近地空间实时态势</b></div>
            <Earth :iss="iss" :satellites="trackedSatellites" @select-satellite="s => selected = s" ref="earthComp" />
            <div class="iss-card">
              <div class="iss-title"><span class="pulse"></span>ISS · ZARYA <small>25544</small></div>
              <div class="coords"><div><small>纬度 LAT</small><b>{{ fmt(iss.lat) }}°</b></div><div><small>经度 LNG</small><b>{{ fmt(iss.lng) }}°</b></div></div>
              <div class="iss-meta"><span>高度 <b>{{ fmt(iss.alt) }}</b> km</span><span>速度 <b>{{ fmt(iss.velocity, 0) }}</b> km/h</span></div>
              <div class="iss-foot"><span>{{ iss.degraded ? 'SGP4 降级推算' : '实时数据已接入' }}</span><span>{{ iss.visibility === 'eclipsed' ? '地影区' : '日照区' }}</span></div>
            </div>
            <div class="sat-legend">
              <span v-for="s in trackedSatellites" :key="s.noradId" class="sat-legend-item">
                <i :style="{background: s.color}"></i>{{ s.name }}
              </span>
            </div>
            <div class="earth-scale">ALTITUDE <b>{{ fmt(iss.alt) }}</b> KM <i></i> VELOCITY <b>{{ fmt(iss.velocity, 0) }}</b> KM/H</div>
          </div>
          <Panel class="trend-panel" title="近 5 年在轨目标发射趋势" subtitle="LAUNCH TREND BY YEAR">
            <VChart :option="launchOption" height="160px" />
          </Panel>
        </section>

        <section class="column right">
          <Panel title="卫星目标目录" subtitle="SATELLITE CATALOG" class="catalog-panel">
            <div class="search"><input v-model="keyword" placeholder="名称 / NORAD / 国家" @keyup.enter="loadSatellites(1)"/><button @click="loadSatellites(1)">检索</button></div>
            <div class="sat-list">
              <button v-for="s in satellites" :key="s.noradId" class="sat-row" @click="selected = s">
                <span class="sat-index">{{ String(s.noradId).slice(-3) }}</span><span class="sat-name"><b>{{ s.name }}</b><small>{{ s.intlDesignator || s.owner || 'NORAD CATALOG' }}</small></span><span class="sat-apo">{{ s.apogee ? Math.round(s.apogee) : '—' }}<small>km</small></span>
              </button>
            </div>
            <div class="pager"><span>共 {{ total.toLocaleString() }} 个目标</span><button :disabled="page <= 1" @click="loadSatellites(page - 1)">‹</button><b>{{ page }}</b><button :disabled="page * 8 >= total" @click="loadSatellites(page + 1)">›</button></div>
          </Panel>
          <Panel title="实时遥测" subtitle="REALTIME TELEMETRY" class="telemetry-panel">
            <div class="telemetry-row"><span>数据通道</span><b :class="connected ? 'ok' : 'warn'">{{ connected ? 'WEBSOCKET · ONLINE' : 'RECONNECTING' }}</b></div>
            <div class="telemetry-row"><span>追踪卫星数</span><b>{{ trackedSatellites.length || 1 }} 颗</b></div>
            <div class="telemetry-row"><span>最近观测时间</span><b>{{ shortTime(iss.observedAt) }}</b></div>
            <div class="telemetry-row"><span>覆盖直径</span><b>{{ fmt(iss.footprint, 0) || '4,530' }} km</b></div>
            <div class="telemetry-row"><span>轨道周期</span><b>92.9 min</b></div>
            <div class="telemetry-actions">
              <button class="primary" @click="showObservation = true">＋ 新增观测</button>
              <button class="ghost" @click="exportSatellites">导出卫星</button>
              <button class="ghost" @click="exportObservations">导出台账</button>
              <button class="ghost" @click="exportSnapshot">截图导出</button>
            </div>
          </Panel>
          <Panel title="每日天文一图" subtitle="ASTRONOMY PICTURE OF THE DAY" class="apod-panel">
            <div v-if="apod && !apod.error" class="apod">
              <img :src="apod.url" :alt="apod.title" class="apod-img" />
              <div class="apod-info">
                <b>{{ apod.title }}</b>
                <small>{{ apod.date }}</small>
              </div>
            </div>
            <div v-else class="apod-empty">每日天文一图加载中…</div>
          </Panel>
        </section>
      </main>

      <footer class="statusbar"><div><span :class="['status-dot', connected ? 'ok' : 'warn']"></span>{{ connected ? '实时数据链路正常' : '实时链路重连中，页面保持最近数据' }}<i></i>数据每 10 秒更新</div><div v-if="iss.message" class="degrade">⚠ {{ iss.message }}</div><div>DATA SOURCE · CelesTrak / Where the ISS at / NOAA SWPC <span>UTC {{ utc }}</span></div></footer>
    </div>

    <div v-if="selected" class="modal-mask" @click.self="selected = null"><div class="modal"><div class="modal-head"><div><small>SATELLITE PROFILE</small><h2>{{ selected.name }}</h2></div><button @click="selected = null">×</button></div><dl><div><dt>NORAD 编目号</dt><dd>{{ selected.noradId }}</dd></div><div><dt>国际编号</dt><dd>{{ selected.intlDesignator || '—' }}</dd></div><div><dt>运营方</dt><dd>{{ selected.owner || '—' }}</dd></div><div><dt>发射日期</dt><dd>{{ selected.launchDate || '—' }}</dd></div><div><dt>轨道倾角</dt><dd>{{ selected.inclination || '—' }}°</dd></div><div><dt>远 / 近地点</dt><dd>{{ selected.apogee || '—' }} / {{ selected.perigee || '—' }} km</dd></div></dl><button class="primary wide" @click="showObservation = true">为该目标新增观测</button></div></div>

    <div v-if="showObservation" class="modal-mask" @click.self="showObservation = false"><form class="modal" @submit.prevent="saveObservation"><div class="modal-head"><div><small>FIELD OBSERVATION</small><h2>新增观测记录</h2></div><button type="button" @click="showObservation = false">×</button></div><label>NORAD 编目号<input v-model.number="form.satelliteId" type="number" required /></label><label>观测人<input v-model="form.observerName" required maxlength="40" /></label><label>观测备注<textarea v-model="form.note" required minlength="2" rows="4" placeholder="例如：23:10 于太原观测，轨迹稳定，设备状态正常。"></textarea></label><p v-if="formMessage" class="form-message">{{ formMessage }}</p><button class="primary wide" :disabled="saving">{{ saving ? '正在写入数据库…' : '保存并回查' }}</button></form></div>

    <div v-if="showRecords" class="modal-mask" @click.self="showRecords = false"><div class="modal records"><div class="modal-head"><div><small>PERSISTED RECORDS</small><h2>观测台账 · 数据库回查</h2></div><button @click="showRecords = false">×</button></div><div v-if="!records.length" class="empty">暂无观测记录</div><div v-for="r in records" :key="r.id" class="record"><b>#{{ r.id }} · {{ r.satellite_name }}</b><span>{{ r.created_at }}</span><p>{{ r.note }}</p><small>观测人：{{ r.observer_name }}</small></div></div></div>
    <div v-if="showReplay" class="modal-mask" @click.self="showReplay = false"><div class="modal replay"><div class="modal-head"><div><small>HISTORY REPLAY</small><h2>ISS 历史轨迹回放</h2></div><button @click="showReplay = false">×</button></div><div class="replay-stats"><span>已加载 <b>{{ replayPath.length }}</b> 个采样点</span><span>当前 <b>{{ replayIndex + 1 }}</b> / {{ replayPath.length }}</span><span class="replay-controls"><button class="ghost" @click="toggleReplay">{{ replayPlaying ? '⏸ 暂停' : '▶ 播放' }}</button><button class="ghost" @click="resetReplay">⟲ 重置</button></span></div><canvas ref="replayCanvas" class="replay-canvas"></canvas><div v-if="!replayPath.length" class="empty replay-empty">暂无历史数据，先让系统运行一段时间采集后再回放</div></div></div>

    <div v-if="needLogin" class="login-mask"><form class="login-card" @submit.prevent="doLogin"><div class="login-orbit">S</div><small>ORBITAL INTELLIGENCE PLATFORM</small><h2>星轨 · 卫星数据可视化</h2><p>使用数字藏经阁邮箱账号登录，进入实时空间态势中心</p><label>邮箱<input v-model="loginForm.username" autocomplete="email" placeholder="your@email.com" /></label><label>密码<input v-model="loginForm.password" type="password" autocomplete="current-password" /></label><p v-if="loginError" class="login-error">{{ loginError }}</p><button class="primary wide" :disabled="logging">{{ logging ? '身份验证中…' : '进入态势中心 →' }}</button><div class="login-hint">仅支持数字藏经阁邮箱账号</div><div class="login-link">没有账号？<a href="https://heyckz.cc/llmops/" target="_blank">去数字藏经阁注册 →</a></div></form></div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import html2canvas from 'html2canvas'
import Panel from './components/Panel.vue'
import Kpi from './components/Kpi.vue'
import VChart from './components/VChart.vue'
import Earth from './components/Earth.vue'
import { api, login, logout, getToken, getLocalToken } from './api'

const stage = ref(null), summary = ref({}), iss = ref({}), satellites = ref([]), total = ref(0), page = ref(1), keyword = ref('')
const orbit = ref([]), countries = ref([]), launches = ref([]), weather = ref([]), connected = ref(false)
const trackedSatellites = ref([]), apod = ref(null)
const selected = ref(null), showObservation = ref(false), showRecords = ref(false), records = ref([])
const showReplay = ref(false), replayPath = ref([]), replayIndex = ref(0), replayPlaying = ref(false), replayCanvas = ref(null)
let replayTimer = null
const needLogin = ref(!getToken()), logging = ref(false), loginError = ref('')
const loginForm = reactive({ username: '', password: '' })
const form = reactive({ satelliteId: 25544, observerName: 'admin', note: '' }), saving = ref(false), formMessage = ref('')
const clock = ref(''), utc = ref('')
let now = new Date()
let ws, reconnectTimer, clockTimer, refreshTimer, disposed = false
const fmt = (v, n = 2) => Number.isFinite(Number(v)) ? Number(v).toLocaleString('zh-CN', { maximumFractionDigits: n, minimumFractionDigits: n }) : '—'
const shortTime = v => v ? new Date(v).toLocaleTimeString('zh-CN', { hour12: false }) : '—'
const weatherClass = computed(() => (summary.value.spaceWeather?.kp || 0) >= 5 ? 'danger' : (summary.value.spaceWeather?.kp || 0) >= 4 ? 'warn' : '')

const axis = { axisLine: { lineStyle: { color: '#173653' } }, axisLabel: { color: '#6e91ad', fontSize: 10 }, splitLine: { lineStyle: { color: 'rgba(48,94,130,.15)' } } }
const tooltip = { backgroundColor: '#071728', borderColor: '#235272', textStyle: { color: '#d5efff', fontSize: 11 } }
const orbitOption = computed(() => ({ tooltip: { ...tooltip, trigger: 'item' }, color: ['#24d6ff', '#3478f6', '#a88bff', '#ffba69'], series: [{ type: 'pie', radius: ['48%', '70%'], center: ['50%', '48%'], padAngle: 3, itemStyle: { borderRadius: 3, borderColor: '#06111e', borderWidth: 3 }, label: { color: '#9ebed1', fontSize: 11, formatter: '{b}\n{c} 颗' }, labelLine: { lineStyle: { color: '#315570' } }, data: orbit.value }] }))
const countryOption = computed(() => ({ tooltip, grid: { left: 8, right: 25, top: 8, bottom: 5, containLabel: true }, xAxis: { type: 'value', ...axis, splitLine: { show: false }, axisLabel: { show: false } }, yAxis: { type: 'category', inverse: true, data: countries.value.map(x => x.name), ...axis, axisLabel: { color: '#a2bfd2', fontSize: 10, width: 65, overflow: 'truncate' } }, series: [{ type: 'bar', barWidth: 8, showBackground: true, backgroundStyle: { color: 'rgba(40,91,120,.12)' }, itemStyle: { color: { type: 'linear', x: 0, y: 0, x2: 1, y2: 0, colorStops: [{ offset: 0, color: '#176cb0' }, { offset: 1, color: '#32dbec' }] }, borderRadius: 2 }, label: { show: true, position: 'right', color: '#7ea9c1', fontSize: 9 }, data: countries.value.map(x => x.value) }] }))
const launchOption = computed(() => ({ tooltip: { ...tooltip, trigger: 'axis' }, grid: { left: 15, right: 20, top: 20, bottom: 5, containLabel: true }, xAxis: { type: 'category', data: launches.value.map(x => x.year), ...axis, boundaryGap: false }, yAxis: { type: 'value', ...axis }, series: [{ type: 'line', smooth: true, symbol: 'circle', symbolSize: 5, data: launches.value.map(x => x.value), lineStyle: { color: '#36d9f1', width: 2 }, itemStyle: { color: '#8af5ff', borderColor: '#09283a', borderWidth: 2 }, areaStyle: { color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: 'rgba(25,195,236,.35)' }, { offset: 1, color: 'rgba(25,195,236,0)' }] } } }] }))
const weatherOption = computed(() => ({ tooltip: { ...tooltip, trigger: 'axis' }, grid: { left: 5, right: 10, top: 15, bottom: 5, containLabel: true }, xAxis: { type: 'category', data: weather.value.map(x => x.time.slice(5, 13)), ...axis, axisLabel: { ...axis.axisLabel, interval: 5 } }, yAxis: { type: 'value', max: 9, ...axis }, series: [{ type: 'line', data: weather.value.map(x => x.kp), showSymbol: false, lineStyle: { color: '#ae91ff', width: 2 }, areaStyle: { color: 'rgba(143,112,239,.12)' }, markLine: { silent: true, symbol: 'none', label: { color: '#fa9a83', fontSize: 9, formatter: '地磁暴阈值' }, lineStyle: { color: '#e57865', type: 'dashed' }, data: [{ yAxis: 5 }] } }] }))

function fit() { const s = Math.min(window.innerWidth / 1920, window.innerHeight / 1080); stage.value.style.transform = `translate(-50%,-50%) scale(${s})` }
async function loadDashboard() {
  const [s, o, c, l, w] = await Promise.all([api('/api/dashboard/summary'), api('/api/dashboard/orbit-distribution'), api('/api/dashboard/countries'), api('/api/dashboard/launch-trend?years=5'), api('/api/dashboard/weather-trend')])
  summary.value = s; orbit.value = o.items; countries.value = c.items; launches.value = l.items; weather.value = w.items
}
async function loadSatellites(p = 1) { const d = await api(`/api/satellites?page=${p}&size=8&keyword=${encodeURIComponent(keyword.value)}`); satellites.value = d.list; total.value = d.total; page.value = p }
function connect() {
  const token = getLocalToken() || getToken()
  if (!token) return
  const protocol = location.protocol === 'https:' ? 'wss' : 'ws'
  ws = new WebSocket(`${protocol}://${location.host}/satdash/ws/realtime?token=${encodeURIComponent(token)}`)
  ws.onopen = () => { connected.value = true }
  ws.onmessage = e => {
    const m = JSON.parse(e.data)
    if (m.type === 'satellites' && Array.isArray(m.items)) {
      trackedSatellites.value = m.items
      const issSat = m.items.find(s => s.noradId === 25544)
      if (issSat) iss.value = { ...issSat, name: 'ISS (ZARYA)' }
      if (!disposed) summary.value.issHistory = (summary.value.issHistory || 0) + 1
    } else if (m.type === 'iss') {
      iss.value = m.data
      if (!disposed) summary.value.issHistory = (summary.value.issHistory || 0) + 1
    }
  }
  ws.onclose = () => { connected.value = false; if (!disposed) reconnectTimer = setTimeout(connect, 3000) }
  ws.onerror = () => ws.close()
}
async function boot() { try { if (!getToken()) { needLogin.value = true; return }; await Promise.all([loadDashboard(), loadSatellites(), loadApod(), loadTracked()]); needLogin.value = false; connect() } catch (e) { if (!getToken()) needLogin.value = true; else formMessage.value = e.message } }
async function loadApod() { try { const d = await api('/api/nasa/apod'); apod.value = d } catch (e) { apod.value = { error: e.message, degraded: true } } }
async function loadTracked() { try { const d = await api('/api/satellites/tracked'); if (d.items) trackedSatellites.value = d.items } catch (e) { /* WS 会兜底 */ } }
async function exportSnapshot() {
  try {
    const el = document.querySelector('.stage')
    if (!el) return
    const canvas = await html2canvas(el, { backgroundColor: '#020409', scale: 1.5, useCORS: true })
    const url = canvas.toDataURL('image/png')
    const a = document.createElement('a')
    a.href = url
    a.download = `satdash-${new Date().toISOString().slice(0, 19).replace(/[T:]/g, '-')}.png`
    a.click()
  } catch (e) {
    alert(`截图失败: ${e.message}`)
  }
}
async function exportSatellites() { window.open(`/satdash/api/export/satellites/csv?group=active&token=${getToken()}`, '_blank') }
async function exportObservations() { window.open(`/satdash/api/export/observations/csv?token=${getToken()}`, '_blank') }
async function doLogin() { logging.value = true; loginError.value = ''; try { await login(loginForm.username, loginForm.password); await boot() } catch (e) { loginError.value = e.message } finally { logging.value = false } }
async function saveObservation() { saving.value = true; formMessage.value = ''; try { const d = await api('/api/observations', { method: 'POST', body: JSON.stringify(form) }); formMessage.value = `已保存为 #${d.item.id}，数据库回查成功`; form.note = ''; setTimeout(() => { showObservation.value = false; formMessage.value = '' }, 1300) } catch (e) { formMessage.value = e.message } finally { saving.value = false } }
async function openRecords() { const d = await api('/api/observations?page=1&size=20'); records.value = d.list; showRecords.value = true }
async function openReplay() {
  showReplay.value = true; replayIndex.value = 0; replayPlaying.value = false
  try {
    const now = new Date()
    const end = now.toISOString().slice(0, 19)
    const start = new Date(now.getTime() - 24 * 3600 * 1000).toISOString().slice(0, 19)
    const d = await api(`/api/iss/history/range?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}&limit=800`)
    replayPath.value = d.items || []
  } catch (e) { replayPath.value = [] }
  if (replayCanvas.value) drawReplay()
}
function drawReplay() {
  const canvas = replayCanvas.value, ctx = canvas?.getContext('2d')
  if (!canvas || !ctx) return
  const w = canvas.clientWidth, h = canvas.clientHeight
  if (canvas.width !== w) { canvas.width = w; canvas.height = h }
  ctx.clearRect(0, 0, w, h)
  ctx.fillStyle = 'rgba(4,10,22,.95)'; ctx.fillRect(0, 0, w, h)
  if (!replayPath.value.length) return
  const pts = replayPath.value.map(p => ({ x: (p.longitude + 180) / 360 * w, y: (90 - p.latitude) / 180 * h }))
  // 轨迹线
  ctx.beginPath()
  ctx.strokeStyle = '#00e4ff'; ctx.lineWidth = 1.5; ctx.globalAlpha = .85
  pts.forEach((p, i) => i ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y))
  ctx.stroke(); ctx.globalAlpha = 1
  // 已播部分加亮
  const played = Math.max(1, replayIndex.value + 1)
  ctx.beginPath(); ctx.strokeStyle = '#f0d060'; ctx.lineWidth = 2.5
  pts.slice(0, played).forEach((p, i) => i ? ctx.lineTo(p.x, p.y) : ctx.moveTo(p.x, p.y))
  ctx.stroke()
  // 当前点
  const cur = pts[replayIndex.value] || pts[0]
  ctx.beginPath(); ctx.fillStyle = '#f0d060'; ctx.arc(cur.x, cur.y, 6, 0, Math.PI * 2); ctx.fill()
  ctx.beginPath(); ctx.fillStyle = '#fff'; ctx.arc(cur.x, cur.y, 2.5, 0, Math.PI * 2); ctx.fill()
  // 经纬网格
  ctx.strokeStyle = 'rgba(58,142,178,.15)'; ctx.lineWidth = 1
  for (let i = 1; i < 6; i++) { ctx.beginPath(); ctx.moveTo(w * i / 6, 0); ctx.lineTo(w * i / 6, h); ctx.stroke() }
  for (let i = 1; i < 4; i++) { ctx.beginPath(); ctx.moveTo(0, h * i / 4); ctx.lineTo(w, h * i / 4); ctx.stroke() }
  // 标签
  ctx.fillStyle = '#00e4ff'; ctx.font = '11px sans-serif'; ctx.globalAlpha = .7
  ctx.fillText(`LAT ${replayPath.value[replayIndex.value]?.latitude.toFixed(2) ?? '—'}°  LNG ${replayPath.value[replayIndex.value]?.longitude.toFixed(2) ?? '—'}°  ${replayPath.value[replayIndex.value]?.observed_at?.slice(11, 19) ?? ''}`, 12, h - 12)
  ctx.globalAlpha = 1
}
function stepReplay() {
  if (!replayPath.value.length) return
  replayIndex.value = Math.min(replayIndex.value + 1, replayPath.value.length - 1)
  drawReplay()
  if (replayIndex.value >= replayPath.value.length - 1) { replayPlaying.value = false; return }
  replayTimer = setTimeout(stepReplay, 120)
}
function toggleReplay() {
  if (!replayPath.value.length) return
  replayPlaying.value = !replayPlaying.value
  if (replayPlaying.value) { if (replayIndex.value >= replayPath.value.length - 1) replayIndex.value = 0; stepReplay() }
  else clearTimeout(replayTimer)
}
function resetReplay() { clearTimeout(replayTimer); replayPlaying.value = false; replayIndex.value = 0; drawReplay() }
function exit() { logout(); ws?.close(); needLogin.value = true }

// ===== 背景音乐（Web Audio 合成太空氛围音）=====
const earthComp = ref(null)
const musicOn = ref(false)
let audioCtx = null, masterGain = null, musicNodes = [], musicTimer = null

function toggleMusic() {
  if (!musicOn.value) {
    startMusic()
  } else {
    stopMusic()
  }
}

function startMusic() {
  try {
    if (!audioCtx) {
      audioCtx = new (window.AudioContext || window.webkitAudioContext)()
      masterGain = audioCtx.createGain()
      masterGain.gain.value = 0
      masterGain.connect(audioCtx.destination)
      buildPad()
      scheduleNotes()
    }
    if (audioCtx.state === 'suspended') audioCtx.resume()
    musicOn.value = true
    masterGain.gain.cancelScheduledValues(audioCtx.currentTime)
    masterGain.gain.linearRampToValueAtTime(.16, audioCtx.currentTime + 2.5)
  } catch (e) {
    alert(`音乐初始化失败: ${e.message}`)
  }
}

function stopMusic() {
  musicOn.value = false
  if (audioCtx && masterGain) {
    masterGain.gain.cancelScheduledValues(audioCtx.currentTime)
    masterGain.gain.linearRampToValueAtTime(0, audioCtx.currentTime + 1)
  }
  if (musicTimer) { clearInterval(musicTimer); musicTimer = null }
}

// 低音 Pad（两个低频振荡 + 滤波，营造太空氛围）
function buildPad() {
  const lp = audioCtx.createBiquadFilter()
  lp.type = 'lowpass'; lp.frequency.value = 420; lp.Q.value = .8
  lp.connect(masterGain)
  ;[55, 82.5, 110].forEach((f, i) => {
    const osc = audioCtx.createOscillator()
    osc.type = 'sine'; osc.frequency.value = f
    const g = audioCtx.createGain()
    g.gain.value = i === 0 ? .5 : .22
    osc.connect(g); g.connect(lp)
    osc.start()
    musicNodes.push(osc)
  })
  // 轻柔噪音层（风声）
  const bufferSize = audioCtx.sampleRate * 2
  const buffer = audioCtx.createBuffer(1, bufferSize, audioCtx.sampleRate)
  const data = buffer.getChannelData(0)
  for (let i = 0; i < bufferSize; i++) data[i] = Math.random() * 2 - 1
  const noise = audioCtx.createBufferSource()
  noise.buffer = buffer; noise.loop = true
  const np = audioCtx.createBiquadFilter()
  np.type = 'lowpass'; np.frequency.value = 300
  const ng = audioCtx.createGain(); ng.gain.value = .05
  noise.connect(np); np.connect(ng); ng.connect(masterGain)
  noise.start()
  musicNodes.push(noise)
}

// 缓慢琶音（C 大调柔和和弦，像太空电梯一样漂浮）
const padNotes = [261.63, 329.63, 392.0, 523.25]  // C E G C5
function scheduleNotes() {
  let step = 0
  const playStep = () => {
    if (!musicOn.value || !audioCtx) return
    const now = audioCtx.currentTime
    const f = padNotes[step % padNotes.length]
    const osc = audioCtx.createOscillator()
    osc.type = 'sine'; osc.frequency.value = f
    const g = audioCtx.createGain()
    g.gain.setValueAtTime(0, now)
    g.gain.linearRampToValueAtTime(.09, now + 1.2)
    g.gain.exponentialRampToValueAtTime(.0001, now + 4.6)
    osc.connect(g); g.connect(masterGain)
    osc.start(now); osc.stop(now + 5)
    step++
  }
  playStep()
  musicTimer = setInterval(() => {
    // 随机间隔 3.5–6s，避免机械感
    const delay = 3500 + Math.random() * 2500
    setTimeout(playStep, delay)
  }, 6000)
}

// ===== 视角复位（让 OrbitControls 回到默认视角）=====
function resetView() {
  try {
    const comp = earthComp.value
    if (comp && comp.resetView) comp.resetView()
  } catch (e) { /* 无组件实例时忽略 */ }
}
onMounted(() => { fit(); window.addEventListener('resize', fit); window.addEventListener('satdash-unauthorized', () => { needLogin.value = true }); clockTimer = setInterval(() => { now = new Date(); clock.value = now.toLocaleString('zh-CN', { hour12: false }); utc.value = now.toISOString().slice(11, 19) }, 1000); refreshTimer = setInterval(() => { if (!needLogin.value) loadDashboard().catch(() => {}) }, 300000); boot() })
onBeforeUnmount(() => { disposed = true; ws?.close(); clearTimeout(reconnectTimer); clearTimeout(replayTimer); clearInterval(clockTimer); clearInterval(refreshTimer); window.removeEventListener('resize', fit) })
</script>
