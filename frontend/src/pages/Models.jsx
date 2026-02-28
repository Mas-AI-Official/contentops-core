import { useState, useEffect } from 'react'
import { Download, Trash2, Play, Check, AlertCircle, RefreshCw, HardDrive } from 'lucide-react'
import Card from '../components/Card'
import Button from '../components/Button'
import Modal from '../components/Modal'
import api from '../api'

export default function Models() {
  const [installedModels, setInstalledModels] = useState([])
  const [availableModels, setAvailableModels] = useState({ recommended: [], large: [] })
  const [ltxModels, setLtxModels] = useState({ models: [], total: 0, total_size_gb: 0 })
  const [currentModels, setCurrentModels] = useState({})
  const [loading, setLoading] = useState(true)
  const [pulling, setPulling] = useState({})
  const [testResults, setTestResults] = useState({})
  const [showDeleteModal, setShowDeleteModal] = useState(null)
  const [activeTab, setActiveTab] = useState('ollama') // 'ollama' or 'ltx'

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const [installedRes, availableRes, currentRes, ltxRes] = await Promise.all([
        api.get('/models/'),
        api.get('/models/available'),
        api.get('/models/current'),
        api.get('/models/ltx').catch(() => ({ data: { models: [], total: 0, total_size_gb: 0, message: 'LTX not enabled' } }))
      ])
      setInstalledModels(installedRes.data)
      setAvailableModels(availableRes.data)
      setCurrentModels(currentRes.data)
      setLtxModels(ltxRes.data)
    } catch (error) {
      console.error('Failed to load models:', error)
    } finally {
      setLoading(false)
    }
  }

  const handlePull = async (modelName) => {
    setPulling(prev => ({ ...prev, [modelName]: { status: 'starting', progress: 0 } }))

    try {
      await api.post('/models/pull', { model_name: modelName })

      // Poll for progress
      const pollInterval = setInterval(async () => {
        try {
          const res = await api.get(`/models/pull/${modelName}/status`)
          setPulling(prev => ({
            ...prev,
            [modelName]: {
              status: res.data.status,
              progress: res.data.progress || 0,
              message: res.data.message
            }
          }))

          if (res.data.status === 'completed' || res.data.status === 'failed') {
            clearInterval(pollInterval)
            if (res.data.status === 'completed') {
              loadData()
            }
          }
        } catch (e) {
          clearInterval(pollInterval)
        }
      }, 1000)

    } catch (error) {
      console.error('Failed to pull model:', error)
      setPulling(prev => ({ ...prev, [modelName]: { status: 'failed', message: error.message } }))
    }
  }

  const handleDelete = async (modelName) => {
    try {
      await api.delete(`/models/${encodeURIComponent(modelName)}`)
      setShowDeleteModal(null)
      loadData()
    } catch (error) {
      console.error('Failed to delete model:', error)
    }
  }

  const handleTest = async (modelName) => {
    setTestResults(prev => ({ ...prev, [modelName]: { status: 'testing' } }))
    try {
      const res = await api.post(`/models/test/${encodeURIComponent(modelName)}`)
      setTestResults(prev => ({ ...prev, [modelName]: res.data }))
    } catch (error) {
      setTestResults(prev => ({ ...prev, [modelName]: { status: 'failed', error: error.message } }))
    }
  }

  const isModelInstalled = (modelName) => {
    return installedModels.some(m => m.name === modelName || m.name.startsWith(modelName.split(':')[0]))
  }

  if (loading) {
    return <div className="flex items-center justify-center h-64">Loading...</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Model Management</h1>
        <Button variant="secondary" onClick={loadData}>
          <RefreshCw className="h-4 w-4" />
          Refresh
        </Button>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex space-x-8">
          <button
            onClick={() => setActiveTab('ollama')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${activeTab === 'ollama'
                ? 'border-primary-500 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
          >
            Ollama Models
          </button>
          <button
            onClick={() => setActiveTab('ltx')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${activeTab === 'ltx'
                ? 'border-primary-500 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
          >
            LTX-2 Video Models
          </button>
        </nav>
      </div>

      {activeTab === 'ltx' ? (
        <LTXModelsSection ltxModels={ltxModels} />
      ) : (
        <>

          {/* Current Configuration */}
          <Card title="Current Configuration">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-500">Main Model</p>
                <p className="font-semibold text-gray-900">{currentModels.main_model}</p>
                <p className="text-xs text-gray-400">Used for script generation</p>
              </div>
              <div className="p-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-500">Fast Model</p>
                <p className="font-semibold text-gray-900">{currentModels.fast_model}</p>
                <p className="text-xs text-gray-400">Used for topic generation</p>
              </div>
              <div className="p-4 bg-gray-50 rounded-lg">
                <p className="text-sm text-gray-500">Ollama URL</p>
                <p className="font-semibold text-gray-900 text-sm">{currentModels.ollama_url}</p>
              </div>
            </div>
            <p className="mt-4 text-sm text-gray-500">
              To change models, edit the <code className="px-1 py-0.5 bg-gray-100 rounded">backend/.env</code> file
              and set <code className="px-1 py-0.5 bg-gray-100 rounded">OLLAMA_MODEL</code> and
              <code className="px-1 py-0.5 bg-gray-100 rounded">OLLAMA_FAST_MODEL</code>.
            </p>
          </Card>

          {/* Installed Models */}
          <Card title={`Installed Models (${installedModels.length})`}>
            {installedModels.length === 0 ? (
              <p className="text-gray-500 text-center py-8">No models installed. Download one below!</p>
            ) : (
              <div className="space-y-3">
                {installedModels.map((model) => (
                  <div key={model.name} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                    <div className="flex items-center gap-3">
                      <HardDrive className="h-5 w-5 text-gray-400" />
                      <div>
                        <p className="font-medium text-gray-900">{model.name}</p>
                        <p className="text-sm text-gray-500">{model.size}</p>
                      </div>
                      {(model.name === currentModels.main_model || model.name === currentModels.fast_model) && (
                        <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs rounded-full">
                          Active
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => handleTest(model.name)}
                        loading={testResults[model.name]?.status === 'testing'}
                      >
                        <Play className="h-4 w-4" />
                        Test
                      </Button>
                      <Button
                        size="sm"
                        variant="danger"
                        onClick={() => setShowDeleteModal(model.name)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Test Results */}
            {Object.entries(testResults).filter(([_, r]) => r.status !== 'testing').length > 0 && (
              <div className="mt-4 pt-4 border-t">
                <h4 className="text-sm font-medium text-gray-700 mb-2">Test Results</h4>
                {Object.entries(testResults).map(([model, result]) => (
                  result.status !== 'testing' && (
                    <div key={model} className={`p-3 rounded-lg mb-2 ${result.status === 'working' ? 'bg-green-50' : 'bg-red-50'
                      }`}>
                      <div className="flex items-center gap-2">
                        {result.status === 'working' ? (
                          <Check className="h-4 w-4 text-green-600" />
                        ) : (
                          <AlertCircle className="h-4 w-4 text-red-600" />
                        )}
                        <span className="font-medium">{model}</span>
                      </div>
                      {result.response && (
                        <p className="text-sm text-gray-600 mt-1">Response: {result.response}</p>
                      )}
                      {result.error && (
                        <p className="text-sm text-red-600 mt-1">Error: {result.error}</p>
                      )}
                    </div>
                  )
                ))}
              </div>
            )}
          </Card>

          {/* Available Models */}
          <Card title="Download New Models">
            <div className="space-y-6">
              {/* Recommended */}
              <div>
                <h4 className="font-medium text-gray-900 mb-3">Recommended Models</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {availableModels.recommended?.map((model) => (
                    <ModelCard
                      key={model.name}
                      model={model}
                      installed={isModelInstalled(model.name)}
                      pulling={pulling[model.name]}
                      onPull={() => handlePull(model.name)}
                    />
                  ))}
                </div>
              </div>

              {/* Hybrid / MoE (MiniMax M2.5, GLM-5 Qwen 3.5, etc.) */}
              {availableModels.hybrid?.length > 0 && (
                <div>
                  <h4 className="font-medium text-gray-900 mb-3">Hybrid / MoE Models</h4>
                  <p className="text-sm text-gray-500 mb-3">
                    Use as <code className="px-1 py-0.5 bg-gray-100 rounded">OLLAMA_MODEL</code> or <code className="px-1 py-0.5 bg-gray-100 rounded">OLLAMA_FAST_MODEL</code> in backend/.env for script and topic generation.
                  </p>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {availableModels.hybrid.map((model) => (
                      <ModelCard
                        key={model.name}
                        model={model}
                        installed={isModelInstalled(model.name)}
                        pulling={pulling[model.name]}
                        onPull={() => handlePull(model.name)}
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* Large Models */}
              <div>
                <h4 className="font-medium text-gray-900 mb-3">Large Models (Requires High VRAM)</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {availableModels.large?.map((model) => (
                    <ModelCard
                      key={model.name}
                      model={model}
                      installed={isModelInstalled(model.name)}
                      pulling={pulling[model.name]}
                      onPull={() => handlePull(model.name)}
                    />
                  ))}
                </div>
              </div>

              {/* Custom Model */}
              <div className="p-4 bg-gray-50 rounded-lg">
                <h4 className="font-medium text-gray-900 mb-2">Pull Custom Model</h4>
                <p className="text-sm text-gray-500 mb-3">
                  Enter any model name from <a href="https://ollama.ai/library" target="_blank" className="text-primary-600 hover:underline">Ollama Library</a>
                </p>
                <CustomModelPull onPull={handlePull} pulling={pulling} />
              </div>
            </div>
          </Card>

          {/* Delete Confirmation Modal */}
          <Modal
            isOpen={!!showDeleteModal}
            onClose={() => setShowDeleteModal(null)}
            title="Delete Model"
            size="sm"
          >
            <p className="text-gray-600 mb-4">
              Are you sure you want to delete <strong>{showDeleteModal}</strong>?
              This will free up disk space but you'll need to download it again to use it.
            </p>
            <div className="flex justify-end gap-3">
              <Button variant="secondary" onClick={() => setShowDeleteModal(null)}>
                Cancel
              </Button>
              <Button variant="danger" onClick={() => handleDelete(showDeleteModal)}>
                Delete Model
              </Button>
            </div>
          </Modal>
        </>
      )}
    </div>
  )
}

function LTXModelsSection({ ltxModels }) {
  const [installing, setInstalling] = useState(false)
  const [installStatus, setInstallStatus] = useState(null)

  const handleInstall = async () => {
    setInstalling(true)
    try {
      await api.post('/models/ltx/install')
      setInstallStatus({ status: 'started', message: 'Installation started in background...' })

      // Poll for status
      const interval = setInterval(async () => {
        try {
          const res = await api.get('/models/pull/ltx_install/status')
          if (res.data.status === 'completed' || res.data.status === 'failed') {
            clearInterval(interval)
            setInstalling(false)
            setInstallStatus(res.data)
            if (res.data.status === 'completed') {
              window.location.reload()
            }
          } else {
            setInstallStatus(res.data)
          }
        } catch (e) {
          clearInterval(interval)
        }
      }, 2000)

    } catch (error) {
      console.error('Failed to start installation:', error)
      setInstalling(false)
      setInstallStatus({ status: 'failed', message: error.message })
    }
  }

  const categories = {
    main: ltxModels.models?.filter(m => m.category === 'main') || [],
    upscaler: ltxModels.models?.filter(m => m.category === 'upscaler') || [],
    lora: ltxModels.models?.filter(m => m.category === 'lora') || [],
    other: ltxModels.models?.filter(m => m.category === 'other') || []
  }

  if (ltxModels.message && ltxModels.message !== 'LTX provider is not enabled') {
    return (
      <Card title="LTX-2 Models">
        <div className="text-center py-8">
          <p className="text-gray-500 mb-4">{ltxModels.message}</p>
          <Button onClick={handleInstall} loading={installing}>
            <Download className="h-4 w-4" />
            Install LTX Models
          </Button>
          {installStatus && (
            <div className="mt-4 max-w-md mx-auto">
              <div className="flex justify-between text-sm text-gray-600 mb-1">
                <span>{installStatus.message}</span>
                <span>{Math.round(installStatus.progress || 0)}%</span>
              </div>
              <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary-500 transition-all duration-300"
                  style={{ width: `${installStatus.progress || 0}%` }}
                />
              </div>
            </div>
          )}
        </div>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      <Card title={`LTX-2 Models (${ltxModels.total || 0})`}>
        <div className="mb-4 p-4 bg-blue-50 rounded-lg flex justify-between items-start">
          <div>
            <p className="text-sm text-gray-700">
              <strong>Total Size:</strong> {ltxModels.total_size_gb || 0} GB
            </p>
            <p className="text-sm text-gray-600 mt-1">
              <strong>Location:</strong> {ltxModels.model_path || 'Not configured'}
            </p>
          </div>
          <Button size="sm" variant="secondary" onClick={handleInstall} loading={installing}>
            <RefreshCw className="h-4 w-4" />
            Re-run Installer
          </Button>
        </div>

        {installStatus && (installing || installStatus.status === 'pulling') && (
          <div className="mb-6 p-4 bg-gray-50 rounded-lg border">
            <h4 className="font-medium text-sm mb-2">Installation Progress</h4>
            <div className="flex justify-between text-sm text-gray-600 mb-1">
              <span>{installStatus.message}</span>
              <span>{Math.round(installStatus.progress || 0)}%</span>
            </div>
            <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-primary-500 transition-all duration-300"
                style={{ width: `${installStatus.progress || 0}%` }}
              />
            </div>
          </div>
        )}

        {/* Main Models */}
        {categories.main.length > 0 && (
          <div className="mb-6">
            <h4 className="font-medium text-gray-900 mb-3">Main Models</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {categories.main.map((model) => (
                <div key={model.name} className={`p-4 border rounded-lg ${model.recommended ? 'border-primary-300 bg-primary-50' : ''}`}>
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1">
                      <p className="font-medium text-gray-900">{model.name}</p>
                      <p className="text-sm text-gray-500">{model.size}</p>
                    </div>
                    {model.recommended && (
                      <span className="px-2 py-0.5 bg-primary-100 text-primary-700 text-xs rounded-full">
                        Recommended
                      </span>
                    )}
                  </div>
                  {model.description && (
                    <p className="text-sm text-gray-600 mb-2">{model.description}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Upscalers */}
        {categories.upscaler.length > 0 && (
          <div className="mb-6">
            <h4 className="font-medium text-gray-900 mb-3">Upscalers</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {categories.upscaler.map((model) => (
                <div key={model.name} className="p-4 border rounded-lg">
                  <p className="font-medium text-gray-900">{model.name}</p>
                  <p className="text-sm text-gray-500">{model.size}</p>
                  {model.description && (
                    <p className="text-sm text-gray-600 mt-1">{model.description}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* LoRAs */}
        {categories.lora.length > 0 && (
          <div className="mb-6">
            <h4 className="font-medium text-gray-900 mb-3">LoRA Adapters</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {categories.lora.map((model) => (
                <div key={model.name} className="p-4 border rounded-lg">
                  <p className="font-medium text-gray-900">{model.name}</p>
                  <p className="text-sm text-gray-500">{model.size}</p>
                  {model.description && (
                    <p className="text-sm text-gray-600 mt-1">{model.description}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {ltxModels.total === 0 && (
          <div className="text-center py-8">
            <p className="text-gray-500 mb-4">No LTX models found.</p>
            <Button onClick={handleInstall} loading={installing}>
              <Download className="h-4 w-4" />
              Install LTX Models
            </Button>
          </div>
        )}
      </Card>
    </div>
  )
}

function ModelCard({ model, installed, pulling, onPull }) {
  const isPulling = pulling && pulling.status === 'pulling'
  const isCompleted = pulling && pulling.status === 'completed'
  const isFailed = pulling && pulling.status === 'failed'

  return (
    <div className="p-4 border rounded-lg">
      <div className="flex items-start justify-between mb-2">
        <div>
          <p className="font-medium text-gray-900">{model.name}</p>
          <p className="text-sm text-gray-500">{model.size}</p>
        </div>
        {installed && !isPulling && (
          <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs rounded-full flex items-center gap-1">
            <Check className="h-3 w-3" /> Installed
          </span>
        )}
      </div>
      <p className="text-sm text-gray-600 mb-2">{model.description}</p>
      <p className="text-xs text-gray-400 mb-3">Best for: {model.use_case}</p>

      {isPulling ? (
        <div>
          <div className="flex justify-between text-sm text-gray-600 mb-1">
            <span>{pulling.message || 'Downloading...'}</span>
            <span>{(pulling.progress || 0).toFixed(1)}%</span>
          </div>
          <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-primary-500 transition-all duration-300"
              style={{ width: `${pulling.progress || 0}%` }}
            />
          </div>
        </div>
      ) : isFailed ? (
        <div className="flex items-center gap-2 text-red-600 text-sm">
          <AlertCircle className="h-4 w-4" />
          <span>Failed: {pulling.message}</span>
        </div>
      ) : !installed ? (
        <Button size="sm" onClick={onPull} className="w-full">
          <Download className="h-4 w-4" />
          Download
        </Button>
      ) : isCompleted ? (
        <div className="flex items-center gap-2 text-green-600 text-sm">
          <Check className="h-4 w-4" />
          <span>Download complete!</span>
        </div>
      ) : null}
    </div>
  )
}

function CustomModelPull({ onPull, pulling }) {
  const [modelName, setModelName] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    if (modelName.trim()) {
      onPull(modelName.trim())
    }
  }

  const isPulling = pulling[modelName]?.status === 'pulling'

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <input
        type="text"
        value={modelName}
        onChange={(e) => setModelName(e.target.value)}
        placeholder="e.g., codellama:7b"
        className="flex-1 px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
        disabled={isPulling}
      />
      <Button type="submit" disabled={!modelName.trim() || isPulling} loading={isPulling}>
        <Download className="h-4 w-4" />
        Pull
      </Button>
    </form>
  )
}
