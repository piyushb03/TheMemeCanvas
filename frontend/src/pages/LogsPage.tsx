import { useState, useEffect, useRef } from 'react'
import { RefreshCw, Download } from 'lucide-react'

const LOG_FILES = ['system', 'scheduler', 'drive', 'youtube', 'ai', 'notifications', 'pipeline', 'errors']

function colorLine(line: string): string {
  if (line.includes('ERROR') || line.includes('❌') || line.includes('FATAL')) return 'error'
  if (line.includes('WARNING') || line.includes('⚠️')) return 'warning'
  if (line.includes('INFO') || line.includes('✅') || line.includes('🟢')) return 'info'
  return ''
}

export default function LogsPage() {
  const [selectedLog, setSelectedLog] = useState('system')
  const [lines, setLines] = useState<string[]>([])
  const [totalLines, setTotalLines] = useState(0)
  const [lineCount, setLineCount] = useState(100)
  const [loading, setLoading] = useState(false)
  const [autoRefresh, setAutoRefresh] = useState(false)
  const logRef = useRef<HTMLDivElement>(null)

  const fetchLogs = async () => {
    setLoading(true)
    try {
      const res = await fetch(`/api/logs?log_file=${selectedLog}&lines=${lineCount}`)
      if (res.ok) {
        const data = await res.json()
        setLines(data.lines)
        setTotalLines(data.total_lines)
      }
    } catch { /* ignore */ }
    setLoading(false)
    // Scroll to bottom
    setTimeout(() => {
      if (logRef.current) {
        logRef.current.scrollTop = logRef.current.scrollHeight
      }
    }, 50)
  }

  useEffect(() => { fetchLogs() }, [selectedLog, lineCount])

  useEffect(() => {
    if (!autoRefresh) return
    const interval = setInterval(fetchLogs, 5000)
    return () => clearInterval(interval)
  }, [autoRefresh, selectedLog])

  const downloadLog = () => {
    const content = lines.join('\n')
    const blob = new Blob([content], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${selectedLog}.log`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

      {/* Controls */}
      <div className="flex items-center gap-3" style={{ flexWrap: 'wrap' }}>
        {/* Log file selector */}
        <div className="flex gap-2" style={{ flexWrap: 'wrap' }}>
          {LOG_FILES.map(lf => (
            <button
              key={lf}
              className={`btn btn-sm ${selectedLog === lf ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setSelectedLog(lf)}
              id={`btn-log-${lf}`}
            >
              {lf}
            </button>
          ))}
        </div>

        <div className="flex gap-2" style={{ marginLeft: 'auto' }}>
          <select
            value={lineCount}
            onChange={e => setLineCount(Number(e.target.value))}
            id="select-log-lines"
            style={{
              background: 'var(--bg-glass)',
              border: '1px solid var(--border-card)',
              borderRadius: '8px',
              color: 'var(--text-primary)',
              fontSize: '12px',
              padding: '6px 10px',
            }}
          >
            {[50, 100, 200, 500].map(n => <option key={n} value={n}>{n} lines</option>)}
          </select>

          <button
            className={`btn btn-sm ${autoRefresh ? 'btn-success' : 'btn-secondary'}`}
            onClick={() => setAutoRefresh(!autoRefresh)}
            id="btn-auto-refresh"
          >
            {autoRefresh ? '⏹ Stop' : '▶ Live'}
          </button>

          <button className="btn btn-secondary btn-sm" onClick={fetchLogs} id="btn-refresh-logs">
            <RefreshCw size={13} />
          </button>

          <button className="btn btn-secondary btn-sm" onClick={downloadLog} id="btn-download-log">
            <Download size={13} />
          </button>
        </div>
      </div>

      {/* Log Info */}
      <div className="flex items-center justify-between">
        <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
          {selectedLog}.log · {totalLines} total lines · showing last {lineCount}
        </span>
        {autoRefresh && (
          <span className="badge badge-success">🔴 Live</span>
        )}
      </div>

      {/* Log Viewer */}
      <div className="log-viewer" ref={logRef}>
        {loading && lines.length === 0 ? (
          <div style={{ color: 'var(--text-muted)', padding: '20px', textAlign: 'center' }}>
            Loading logs...
          </div>
        ) : lines.length === 0 ? (
          <div style={{ color: 'var(--text-muted)', padding: '20px', textAlign: 'center' }}>
            No log entries found. Logs appear here once the scheduler starts.
          </div>
        ) : (
          lines.map((line, i) => (
            <div key={i} className={`log-line ${colorLine(line)}`}>
              {line || '\u00A0'}
            </div>
          ))
        )}
      </div>
    </div>
  )
}
