import { useState, useEffect } from 'react'
import { CheckCircle, XCircle, AlertCircle, Copy, RefreshCw, FolderOpen, HardDrive } from 'lucide-react'
import Card from '../components/Card'
import Button from '../components/Button'
import { getSettings, checkPaths, checkServices, getEnvTemplate } from '../api'
import api from '../api'

export default function Settings() {
  const [settings, setSettings] = useState(null)
  const [paths, setPaths] = useState(null)
  const [modelPaths, setModelPaths] = useState(null)
  const [services, setServices] = useState(null)
  const [envTemplate, setEnvTemplate] = useState('')
  const [loading, setLoading] = useState(true)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const [settingsRes, pathsRes, servicesRes, envRes, modelPathsRes, storageRes] = await Promise.all([
        getSettings(),
        checkPaths(),
        checkServices(),
        getEnvTemplate(),
        api.get('/settings/model-paths/check'),
        api.get('/cleanup/stats')
      ])
      setSettings({ ...settingsRes.data, storage_stats: storageRes.data })
      setPaths(pathsRes.data)
      setServices(servicesRes.data)
      setEnvTemplate(envRes.data.template)
      setModelPaths(modelPathsRes.data)
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

  const createModelPaths = async () => {
    try {
      await api.post('/settings/model-paths/create')
      loadData()
    } catch (error) {
      console.error('Failed to create paths:', error)
    }
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

      {/* Python & Environment Info */}
      {settings && (
        <Card title="Environment">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 border rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <span className="font-medium text-gray-900">Python Version</span>
                {settings.python_version?.startsWith(settings.required_python_version) ? (
                  <CheckCircle className="h-5 w-5 text-green-500" />
                ) : (
                  <AlertCircle className="h-5 w-5 text-yellow-500" />
                )}
              </div>
              <p className="text-lg font-mono text-gray-700">{settings.python_version}</p>
              <p className="text-xs text-gray-500 mt-1">Recommended: {settings.required_python_version}.x</p>
            </div>
            <div className="p-4 border rounded-lg">
              <span className="font-medium text-gray-900">Project Path</span>
              <p className="text-sm font-mono text-gray-600 mt-2 break-all">{settings.base_path}</p>
            </div>
            <div className="p-4 border rounded-lg">
              <span className="font-medium text-gray-900">Models Path</span>
              <p className="text-sm font-mono text-gray-600 mt-2 break-all">{settings.models_path}</p>
            </div>
          </div>
        </Card>
      )}

      {/* Services Status */}
      <Card title="Services Status">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {services && Object.entries(services).map(([name, info]) => (
            <div key={name} className="p-4 border rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <span className="font-medium text-gray-900 capitalize">{name.replace(/_/g, ' ')}</span>
                {info.status === 'running' || info.status === 'installed' || info.status === 'cli_available' || info.status === 'ok' || info.status === 'configured' ? (
                  <CheckCircle className="h-5 w-5 text-green-500" />
                ) : info.status === 'warning' || info.status === 'disabled' || info.status === 'not_configured' ? (
                  <AlertCircle className="h-5 w-5 text-yellow-500" />
                ) : (
                  <XCircle className="h-5 w-5 text-red-500" />
                )}
              </div>
              <p className="text-sm text-gray-500">{info.status}</p>
              {info.version && <p className="text-xs text-gray-400 mt-1 truncate">{info.version}</p>}
              {info.message && <p className="text-xs text-yellow-600 mt-1">{info.message}</p>}
              {info.models && (
                <div className="mt-2">
                  <p className="text-xs text-gray-500">{info.model_count || info.models.length} models:</p>
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
              {info.voice_count && (
                <p className="text-xs text-gray-500 mt-1">{info.voice_count} voices available</p>
              )}
              {info.error && (
                <p className="text-xs text-red-500 mt-1 truncate" title={info.error}>{info.error}</p>
              )}
              {info.note && (
                <p className="text-xs text-gray-500 mt-1">{info.note}</p>
              )}
              {info.fix && (
                <p className="text-xs text-blue-700 mt-2 p-2 bg-blue-50 rounded border border-blue-100" title={info.fix}>
                  How to configure: {info.fix}
                </p>
              )}
            </div>
          ))}
        </div>
      </Card>

      {/* Model Cache Paths */}
      <Card
        title="Model Cache Directories"
        actions={
          <Button variant="secondary" size="sm" onClick={createModelPaths}>
            <FolderOpen className="h-4 w-4" />
            Create Missing
          </Button>
        }
      >
        <p className="text-sm text-gray-500 mb-4">
          Models are cached locally in these directories. Set <code className="px-1 py-0.5 bg-gray-100 rounded">OLLAMA_MODELS</code> environment variable to store Ollama models here.
        </p>
        <div className="space-y-2">
          {modelPaths && Object.entries(modelPaths).filter(([name]) => name !== 'ollama_models_env').map(([name, info]) => (
            <div key={name} className="flex items-center justify-between py-2 border-b last:border-0">
              <div className="flex-1 min-w-0">
                <span className="font-medium text-gray-900">{name.replace(/_/g, ' ')}</span>
                <p className="text-sm text-gray-500 font-mono truncate">{info.path}</p>
              </div>
              <div className="flex items-center gap-3 ml-4">
                {info.size_mb > 0 && (
                  <span className="text-xs text-gray-500 flex items-center gap-1">
                    <HardDrive className="h-3 w-3" />
                    {info.size_mb} MB
                  </span>
                )}
                {info.exists ? (
                  <div className="flex items-center gap-1">
                    <CheckCircle className="h-5 w-5 text-green-500" />
                    {info.writable && <span className="text-xs text-green-600">writable</span>}
                  </div>
                ) : (
                  <XCircle className="h-5 w-5 text-red-500" />
                )}
              </div>
            </div>
          ))}
          {modelPaths?.ollama_models_env && (
            <div className="mt-4 p-3 bg-blue-50 rounded-lg">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-blue-900">OLLAMA_MODELS Environment Variable:</span>
                {modelPaths.ollama_models_env.is_set ? (
                  <CheckCircle className="h-4 w-4 text-green-500" />
                ) : (
                  <AlertCircle className="h-4 w-4 text-yellow-500" />
                )}
              </div>
              {modelPaths.ollama_models_env.is_set ? (
                <p className="text-xs font-mono text-blue-700 mt-1">{modelPaths.ollama_models_env.value}</p>
              ) : (
                <p className="text-xs text-blue-600 mt-1">
                  Not set. Run: <code className="bg-blue-100 px-1 rounded">setx OLLAMA_MODELS "D:\Ideas\content_factory\models\ollama"</code>
                </p>
              )}
            </div>
          )}
        </div>
      </Card>

      {/* Data Paths Status */}
      <Card title="Data Directories">
        <div className="space-y-2">
          {paths && Object.entries(paths).map(([name, info]) => (
            <div key={name} className="flex items-center justify-between py-2 border-b last:border-0">
              <div className="flex-1 min-w-0">
                <span className="font-medium text-gray-900">{name.replace(/_/g, ' ')}</span>
                <p className="text-sm text-gray-500 font-mono truncate">{info.path}</p>
              </div>
              <div className="flex items-center gap-2 ml-4">
                {info.exists ? (
                  <div className="flex items-center gap-1">
                    <CheckCircle className="h-5 w-5 text-green-500" />
                    {info.writable && <span className="text-xs text-green-600">writable</span>}
                  </div>
                ) : (
                  <XCircle className="h-5 w-5 text-red-500" />
                )}
              </div>
            </div>
          ))}
        </div>
      </Card>

      {/* Current Settings */}
      <Card title="Current Configuration">
        {settings && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h4 className="font-medium text-gray-900 mb-3">LLM</h4>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-500">Provider</span>
                  <span className="text-gray-900">{settings.llm_provider}</span>
                </div>
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
                {settings.llm_provider === 'mcp' && (
                  <>
                    <div className="flex justify-between">
                      <span className="text-gray-500">MCP Connector</span>
                      <span className="text-gray-900">{settings.mcp_llm_connector || 'not set'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">MCP Model</span>
                      <span className="text-gray-900">{settings.mcp_llm_model || 'not set'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-500">MCP Path</span>
                      <span className="text-gray-900">{settings.mcp_llm_path || 'not set'}</span>
                    </div>
                  </>
                )}
              </div>
            </div>

            <div>
              <h4 className="font-medium text-gray-900 mb-3">TTS</h4>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-500">Provider</span>
                  <span className="text-gray-900">{settings.tts_provider}</span>
                </div>
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
                <div className="flex justify-between">
                  <span className="text-gray-500">Compute Type</span>
                  <span className="text-gray-900">{settings.whisper_compute_type}</span>
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
                <div className="flex justify-between">
                  <span className="text-gray-500">Video Provider</span>
                  <span className="text-gray-900">{settings.video_gen_provider}</span>
                </div>
                {settings.video_gen_provider === 'ltx' && (
                  <div className="flex justify-between">
                    <span className="text-gray-500">LTX API</span>
                    <span className="text-gray-900 font-mono">{settings.ltx_api_url || 'not set'}</span>
                  </div>
                )}
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

      {/* Storage & Cleanup */}
      <Card title="Storage & Cleanup">
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="p-4 border rounded-lg bg-gray-50">
              <span className="text-sm text-gray-500">Total Usage</span>
              <p className="text-2xl font-bold text-gray-900 mt-1">
                {settings?.storage_stats?.total_mb ? `${(settings.storage_stats.total_mb / 1024).toFixed(2)} GB` : 'Loading...'}
              </p>
            </div>
            <div className="p-4 border rounded-lg">
              <span className="text-sm text-gray-500">Outputs</span>
              <p className="text-lg font-semibold text-gray-900 mt-1">
                {settings?.storage_stats?.outputs_mb ? `${settings.storage_stats.outputs_mb} MB` : '0 MB'}
              </p>
            </div>
            <div className="p-4 border rounded-lg">
              <span className="text-sm text-gray-500">Uploads</span>
              <p className="text-lg font-semibold text-gray-900 mt-1">
                {settings?.storage_stats?.uploads_mb ? `${settings.storage_stats.uploads_mb} MB` : '0 MB'}
              </p>
            </div>
            <div className="p-4 border rounded-lg">
              <span className="text-sm text-gray-500">Logs</span>
              <p className="text-lg font-semibold text-gray-900 mt-1">
                {settings?.storage_stats?.logs_mb ? `${settings.storage_stats.logs_mb} MB` : '0 MB'}
              </p>
            </div>
          </div>

          <div className="border-t pt-4">
            <h4 className="font-medium text-gray-900 mb-3">Cleanup Actions</h4>
            <div className="flex flex-wrap gap-3">
              <Button
                variant="secondary"
                onClick={async () => {
                  if (confirm('Run cleanup (dry run)? Check logs for details.')) {
                    await api.post('/cleanup/run?dry_run=true')
                    alert('Dry run complete. Check logs.')
                  }
                }}
              >
                Dry Run Cleanup
              </Button>
              <Button
                variant="danger"
                onClick={async () => {
                  if (confirm('Are you sure? This will DELETE old files permanently.')) {
                    await api.post('/cleanup/run?dry_run=false')
                    loadData()
                    alert('Cleanup complete!')
                  }
                }}
              >
                Run Full Cleanup
              </Button>
            </div>
            <p className="text-xs text-gray-500 mt-2">
              Deletes files older than retention policy (default: Videos 1 day, Temp 12h, Logs 7 days).
            </p>
          </div>
        </div>
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
          Copy this template and save it as <code className="px-1 py-0.5 bg-gray-100 rounded">backend\.env</code>
        </p>
        <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto text-sm max-h-96">
          {envTemplate}
        </pre>
      </Card>
    </div>
  )
}
