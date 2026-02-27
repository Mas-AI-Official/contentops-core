import { useState, useEffect, useRef } from 'react'
import { Youtube, Instagram, Music2, CheckCircle, AlertCircle, XCircle, RefreshCw, Plus, Trash2, Monitor, ExternalLink, Shield } from 'lucide-react'
import Card from '../components/Card'
import Button from '../components/Button'
import {
  getPublishingAccounts,
  addPublishingAccount,
  deletePublishingAccount,
  openBrowserLogin,
  verifyBrowserLogin
} from '../api'

const PLATFORMS = {
  youtube: { name: 'YouTube', icon: Youtube, color: 'text-red-600', bg: 'bg-red-50' },
  instagram: { name: 'Instagram', icon: Instagram, color: 'text-pink-600', bg: 'bg-pink-50' },
  tiktok: { name: 'TikTok', icon: Music2, color: 'text-gray-800', bg: 'bg-gray-100' },
}

export default function Accounts() {
  const [accounts, setAccounts] = useState([])
  const [loading, setLoading] = useState(true)
  const [showAddModal, setShowAddModal] = useState(false)
  const [newAccount, setNewAccount] = useState({ platform: 'youtube', handle: '', display_name: '', mode: 'auto_smart' })
  const [liveBrowser, setLiveBrowser] = useState(false)
  const wsRef = useRef(null)
  const [browserImage, setBrowserImage] = useState(null)
  const [browserStatus, setBrowserStatus] = useState('Connecting...')

  useEffect(() => {
    loadAccounts()
    return () => {
      if (wsRef.current) wsRef.current.close()
    }
  }, [])

  useEffect(() => {
    if (liveBrowser) {
      connectWebSocket()
    } else {
      if (wsRef.current) wsRef.current.close()
    }
  }, [liveBrowser])

  const connectWebSocket = () => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.hostname}:8000/api/publishing/browser/live`

    wsRef.current = new WebSocket(wsUrl)

    wsRef.current.onopen = () => {
      setBrowserStatus('Connected to Live Browser')
    }

    wsRef.current.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.type === 'screenshot') {
        setBrowserImage(`data:image/jpeg;base64,${data.image}`)
      } else if (data.type === 'status') {
        setBrowserStatus(data.message)
        setBrowserImage(null)
      }
    }

    wsRef.current.onclose = () => {
      setBrowserStatus('Disconnected')
    }
  }

  const loadAccounts = async () => {
    try {
      const res = await getPublishingAccounts()
      setAccounts(res.data.accounts)
    } catch (error) {
      console.error('Failed to load accounts:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleAddAccount = async () => {
    try {
      await addPublishingAccount(newAccount)
      setShowAddModal(false)
      loadAccounts()
      setNewAccount({ platform: 'youtube', handle: '', display_name: '', mode: 'auto_smart' })
    } catch (error) {
      console.error('Failed to add account:', error)
      alert('Failed to add account')
    }
  }

  const handleDelete = async (id) => {
    if (!confirm('Are you sure you want to remove this account?')) return
    try {
      await deletePublishingAccount(id)
      loadAccounts()
    } catch (error) {
      console.error('Failed to delete account:', error)
    }
  }

  const handleBrowserLogin = async (id) => {
    try {
      setLiveBrowser(true)
      await openBrowserLogin(id)
    } catch (error) {
      console.error('Failed to open browser:', error)
      alert(error.response?.data?.detail || 'Failed to open browser')
    }
  }

  const handleVerifyLogin = async (id) => {
    try {
      const res = await verifyBrowserLogin(id)
      if (res.data.status === 'logged_in') {
        alert('Login verified successfully!')
        loadAccounts()
      } else {
        alert('Not logged in yet. Please complete login in the browser.')
      }
    } catch (error) {
      console.error('Failed to verify login:', error)
    }
  }

  if (loading) return <div className="flex justify-center p-12">Loading...</div>

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Publishing Accounts</h1>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => setLiveBrowser(!liveBrowser)}>
            <Monitor className="h-4 w-4 mr-2" />
            {liveBrowser ? 'Hide Browser' : 'Live Browser'}
          </Button>
          <Button onClick={() => setShowAddModal(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Add Account
          </Button>
        </div>
      </div>

      {/* Live Browser View (Manus-style) */}
      {liveBrowser && (
        <Card className="bg-gray-900 text-white overflow-hidden border-gray-800">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
              <span className="font-mono text-sm">LIVE BROWSER VIEW</span>
            </div>
            <span className="text-xs text-gray-400">{browserStatus}</span>
          </div>

          <div className="aspect-video bg-black rounded-lg flex items-center justify-center overflow-hidden border border-gray-700 relative">
            {browserImage ? (
              <img src={browserImage} alt="Live Browser" className="w-full h-full object-contain" />
            ) : (
              <div className="text-center text-gray-500">
                <Monitor className="h-12 w-12 mx-auto mb-2 opacity-50" />
                <p>Waiting for browser session...</p>
              </div>
            )}
          </div>
        </Card>
      )}

      {/* Accounts List */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {accounts.map(account => {
          const PlatformIcon = PLATFORMS[account.platform]?.icon || AlertCircle
          const platformColor = PLATFORMS[account.platform]?.color || 'text-gray-600'
          const platformBg = PLATFORMS[account.platform]?.bg || 'bg-gray-100'

          return (
            <Card key={account.id} className="relative group">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg ${platformBg}`}>
                    <PlatformIcon className={`h-6 w-6 ${platformColor}`} />
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900">{account.display_name}</h3>
                    <p className="text-sm text-gray-500">@{account.handle}</p>
                  </div>
                </div>
                <div className={`px-2 py-1 rounded-full text-xs font-medium ${account.status === 'connected' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
                  }`}>
                  {account.status === 'connected' ? 'Connected' : 'Needs Login'}
                </div>
              </div>

              <div className="mt-4 space-y-2">
                <div className="flex items-center justify-between text-xs text-gray-500">
                  <span>Mode:</span>
                  <span className="font-medium capitalize">{account.mode.replace('_', ' ')}</span>
                </div>
                <div className="flex items-center justify-between text-xs text-gray-500">
                  <span>Auto-Confirm:</span>
                  <span className="font-medium">{account.auto_confirm ? 'Yes' : 'No'}</span>
                </div>
              </div>

              <div className="mt-4 flex gap-2">
                {account.status !== 'connected' ? (
                  <>
                    <Button size="sm" variant="secondary" className="flex-1" onClick={() => handleBrowserLogin(account.id)}>
                      <ExternalLink className="h-3 w-3 mr-1" />
                      Login
                    </Button>
                    <Button size="sm" className="flex-1" onClick={() => handleVerifyLogin(account.id)}>
                      <CheckCircle className="h-3 w-3 mr-1" />
                      Verify
                    </Button>
                  </>
                ) : (
                  <Button size="sm" variant="secondary" className="flex-1" onClick={() => handleBrowserLogin(account.id)}>
                    <Monitor className="h-3 w-3 mr-1" />
                    Open Browser
                  </Button>
                )}
                <button
                  onClick={() => handleDelete(account.id)}
                  className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </Card>
          )
        })}

        {/* Add New Card */}
        <button
          onClick={() => setShowAddModal(true)}
          className="flex flex-col items-center justify-center p-6 border-2 border-dashed border-gray-200 rounded-xl hover:border-primary-500 hover:bg-primary-50 transition-all group h-full min-h-[200px]"
        >
          <div className="p-3 rounded-full bg-gray-100 group-hover:bg-primary-100 transition-colors">
            <Plus className="h-6 w-6 text-gray-400 group-hover:text-primary-600" />
          </div>
          <p className="mt-3 font-medium text-gray-600 group-hover:text-primary-700">Add Account</p>
        </button>
      </div>

      {/* Add Account Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-md">
            <h2 className="text-xl font-bold mb-4">Add Publishing Account</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Platform</label>
                <select
                  value={newAccount.platform}
                  onChange={e => setNewAccount({ ...newAccount, platform: e.target.value })}
                  className="w-full rounded-lg border-gray-300"
                >
                  <option value="youtube">YouTube</option>
                  <option value="instagram">Instagram</option>
                  <option value="tiktok">TikTok</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Handle (@username)</label>
                <input
                  type="text"
                  value={newAccount.handle}
                  onChange={e => setNewAccount({ ...newAccount, handle: e.target.value })}
                  className="w-full rounded-lg border-gray-300"
                  placeholder="e.g. mychannel"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Display Name</label>
                <input
                  type="text"
                  value={newAccount.display_name}
                  onChange={e => setNewAccount({ ...newAccount, display_name: e.target.value })}
                  className="w-full rounded-lg border-gray-300"
                  placeholder="e.g. My Channel"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Publishing Mode</label>
                <select
                  value={newAccount.mode}
                  onChange={e => setNewAccount({ ...newAccount, mode: e.target.value })}
                  className="w-full rounded-lg border-gray-300"
                >
                  <option value="auto_smart">Auto Smart (API + Browser Fallback)</option>
                  <option value="browser_assist">Browser Assist Only</option>
                  <option value="auto_api">API Only</option>
                </select>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="auto_confirm"
                  checked={newAccount.auto_confirm}
                  onChange={e => setNewAccount({ ...newAccount, auto_confirm: e.target.checked })}
                  className="rounded border-gray-300 text-primary-600"
                />
                <label htmlFor="auto_confirm" className="text-sm text-gray-700">
                  Auto-Confirm (Skip manual review)
                </label>
              </div>
            </div>
            <div className="mt-6 flex justify-end gap-2">
              <Button variant="secondary" onClick={() => setShowAddModal(false)}>Cancel</Button>
              <Button onClick={handleAddAccount}>Add Account</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
