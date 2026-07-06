import { Info, ExternalLink } from 'lucide-react'

interface ConfigRow {
  key: string
  envVar: string
  description: string
  required: boolean
  link?: string
}

const CONFIGS: { section: string; items: ConfigRow[] }[] = [
  {
    section: '🔑 Google Drive',
    items: [
      { key: 'Queue Folder ID', envVar: 'DRIVE_QUEUE_FOLDER_ID', description: 'ID of the folder containing your video queue', required: true, link: 'https://drive.google.com' },
      { key: 'Uploaded Folder ID', envVar: 'DRIVE_UPLOADED_FOLDER_ID', description: 'ID of the folder for processed videos', required: true },
      { key: 'Failed Folder ID', envVar: 'DRIVE_FAILED_FOLDER_ID', description: 'ID of the folder for failed uploads', required: true },
      { key: 'Service Account JSON', envVar: 'GOOGLE_SERVICE_ACCOUNT_FILE', description: 'Path to Google service account credentials file', required: false },
      { key: 'OAuth Client Secrets', envVar: 'GOOGLE_OAUTH_CLIENT_SECRETS_FILE', description: 'Path to OAuth2 client secrets JSON (alternative to service account)', required: false },
    ]
  },
  {
    section: '📺 YouTube',
    items: [
      { key: 'Channel ID', envVar: 'YOUTUBE_CHANNEL_ID', description: 'Your YouTube channel ID (found in YouTube Studio)', required: true, link: 'https://studio.youtube.com' },
      { key: 'OAuth Client Secrets', envVar: 'YOUTUBE_OAUTH_CLIENT_SECRETS_FILE', description: 'Path to YouTube OAuth2 client secrets JSON', required: true },
      { key: 'Privacy Status', envVar: 'YOUTUBE_PRIVACY_STATUS', description: 'public | private | unlisted', required: false },
      { key: 'Category ID', envVar: 'YOUTUBE_CATEGORY_ID', description: '23=Comedy, 24=Entertainment, 10=Music', required: false },
    ]
  },

  {
    section: '🤖 Groq AI',
    items: [
      { key: 'Groq API Key', envVar: 'GROQ_API_KEY', description: 'Your Groq API key', required: true, link: 'https://console.groq.com/keys' },
      { key: 'Groq Model', envVar: 'GROQ_MODEL', description: 'e.g. llama3-70b-8192', required: false },
    ]
  },
  {
    section: '🔔 Telegram',
    items: [
      { key: 'Bot Token', envVar: 'TELEGRAM_BOT_TOKEN', description: 'Token from @BotFather on Telegram', required: false, link: 'https://t.me/BotFather' },
      { key: 'Chat ID', envVar: 'TELEGRAM_CHAT_ID', description: 'Your personal chat ID (get from @userinfobot)', required: false },
    ]
  },

  {
    section: '⏰ Scheduler',
    items: [
      { key: 'Upload Time', envVar: 'UPLOAD_TIME', description: 'Time to upload daily (HH:MM, 24-hour)', required: false },
      { key: 'Timezone', envVar: 'TIMEZONE', description: 'e.g. Asia/Kolkata, America/New_York, Europe/London', required: false },
      { key: 'Upload Order', envVar: 'UPLOAD_ORDER', description: 'oldest_first | newest_first | random', required: false },
    ]
  },
]

export default function SettingsPage() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>

      {/* Alert */}
      <div className="alert alert-info">
        <Info size={16} style={{ flexShrink: 0 }} />
        <span>
          All settings are configured via the <code style={{ background: 'rgba(255,255,255,0.1)', padding: '1px 6px', borderRadius: '4px' }}>.env</code> file in the project root.
          Copy <code style={{ background: 'rgba(255,255,255,0.1)', padding: '1px 6px', borderRadius: '4px' }}>.env.example</code> to <code style={{ background: 'rgba(255,255,255,0.1)', padding: '1px 6px', borderRadius: '4px' }}>.env</code> and fill in your values.
          Restart the server after changes.
        </span>
      </div>

      {/* Config Sections */}
      {CONFIGS.map(({ section, items }) => (
        <div key={section} className="card">
          <div className="card-header">
            <span className="card-title">{section}</span>
          </div>
          <div className="table-container" style={{ border: 'none', borderRadius: 0 }}>
            <table>
              <thead>
                <tr>
                  <th>Setting</th>
                  <th>Environment Variable</th>
                  <th>Description</th>
                  <th>Required</th>
                </tr>
              </thead>
              <tbody>
                {items.map(item => (
                  <tr key={item.envVar}>
                    <td style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{item.key}</td>
                    <td>
                      <div className="flex items-center gap-2">
                        <code style={{
                          background: 'rgba(124,58,237,0.15)',
                          color: 'var(--brand-accent)',
                          padding: '2px 8px',
                          borderRadius: '4px',
                          fontSize: '11px',
                          fontFamily: 'var(--font-mono)',
                        }}>{item.envVar}</code>
                        {item.link && (
                          <a href={item.link} target="_blank" rel="noopener noreferrer" className="link">
                            <ExternalLink size={12} />
                          </a>
                        )}
                      </div>
                    </td>
                    <td style={{ fontSize: '12px', color: 'var(--text-muted)', maxWidth: '300px' }}>{item.description}</td>
                    <td>
                      <span className={`badge ${item.required ? 'badge-error' : 'badge-muted'}`}>
                        {item.required ? 'Required' : 'Optional'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}

      {/* Quick Instructions */}
      <div className="card">
        <div className="card-header">
          <span className="card-title">📚 Quick Setup Guide</span>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '13px', color: 'var(--text-secondary)' }}>
          {[
            ['1. Google Cloud Project', 'Create a project at console.cloud.google.com. Enable Google Drive API and YouTube Data API v3.'],
            ['2. YouTube OAuth2', 'Create OAuth 2.0 credentials (Desktop app). Download the client_secrets.json file to credentials/.'],
            ['3. Google Drive Setup', 'Create 3 folders in Google Drive: Queue, Uploaded, Failed. Copy their IDs from the browser URL.'],
            ['4. Groq API Key', 'Get your API key at console.groq.com. llama3-70b-8192 is recommended.'],
            ['5. Telegram Bot', 'Message @BotFather on Telegram: /newbot. Copy the token. Get your Chat ID from @userinfobot.'],
            ['6. First Run', 'Copy .env.example to .env, fill all values, then run: docker-compose up -d or python -m uvicorn app.main:app'],
          ].map(([title, desc]) => (
            <div key={title} style={{ display: 'flex', gap: '12px', padding: '12px', background: 'var(--bg-glass)', borderRadius: '8px' }}>
              <span style={{ color: 'var(--brand-accent)', fontWeight: 700, whiteSpace: 'nowrap' }}>{title}</span>
              <span style={{ color: 'var(--text-muted)' }}>{desc}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
