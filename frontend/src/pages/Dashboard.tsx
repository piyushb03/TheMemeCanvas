import { useState, useEffect } from 'react'
import { Upload, Clock, TrendingUp, AlertCircle, CheckCircle, Inbox, Youtube, Activity, RefreshCw } from 'lucide-react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend
} from 'recharts'
import { format, formatDistanceToNow } from 'date-fns'

interface Stats {
  total_uploaded: number
  total_failed: number
  total_queue: number
  queue_remaining: number
  days_remaining: number
  uploads_paused: boolean
  next_upload_time: string | null
  upload_time_setting: string
  timezone: string
  today_upload: any | null
}

interface HealthResult {
  component: string
  status: string
  message: string
  latency_ms: number | null
}

interface HealthReport {
  overall_status: string
  checked_at: string
  components: HealthResult[]
}

interface ChartData {
  labels: string[]
  data: number[]
}

const STATUS_COLORS = {
  completed: '#22c55e',
  failed: '#ef4444',
  pending: '#f59e0b',
  retrying: '#3b82f6',
  skipped: '#6b7280',
}

function StatCard({ icon: Icon, value, label, sub, color }: {
  icon: any, value: string | number, label: string, sub?: string, color: string
}) {
  return (
    <div className="stat-card">
      <div className={`stat-icon ${color}`}>
        <Icon size={22} />
      </div>
      <div className="stat-content">
        <div className="stat-value">{value}</div>
        <div className="stat-label">{label}</div>
        {sub && <div className="stat-sub">{sub}</div>}
      </div>
    </div>
  )
}

function HealthGrid({ health }: { health: HealthReport | null }) {
  if (!health) return (
    <div className="health-grid">
      {[...Array(6)].map((_, i) => (
        <div key={i} className="skeleton" style={{ height: '80px' }} />
      ))}
    </div>
  )

  const STATUS_EMOJI: Record<string, string> = {
    ok: '✅',
    warning: '⚠️',
    error: '❌',
  }

  return (
    <div className="health-grid">
      {health.components.map(c => (
        <div key={c.component} className={`health-item ${c.status}`}>
          <div className="flex items-center gap-2">
            <span>{STATUS_EMOJI[c.status] || '❓'}</span>
            <span className="health-item-name">{c.component.replace(/_/g, ' ')}</span>
          </div>
          <span className="health-item-status">{c.message.slice(0, 60)}</span>
          {c.latency_ms && (
            <span style={{ fontSize: '10px', color: 'var(--text-dim)' }}>{c.latency_ms.toFixed(0)}ms</span>
          )}
        </div>
      ))}
    </div>
  )
}

function TodayUploadCard({ upload }: { upload: any }) {
  if (!upload) {
    return (
      <div className="upload-card" style={{ background: 'rgba(0,0,0,0.2)' }}>
        <div className="upload-card-icon" style={{ background: 'rgba(107,90,138,0.15)' }}>⏳</div>
        <div className="upload-card-info">
          <div className="upload-card-filename" style={{ color: 'var(--text-muted)' }}>No upload today yet</div>
          <div className="upload-card-meta">Waiting for scheduled upload time</div>
        </div>
      </div>
    )
  }

  return (
    <div className="upload-card">
      <div className="upload-card-icon" style={{ background: 'rgba(34,197,94,0.15)' }}>✅</div>
      <div className="upload-card-info">
        <div className="upload-card-filename">{upload.title || upload.filename}</div>
        <div className="upload-card-meta flex gap-2" style={{ flexWrap: 'wrap' }}>
          {upload.youtube_url && (
            <a href={upload.youtube_url} target="_blank" rel="noopener noreferrer" className="link">▶ YouTube</a>
          )}
          {upload.completed_at && (
            <span style={{ color: 'var(--text-dim)' }}>
              {formatDistanceToNow(new Date(upload.completed_at), { addSuffix: true })}
            </span>
          )}
        </div>
      </div>
      <span className="badge badge-success">Uploaded</span>
    </div>
  )
}

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [health, setHealth] = useState<HealthReport | null>(null)
  const [chartData, setChartData] = useState<ChartData | null>(null)
  const [statusChart, setStatusChart] = useState<ChartData | null>(null)
  const [refreshing, setRefreshing] = useState(false)
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date())

  const fetchAll = async () => {
    setRefreshing(true)
    try {
      const [statsRes, healthRes, chartRes, statusRes] = await Promise.all([
        fetch('/api/stats'),
        fetch('/api/health'),
        fetch('/api/charts/upload-history?days=30'),
        fetch('/api/charts/status-breakdown'),
      ])

      if (statsRes.ok) setStats(await statsRes.json())
      if (healthRes.ok) setHealth(await healthRes.json())
      if (chartRes.ok) setChartData(await chartRes.json())
      if (statusRes.ok) setStatusChart(await statusRes.json())
      setLastRefresh(new Date())
    } catch (err) {
      console.error('Failed to fetch dashboard data:', err)
    }
    setRefreshing(false)
  }

  useEffect(() => {
    fetchAll()
    const interval = setInterval(fetchAll, 60000) // Refresh every minute
    return () => clearInterval(interval)
  }, [])

  // Build chart data for recharts
  const uploadChartData = chartData
    ? chartData.labels.map((date, i) => ({ date, uploads: chartData.data[i] }))
    : []

  const statusPieData = statusChart
    ? statusChart.labels.map((label, i) => ({
        name: label,
        value: statusChart.data[i],
        color: STATUS_COLORS[label as keyof typeof STATUS_COLORS] || '#6b7280',
      }))
    : []

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>

      {/* Refresh bar */}
      <div className="flex items-center justify-between">
        <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
          Last updated: {formatDistanceToNow(lastRefresh, { addSuffix: true })}
        </div>
        <button
          className="btn btn-secondary btn-sm"
          onClick={fetchAll}
          disabled={refreshing}
          id="btn-refresh-dashboard"
        >
          <RefreshCw size={14} className={refreshing ? 'loading-spinner' : ''} />
          Refresh
        </button>
      </div>

      {/* Stats Grid */}
      <div className="stats-grid">
        <StatCard
          icon={Upload}
          value={stats?.total_uploaded ?? '—'}
          label="Total Uploaded"
          sub="All time"
          color="green"
        />
        <StatCard
          icon={Inbox}
          value={stats?.queue_remaining ?? '—'}
          label="Queue Remaining"
          sub={stats ? `~${stats.days_remaining} days` : ''}
          color="purple"
        />
        <StatCard
          icon={AlertCircle}
          value={stats?.total_failed ?? '—'}
          label="Failed Uploads"
          sub="Require attention"
          color="red"
        />
        <StatCard
          icon={Clock}
          value={stats?.upload_time_setting ?? '—'}
          label="Upload Time"
          sub={stats?.timezone}
          color="blue"
        />
        <StatCard
          icon={TrendingUp}
          value={stats?.days_remaining ?? '—'}
          label="Days of Content"
          sub="At 1 video/day"
          color="yellow"
        />
        <StatCard
          icon={Activity}
          value={stats?.uploads_paused ? 'Paused' : 'Running'}
          label="Scheduler Status"
          sub={stats?.next_upload_time ? `Next: ${stats.next_upload_time}` : ''}
          color={stats?.uploads_paused ? 'yellow' : 'green'}
        />
      </div>

      {/* Today's Upload */}
      <div className="card">
        <div className="card-header">
          <span className="card-title">Today's Upload</span>
          {stats?.next_upload_time && (
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Next: {stats.next_upload_time}
            </span>
          )}
        </div>
        <TodayUploadCard upload={stats?.today_upload} />
      </div>

      {/* Charts */}
      <div className="content-grid">
        {/* Upload History Chart */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">Upload History (30 days)</span>
          </div>
          {uploadChartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={uploadChartData} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
                <defs>
                  <linearGradient id="uploadGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#7c3aed" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#7c3aed" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="date" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} tickLine={false} />
                <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 10 }} tickLine={false} axisLine={false} />
                <Tooltip
                  contentStyle={{
                    background: 'var(--bg-surface)',
                    border: '1px solid var(--border-card)',
                    borderRadius: '8px',
                    color: 'var(--text-primary)',
                    fontSize: '12px',
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="uploads"
                  stroke="#7c3aed"
                  strokeWidth={2}
                  fill="url(#uploadGradient)"
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div style={{ height: '220px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
              No upload data yet
            </div>
          )}
        </div>

        {/* Status Breakdown */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">Status Breakdown</span>
          </div>
          {statusPieData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={statusPieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={90}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {statusPieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    background: 'var(--bg-surface)',
                    border: '1px solid var(--border-card)',
                    borderRadius: '8px',
                    color: 'var(--text-primary)',
                    fontSize: '12px',
                  }}
                />
                <Legend
                  formatter={(value) => <span style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>{value}</span>}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div style={{ height: '220px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
              No data yet
            </div>
          )}
        </div>
      </div>

      {/* Health Check */}
      <div className="card">
        <div className="card-header">
          <span className="card-title">System Health</span>
          {health && (
            <span className={`badge ${health.overall_status === 'ok' ? 'badge-success' : health.overall_status === 'warning' ? 'badge-warning' : 'badge-error'}`}>
              {health.overall_status.toUpperCase()}
            </span>
          )}
        </div>
        <HealthGrid health={health} />
      </div>

    </div>
  )
}
