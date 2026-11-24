// 卫星数据可视化大屏 类型声明
// 供后续 TypeScript 迁移使用的共享接口

export interface SatellitePosition {
  noradId: number
  name: string
  lat: number
  lng: number
  alt: number
  velocity?: number
  degraded: boolean
  observedAt?: string
}

export interface DashboardSummary {
  totalObjects: number
  trackable: number
  countries: number
  issHistory: number
}

export interface Observation {
  id: number
  satellite_id: number
  satellite_name: string
  observer_name: string
  note: string
  created_at: string
}

export interface ApodData {
  title?: string
  explanation?: string
  url?: string
  hdurl?: string
  mediaType?: string
  date?: string
  copyright?: string
  source?: string
  error?: string
  degraded?: boolean
}

export interface ReplayPoint {
  latitude: number
  longitude: number
  altitude: number
  observed_at: string
}

export interface TelemetryState {
  connected: boolean
  trackedCount: number
  lastObservedAt: string | null
  coverageDiameter: number | null
  orbitalPeriod: number | null
}
