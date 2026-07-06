import { BrowserRouter, Routes, Route, NavLink, useLocation } from 'react-router-dom'
import { useState, useEffect } from 'react'
import {
  LayoutDashboard, ListVideo, History, Activity,
  Bell, Settings, Play, Pause, RefreshCw, Zap
} from 'lucide-react'
import Dashboard from './pages/Dashboard'
import Queue from './pages/Queue'
import HistoryPage from './pages/HistoryPage'
import LogsPage from './pages/LogsPage'
import SettingsPage from './pages/SettingsPage'

const API = '/api'

interface SystemStatus {
  uploading: boolean
  paused: boolean
  nextUpload: string | null
}

function Sidebar({ status }: { status: SystemStatus }) {
  const navItems = [
    { path: '/', icon: LayoutDashboard, label: 'Dashboard' },
    { path: '/queue', icon: ListVideo, label: 'Queue' },
    { path: '/history', icon: History, label: 'History' },
    { path: '/logs', icon: Activity, label: 'Logs' },
    { path: '/settings', icon: Settings, label: 'Settings' },
  ]

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div className="sidebar-logo-icon">🎭</div>
        <div className="sidebar-logo-text">
          <span className="sidebar-logo-title">TheMemeCanvas</span>
          <span className="sidebar-logo-subtitle">Automation Suite</span>
        </div>
      </div>

      <nav className="sidebar-nav">
        <span className="nav-section-label">Navigation</span>
        {navItems.map(({ path, icon: Icon, label }) => (
          <NavLink
            key={path}
            to={path}
            end={path === '/'}
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <Icon className="nav-item-icon" size={18} />
            {label}
          </NavLink>
        ))}

        <span className="nav-section-label" style={{ marginTop: '8px' }}>Controls</span>
        <QuickControls />
      </nav>

      <div className="sidebar-footer">
        <div className="sidebar-status">
          <div className={`status-dot ${status.paused ? 'warning' : 'ok'}`} />
          <span className="status-text">
            {status.paused ? 'Uploads Paused' : 'Scheduler Running'}
          </span>
        </div>
        {status.nextUpload && (
          <div style={{ marginTop: '8px', padding: '6px 12px', fontSize: '11px', color: 'var(--text-muted)' }}>
            Next: {status.nextUpload}
          </div>
        )}
      </div>
    </aside>
  )
}

function QuickControls() {
  const [loading, setLoading] = useState<string | null>(null)
  const [msg, setMsg] = useState<string | null>(null)

  const action = async (endpoint: string, label: string) => {
    setLoading(label)
    try {
      const res = await fetch(`/api/scheduler/${endpoint}`, { method: 'POST' })
      const data = await res.json()
      setMsg(data.status || 'Done')
      setTimeout(() => setMsg(null), 2000)
    } catch {
      setMsg('Error')
    }
    setLoading(null)
  }

  return (
    <>
      {msg && (
        <div className="alert alert-success" style={{ padding: '6px 10px', fontSize: '11px', marginBottom: '4px' }}>
          {msg}
        </div>
      )}
      <button
        className="nav-item"
        onClick={() => action('trigger-now', 'trigger')}
        disabled={loading === 'trigger'}
        id="btn-trigger-now"
      >
        <Zap size={18} className="nav-item-icon" />
        {loading === 'trigger' ? 'Triggering...' : 'Upload Now'}
      </button>
      <button
        className="nav-item"
        onClick={() => action('pause', 'pause')}
        disabled={loading === 'pause'}
        id="btn-pause-uploads"
      >
        <Pause size={18} className="nav-item-icon" />
        Pause Uploads
      </button>
      <button
        className="nav-item"
        onClick={() => action('resume', 'resume')}
        disabled={loading === 'resume'}
        id="btn-resume-uploads"
      >
        <Play size={18} className="nav-item-icon" />
        Resume Uploads
      </button>
      <button
        className="nav-item"
        onClick={() => action('sync-queue', 'sync')}
        disabled={loading === 'sync'}
        id="btn-sync-queue"
      >
        <RefreshCw size={18} className="nav-item-icon" />
        Sync Queue
      </button>
    </>
  )
}

function PageHeader({ title }: { title: string }) {
  return (
    <header className="page-header">
      <h1 className="page-title">{title}</h1>
      <div className="flex items-center gap-3">
        <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
          {new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
        </span>
      </div>
    </header>
  )
}

function AppContent() {
  const location = useLocation()
  const [status, setStatus] = useState<SystemStatus>({ uploading: false, paused: false, nextUpload: null })

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        const res = await fetch(`${API}/stats`)
        if (res.ok) {
          const data = await res.json()
          setStatus({
            uploading: false,
            paused: data.uploads_paused,
            nextUpload: data.next_upload_time,
          })
        }
      } catch { /* ignore */ }
    }

    fetchStatus()
    const interval = setInterval(fetchStatus, 30000)
    return () => clearInterval(interval)
  }, [])

  const pageTitle = (path: string) => {
    const titles: Record<string, string> = {
      '/': '🎭 Dashboard',
      '/queue': '📋 Content Queue',
      '/history': '📜 Upload History',
      '/logs': '📋 System Logs',
      '/settings': '⚙️ Settings',
    }
    return titles[path] || 'TheMemeCanvas'
  }

  return (
    <div className="app-layout">
      <Sidebar status={status} />
      <div className="main-content">
        <PageHeader title={pageTitle(location.pathname)} />
        <div className="page-content">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/queue" element={<Queue />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/logs" element={<LogsPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </div>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AppContent />
    </BrowserRouter>
  )
}
