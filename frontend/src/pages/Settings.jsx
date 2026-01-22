import { useState, useEffect } from 'react'
import { CheckCircle, XCircle, AlertCircle, Copy, RefreshCw } from 'lucide-react'
import Card from '../components/Card'
import Button from '../components/Button'
import { getSettings, checkPaths, checkServices, getEnvTemplate } from '../api'

export default function Settings() {
  const [settings, setSettings] = useState(null)
  const [paths, setPaths] = useState(null)
  const [services, setServices] = useState(null)
  const [envTemplate, setEnvTemplate] = useState('')
  const [loading, setLoading] = useState(true)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const [settingsRes, pathsRes, servicesRes, envRes] = await Promise.all([
        getSettings(),
        checkPaths(),
        checkServices(),
        getEnvTemplate()
      ])
      setSettings(settingsRes.data)
      setPaths(pathsRes.data)
      setServices(servicesRes.data)
      setEnvTemplate(envRes.data.template)
    } catch (error) {
      console.error('Failed to load settings:', error)
    } finally {
      setLoading(false)
    }
  }

  const copyEnvTemplate = () => {
    navigator.clipboard.writeText(envTemplate)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  if (loading) {
    return <div className="flex items-center justify-center h-64">Loading...</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Settings</h1>
        <Button variant="secondary" onClick={loadData}>
          <RefreshCw className="h-4 w-4" />
          Refresh
        </Button>
      </div>

      {/* Services Status */}
      <Card title="Services Status">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {services && Object.entries(services).map(([name, info]) => (
            <div key={name} className="p-4 border rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <span className="font-medium text-gray-900 capitalize">{name.replace('_', ' ')}</span>
                {info.status === 'running' || info.status === 'installed' || info.status === 'cli_available' ? (
                  <CheckCircle className="h-5 w-5 text-green-500" />
                ) : (
                  <XCircle className="h-5 w-5 text-red-500" />
                )}
              </div>
              <p className="text-sm text-gray-500">{info.status}</p>
              {info.version && <p className="text-xs text-gray-400 mt-1">{info.version}</p>}
              {info.models && (
                <div className="mt-2">
                  <p className="text-xs text-gray-500">Models:</p>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {info.models.slice(0, 3).map((model, i) => (
                      <span key={i} className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs">
                        {model}
                      </span>
                    ))}
                    {info.models.length > 3 && (
                      <span className="text-xs text-gray-400">+{info.models.length - 3} more</span>
                    )}
                  </div>
                </div>
              )}
              {info.error && (
                <p className="text-xs text-red-500 mt-1">{info.error}</p>
              )}
            </div>
          ))}
        </div>
      </Card>

      {/* Paths Status */}
      <Card title="Directory Status">
        <div className="space-y-2">
          {paths && Object.entries(paths).map(([name, info]) => (
            <div key={name} className="flex items-center justify-between py-2 border-b last:border-0">
              <div>
                <span className="font-medium text-gray-900">{name.replace(/_/g, ' ')}</span>
                <p className="text-sm text-gray-500 font-mono">{info.path}</p>
              </div>
              {info.exists ? (
                <CheckCircle className="h-5 w-5 text-green-500" />
              ) : (
                <XCircle className="h-5 w-5 text-red-500" />
              )}
            </div>
          ))}
        </div>
      </Card>

      {/* Current Settings */}
      <Card title="Current Configuration">
        {settings && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h4 className="font-medium text-gray-900 mb-3">LLM (Ollama)</h4>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-500">Base URL</span>
                  <span className="text-gray-900 font-mono">{settings.ollama_base_url}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Main Model</span>
                  <span className="text-gray-900">{settings.ollama_model}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Fast Model</span>
                  <span className="text-gray-900">{settings.ollama_fast_model}</span>
                </div>
              </div>
            </div>

            <div>
              <h4 className="font-medium text-gray-900 mb-3">TTS</h4>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-500">XTTS Enabled</span>
                  <span className="text-gray-900">{settings.xtts_enabled ? 'Yes' : 'No'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">ElevenLabs</span>
                  <span className="text-gray-900">{settings.elevenlabs_configured ? 'Configured' : 'Not configured'}</span>
                </div>
              </div>
            </div>

            <div>
              <h4 className="font-medium text-gray-900 mb-3">Whisper</h4>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-500">Model</span>
                  <span className="text-gray-900">{settings.whisper_model}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Device</span>
                  <span className="text-gray-900">{settings.whisper_device}</span>
                </div>
              </div>
            </div>

            <div>
              <h4 className="font-medium text-gray-900 mb-3">Video Defaults</h4>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-500">Resolution</span>
                  <span className="text-gray-900">{settings.default_video_width}x{settings.default_video_height}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">FPS</span>
                  <span className="text-gray-900">{settings.default_video_fps}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">BG Music Volume</span>
                  <span className="text-gray-900">{(settings.default_bg_music_volume * 100).toFixed(0)}%</span>
                </div>
              </div>
            </div>

            <div>
              <h4 className="font-medium text-gray-900 mb-3">Worker</h4>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-500">Enabled</span>
                  <span className="text-gray-900">{settings.worker_enabled ? 'Yes' : 'No'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Interval</span>
                  <span className="text-gray-900">{settings.worker_interval_seconds}s</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Max Concurrent</span>
                  <span className="text-gray-900">{settings.max_concurrent_jobs}</span>
                </div>
              </div>
            </div>

            <div>
              <h4 className="font-medium text-gray-900 mb-3">Platforms</h4>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between items-center">
                  <span className="text-gray-500">YouTube</span>
                  {settings.youtube_configured ? (
                    <span className="flex items-center gap-1 text-green-600">
                      <CheckCircle className="h-4 w-4" /> Connected
                    </span>
                  ) : (
                    <span className="text-gray-400">Not configured</span>
                  )}
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-500">Instagram</span>
                  {settings.instagram_configured ? (
                    <span className="flex items-center gap-1 text-green-600">
                      <CheckCircle className="h-4 w-4" /> Connected
                    </span>
                  ) : (
                    <span className="text-gray-400">Not configured</span>
                  )}
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-500">TikTok</span>
                  {settings.tiktok_configured ? (
                    settings.tiktok_verified ? (
                      <span className="flex items-center gap-1 text-green-600">
                        <CheckCircle className="h-4 w-4" /> Verified
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-yellow-600">
                        <AlertCircle className="h-4 w-4" /> Unverified
                      </span>
                    )
                  ) : (
                    <span className="text-gray-400">Not configured</span>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </Card>

      {/* Environment Template */}
      <Card 
        title=".env Template"
        actions={
          <Button variant="secondary" size="sm" onClick={copyEnvTemplate}>
            <Copy className="h-4 w-4" />
            {copied ? 'Copied!' : 'Copy'}
          </Button>
        }
      >
        <p className="text-sm text-gray-500 mb-4">
          Copy this template and save it as <code className="px-1 py-0.5 bg-gray-100 rounded">.env</code> in the backend folder.
        </p>
        <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto text-sm">
          {envTemplate}
        </pre>
      </Card>
    </div>
  )
}
