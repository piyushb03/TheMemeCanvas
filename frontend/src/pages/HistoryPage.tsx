import { useState, useEffect } from 'react'
import { ExternalLink, RefreshCw, Search, Filter } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'

interface UploadRecord {
  id: number
  filename: string
  title: string | null
  status: string
  youtube_video_id: string | null
  youtube_url: string | null
  youtube_status: string | null
  instagram_reel_id: string | null
  instagram_url: string | null
  instagram_status: string | null
  retry_count: number
  created_at: string | null
  completed_at: string | null
  last_error: string | null
}

const STATUS_BADGE = {
  completed: 'badge-success',
  failed: 'badge-error',
  pending: 'badge-info',
  retrying: 'badge-warning',
  skipped: 'badge-muted',
  uploading_youtube: 'badge-info',
  generating_metadata: 'badge-info',
  downloading: 'badge-info',
}

export default function HistoryPage() {
  const [uploads, setUploads] = useState<UploadRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<string>('all')
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(0)
  const pageSize = 25

  const fetchUploads = async () => {
    setLoading(true)
    try {
      const statusParam = filter !== 'all' ? `&status=${filter}` : ''
      const res = await fetch(`/api/uploads?limit=${pageSize}&offset=${page * pageSize}${statusParam}`)
      if (res.ok) setUploads(await res.json())
    } catch { /* ignore */ }
    setLoading(false)
  }

  useEffect(() => { fetchUploads() }, [filter, page])

  const filtered = uploads.filter(u =>
    !search || u.filename.toLowerCase().includes(search.toLowerCase()) ||
    (u.title || '').toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

      {/* Filters */}
      <div className="flex items-center gap-3" style={{ flexWrap: 'wrap' }}>
        <div style={{ position: 'relative', flex: 1, minWidth: '200px' }}>
          <Search size={14} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
          <input
            type="text"
            placeholder="Search by filename or title..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            id="input-history-search"
            style={{
              width: '100%',
              padding: '8px 12px 8px 34px',
              background: 'var(--bg-glass)',
              border: '1px solid var(--border-card)',
              borderRadius: '8px',
              color: 'var(--text-primary)',
              fontSize: '13px',
              outline: 'none',
            }}
          />
        </div>

        <div className="flex gap-2">
          {['all', 'completed', 'failed', 'pending', 'retrying'].map(s => (
            <button
              key={s}
              className={`btn btn-sm ${filter === s ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setFilter(s)}
              id={`btn-filter-${s}`}
            >
              {s.charAt(0).toUpperCase() + s.slice(1)}
            </button>
          ))}
        </div>

        <button className="btn btn-secondary btn-sm" onClick={fetchUploads} id="btn-refresh-history">
          <RefreshCw size={13} />
        </button>
      </div>

      {/* Table */}
      <div className="card" style={{ padding: 0 }}>
        <div className="table-container">
          {loading ? (
            <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
              <div className="loading-spinner" style={{ margin: '0 auto 12px' }} />
              Loading...
            </div>
          ) : filtered.length === 0 ? (
            <div style={{ padding: '60px', textAlign: 'center', color: 'var(--text-muted)' }}>
              <p>No uploads found</p>
            </div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Filename / Title</th>
                  <th>Status</th>
                  <th>YouTube</th>
                  <th>Retries</th>
                  <th>Uploaded</th>
                  <th>Error</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(u => (
                  <tr key={u.id}>
                    <td style={{ color: 'var(--text-dim)', fontSize: '11px' }}>#{u.id}</td>
                    <td style={{ maxWidth: '220px' }}>
                      <div className="td-filename">{u.title || u.filename}</div>
                      {u.title && <div style={{ fontSize: '10px', color: 'var(--text-dim)', marginTop: '2px' }} className="truncate">{u.filename}</div>}
                    </td>
                    <td>
                      <span className={`badge ${STATUS_BADGE[u.status as keyof typeof STATUS_BADGE] || 'badge-muted'}`}>
                        {u.status.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td>
                      {u.youtube_url ? (
                        <a href={u.youtube_url} target="_blank" rel="noopener noreferrer" className="link flex items-center gap-1">
                          <span className="badge badge-success">✓</span>
                          <ExternalLink size={11} />
                        </a>
                      ) : (
                        <span className={`badge ${u.youtube_status === 'failed' ? 'badge-error' : 'badge-muted'}`}>
                          {u.youtube_status || '—'}
                        </span>
                      )}
                    </td>

                    <td style={{ textAlign: 'center' }}>
                      {u.retry_count > 0 ? (
                        <span className="badge badge-warning">{u.retry_count}×</span>
                      ) : '—'}
                    </td>
                    <td style={{ fontSize: '11px', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                      {u.completed_at
                        ? formatDistanceToNow(new Date(u.completed_at), { addSuffix: true })
                        : '—'}
                    </td>
                    <td style={{ maxWidth: '180px' }}>
                      {u.last_error && (
                        <span title={u.last_error} style={{ fontSize: '11px', color: 'var(--error)', cursor: 'help' }} className="truncate">
                          {u.last_error.slice(0, 50)}...
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between">
        <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
          Page {page + 1} · Showing {filtered.length} records
        </span>
        <div className="flex gap-2">
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => setPage(p => Math.max(0, p - 1))}
            disabled={page === 0}
            id="btn-prev-page"
          >← Prev</button>
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => setPage(p => p + 1)}
            disabled={uploads.length < pageSize}
            id="btn-next-page"
          >Next →</button>
        </div>
      </div>
    </div>
  )
}
