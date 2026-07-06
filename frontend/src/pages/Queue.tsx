import { useState, useEffect } from 'react'
import { RefreshCw, SkipForward, Video, HardDrive } from 'lucide-react'

interface QueueItem {
  id: number
  filename: string
  drive_file_id: string
  is_processed: boolean
  is_skipped: boolean
  has_thumbnail: boolean
  file_size_bytes: number | null
  discovered_at: string
}

function formatBytes(bytes: number | null): string {
  if (!bytes) return '—'
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

export default function Queue() {
  const [items, setItems] = useState<QueueItem[]>([])
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [skipping, setSkipping] = useState<number | null>(null)
  const [showProcessed, setShowProcessed] = useState(false)

  const fetchQueue = async () => {
    setLoading(true)
    try {
      const url = showProcessed ? '/api/queue' : '/api/queue?processed=false'
      const res = await fetch(url)
      if (res.ok) setItems(await res.json())
    } catch (err) {
      console.error('Failed to fetch queue:', err)
    }
    setLoading(false)
  }

  const syncQueue = async () => {
    setSyncing(true)
    try {
      const res = await fetch('/api/queue/sync', { method: 'POST' })
      const data = await res.json()
      alert(`Sync complete! +${data.new_items} new items. Total: ${data.total}`)
      await fetchQueue()
    } catch {
      alert('Sync failed')
    }
    setSyncing(false)
  }

  const skipItem = async (id: number) => {
    setSkipping(id)
    try {
      await fetch(`/api/queue/skip/${id}`, { method: 'POST' })
      await fetchQueue()
    } catch { /* ignore */ }
    setSkipping(null)
  }

  useEffect(() => { fetchQueue() }, [showProcessed])

  const pending = items.filter(i => !i.is_processed && !i.is_skipped)
  const skipped = items.filter(i => i.is_skipped)
  const processed = items.filter(i => i.is_processed)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

      {/* Header Controls */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="badge badge-info">{pending.length} pending</span>
          <span className="badge badge-muted">{processed.length} processed</span>
          {skipped.length > 0 && <span className="badge badge-warning">{skipped.length} skipped</span>}
        </div>
        <div className="flex gap-2">
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => setShowProcessed(!showProcessed)}
            id="btn-toggle-processed"
          >
            {showProcessed ? 'Hide Processed' : 'Show All'}
          </button>
          <button
            className="btn btn-primary btn-sm"
            onClick={syncQueue}
            disabled={syncing}
            id="btn-sync-queue-page"
          >
            <RefreshCw size={14} />
            {syncing ? 'Syncing...' : 'Sync from Drive'}
          </button>
        </div>
      </div>

      {/* Queue Table */}
      <div className="card" style={{ padding: 0 }}>
        <div className="table-container">
          {loading ? (
            <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
              <div className="loading-spinner" style={{ margin: '0 auto 12px' }} />
              Loading queue...
            </div>
          ) : items.length === 0 ? (
            <div style={{ padding: '60px', textAlign: 'center', color: 'var(--text-muted)' }}>
              <Video size={48} style={{ margin: '0 auto 16px', opacity: 0.3 }} />
              <p style={{ fontSize: '16px', marginBottom: '8px' }}>Queue is empty</p>
              <p style={{ fontSize: '13px' }}>Add videos to your Google Drive Queue folder and sync.</p>
            </div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>#</th>
                  <th>Filename</th>
                  <th>Size</th>
                  <th>Thumbnail</th>
                  <th>Discovered</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item, idx) => (
                  <tr key={item.id}>
                    <td style={{ color: 'var(--text-dim)', fontSize: '11px' }}>{idx + 1}</td>
                    <td>
                      <div className="flex items-center gap-2">
                        <Video size={14} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
                        <span className="td-filename">{item.filename}</span>
                      </div>
                    </td>
                    <td>
                      <div className="flex items-center gap-1">
                        <HardDrive size={12} style={{ color: 'var(--text-dim)' }} />
                        <span style={{ fontSize: '12px' }}>{formatBytes(item.file_size_bytes)}</span>
                      </div>
                    </td>
                    <td>
                      <span className={`badge ${item.has_thumbnail ? 'badge-success' : 'badge-muted'}`}>
                        {item.has_thumbnail ? '✓ Yes' : '— Auto'}
                      </span>
                    </td>
                    <td style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                      {new Date(item.discovered_at).toLocaleDateString()}
                    </td>
                    <td>
                      {item.is_processed ? (
                        <span className="badge badge-success">Processed</span>
                      ) : item.is_skipped ? (
                        <span className="badge badge-warning">Skipped</span>
                      ) : (
                        <span className="badge badge-info">Pending</span>
                      )}
                    </td>
                    <td>
                      {!item.is_processed && !item.is_skipped && (
                        <button
                          className="btn btn-secondary btn-sm btn-icon"
                          title="Skip this video"
                          onClick={() => skipItem(item.id)}
                          disabled={skipping === item.id}
                          id={`btn-skip-${item.id}`}
                        >
                          <SkipForward size={13} />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}
