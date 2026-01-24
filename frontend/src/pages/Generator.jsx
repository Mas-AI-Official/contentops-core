import { useState, useEffect } from 'react'
import { Wand2, Play, RefreshCw, Check, Eye, TrendingUp, AlertTriangle, Zap, Settings } from 'lucide-react'
import { Link } from 'react-router-dom'
import Card from '../components/Card'
import Button from '../components/Button'
import VideoPlayer from '../components/VideoPlayer'
import StatusBadge from '../components/StatusBadge'
import { getNiches, generateTopic, generateScript, generateVideo, getGenerationStatus, approveAndPublish, getLTXModels, automateNiche, getJobs } from '../api'

export default function Generator() {
  const [niches, setNiches] = useState([])
  const [selectedNiche, setSelectedNiche] = useState(null)
  const [topic, setTopic] = useState('')
  const [script, setScript] = useState(null)
  const [loading, setLoading] = useState({ niches: true, topic: false, script: false, video: false, autopilot: false })
  const [activeJob, setActiveJob] = useState(null)
  const [pollInterval, setPollInterval] = useState(null)
  const [ltxModels, setLtxModels] = useState([])
  const [selectedVideoModel, setSelectedVideoModel] = useState('')
  const [mode, setMode] = useState('manual') // 'manual' or 'autopilot'
  const [error, setError] = useState(null)

  useEffect(() => {
    loadNiches()
    return () => {
      if (pollInterval) clearInterval(pollInterval)
    }
  }, [])

  useEffect(() => {
    if (selectedNiche) {
      checkActiveJob(selectedNiche.id)
    }
  }, [selectedNiche])

  const checkActiveJob = async (nicheId) => {
    try {
      const res = await getJobs({ niche_id: nicheId, limit: 1 })
      if (res.data && res.data.length > 0) {
        const job = res.data[0]
        if (['pending', 'queued', 'generating_script', 'generating_audio', 'generating_subtitles', 'rendering', 'publishing', 'ready_for_review'].includes(job.status)) {
          setActiveJob({
            job_id: job.id,
            status: job.status,
            progress: job.progress_percent,
            preview_url: job.status === 'ready_for_review' ? `/api/generator/preview/${job.id}` : null,
            error: job.error_message
          })
          if (!pollInterval) {
            startPolling(job.id)
          }
        }
      }
    } catch (e) {
      console.error("Failed to check active job:", e)
    }
  }

  const loadNiches = async () => {
    try {
      setError(null)
      const [nichesRes, modelsRes] = await Promise.all([
        getNiches(),
        getLTXModels().catch(() => ({ data: { models: [] } }))
      ])
      setNiches(nichesRes.data)
      setLtxModels(modelsRes.data?.models || [])

      if (nichesRes.data.length > 0) {
        setSelectedNiche(nichesRes.data[0])
      }

      const recommendedModel = modelsRes.data?.models?.find(m => m.recommended)
      if (recommendedModel) {
        setSelectedVideoModel(recommendedModel.name)
      }
    } catch (error) {
      console.error('Failed to load niches:', error)
      setError('Backend connection failed. Please ensure the backend is running.')
    } finally {
      setLoading(prev => ({ ...prev, niches: false }))
    }
  }

  const [topicData, setTopicData] = useState(null)

  // ...

  const handleGenerateTopic = async (source = 'auto') => {
    if (!selectedNiche) return
    setLoading(prev => ({ ...prev, topic: true }))
    setTopicData(null)
    try {
      const actualSource = typeof source === 'string' ? source : 'auto'
      const res = await generateTopic(selectedNiche.id, actualSource)
      setTopic(res.data.topic)
      if (res.data.data) {
        setTopicData(res.data.data)
      }
    } catch (error) {
      console.error('Failed to generate topic:', error)
    } finally {
      setLoading(prev => ({ ...prev, topic: false }))
    }
  }

  const handleGenerateScript = async () => {
    if (!selectedNiche || !topic) return
    setLoading(prev => ({ ...prev, script: true }))
    try {
      const res = await generateScript({ niche_id: selectedNiche.id, topic })
      setScript(res.data)
    } catch (error) {
      console.error('Failed to generate script:', error)
    } finally {
      setLoading(prev => ({ ...prev, script: false }))
    }
  }

  const handleGenerateVideo = async () => {
    if (!selectedNiche || !topic) return
    setLoading(prev => ({ ...prev, video: true }))
    try {
      const res = await generateVideo({
        niche_id: selectedNiche.id,
        topic,
        video_model: selectedVideoModel || null
      })
      setActiveJob({ id: res.data.job_id, status: 'pending', progress: 0 })
      startPolling(res.data.job_id)
    } catch (error) {
      console.error('Failed to start video generation:', error)
      setLoading(prev => ({ ...prev, video: false }))
    }
  }

  const startPolling = (jobId) => {
    const interval = setInterval(async () => {
      try {
        const res = await getGenerationStatus(jobId)
        setActiveJob(res.data)

        if (['ready_for_review', 'failed', 'published'].includes(res.data.status)) {
          clearInterval(interval)
          setPollInterval(null)
          setLoading(prev => ({ ...prev, video: false }))
        }
      } catch (error) {
        console.error('Failed to poll status:', error)
      }
    }, 2000)
    setPollInterval(interval)
  }

  const handleApprove = async (publish = false) => {
    if (!activeJob) return
    try {
      const platforms = []
      if (selectedNiche.post_to_youtube) platforms.push('youtube')
      if (selectedNiche.post_to_instagram) platforms.push('instagram')
      if (selectedNiche.post_to_tiktok) platforms.push('tiktok')

      await approveAndPublish(activeJob.job_id, platforms)
      alert(publish ? 'Video approved and queued for publishing!' : 'Video approved!')
    } catch (error) {
      console.error('Failed to approve:', error)
    }
  }

  const handleEnableAutopilot = async () => {
    if (!selectedNiche) return
    setLoading(prev => ({ ...prev, autopilot: true }))
    try {
      await automateNiche(selectedNiche.id, { enabled: true })
      alert(`Autopilot enabled for ${selectedNiche.name}! It will now generate and post content automatically.`)
      loadNiches() // Reload to update state
    } catch (error) {
      console.error('Failed to enable autopilot:', error)
      alert('Failed to enable autopilot')
    } finally {
      setLoading(prev => ({ ...prev, autopilot: false }))
    }
  }

  const resetGenerator = () => {
    setTopic('')
    setScript(null)
    setActiveJob(null)
    if (pollInterval) {
      clearInterval(pollInterval)
      setPollInterval(null)
    }
    setLoading({ niches: false, topic: false, script: false, video: false, autopilot: false })
  }

  if (loading.niches) {
    return <div className="flex items-center justify-center h-64">Loading...</div>
  }

  if (error) {
    return (
      <div className="p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3 text-red-700">
        <AlertTriangle className="h-5 w-5" />
        <p>{error}</p>
        <Button size="sm" variant="secondary" onClick={loadNiches}>Retry</Button>
      </div>
    )
  }

  if (niches.length === 0) {
    return (
      <div className="text-center py-12">
        <Wand2 className="h-12 w-12 text-gray-300 mx-auto mb-4" />
        <h2 className="text-xl font-semibold text-gray-900 mb-2">No Niches Found</h2>
        <p className="text-gray-500 mb-6">Create your first niche to start generating content.</p>
        <Link to="/niches">
          <Button>Create Niche</Button>
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Video Generator</h1>
        <div className="flex items-center gap-4">
          <div className="bg-gray-100 p-1 rounded-lg flex">
            <button
              onClick={() => setMode('manual')}
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-all ${mode === 'manual' ? 'bg-white shadow text-gray-900' : 'text-gray-500 hover:text-gray-700'
                }`}
            >
              Manual Mode
            </button>
            <button
              onClick={() => setMode('autopilot')}
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-all ${mode === 'autopilot' ? 'bg-white shadow text-primary-600' : 'text-gray-500 hover:text-gray-700'
                }`}
            >
              Autopilot Mode
            </button>
          </div>
          {activeJob && mode === 'manual' && (
            <Button variant="secondary" onClick={resetGenerator}>
              <RefreshCw className="h-4 w-4" />
              Start Over
            </Button>
          )}
        </div>
      </div>

      {mode === 'autopilot' ? (
        <Card>
          <div className="text-center py-12">
            <Zap className="h-16 w-16 text-yellow-500 mx-auto mb-4" />
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Autopilot Mode</h2>
            <p className="text-gray-500 max-w-md mx-auto mb-8">
              Autopilot automatically generates, renders, and publishes videos for your niches based on their schedule.
            </p>

            <div className="max-w-md mx-auto bg-gray-50 rounded-xl p-6 mb-8 text-left">
              <h3 className="font-semibold mb-4">Select Niche to Configure</h3>
              <select
                value={selectedNiche?.id || ''}
                onChange={(e) => {
                  const niche = niches.find(n => n.id === parseInt(e.target.value))
                  setSelectedNiche(niche)
                }}
                className="w-full px-3 py-2 border rounded-lg mb-4"
              >
                {niches.map(niche => (
                  <option key={niche.id} value={niche.id}>{niche.name}</option>
                ))}
              </select>

              {selectedNiche && (
                <div className="space-y-4">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Status</span>
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${selectedNiche.auto_mode ? 'bg-green-100 text-green-700' : 'bg-gray-200 text-gray-700'
                      }`}>
                      {selectedNiche.auto_mode ? 'Active' : 'Inactive'}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Schedule</span>
                    <span className="font-medium">{selectedNiche.posting_schedule?.join(', ') || 'None'}</span>
                  </div>

                  {!selectedNiche.auto_mode ? (
                    <Button onClick={handleEnableAutopilot} loading={loading.autopilot} className="w-full">
                      <Zap className="h-4 w-4 mr-2" />
                      Enable Autopilot
                    </Button>
                  ) : (
                    <div className="text-center text-sm text-green-600 font-medium flex items-center justify-center gap-2">
                      <Check className="h-4 w-4" />
                      Autopilot is running
                    </div>
                  )}

                  <Link to={`/niches/${selectedNiche.id}`} className="block">
                    <Button variant="secondary" className="w-full">
                      <Settings className="h-4 w-4 mr-2" />
                      Configure Settings
                    </Button>
                  </Link>
                </div>
              )}
            </div>
          </div>
        </Card>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left: Controls */}
          <div className="space-y-6">
            {/* Niche Selection */}
            <Card title="1. Select Niche">
              <select
                value={selectedNiche?.id || ''}
                onChange={(e) => {
                  const niche = niches.find(n => n.id === parseInt(e.target.value))
                  setSelectedNiche(niche)
                }}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                disabled={activeJob}
              >
                {niches.map(niche => (
                  <option key={niche.id} value={niche.id}>{niche.name}</option>
                ))}
              </select>
              {selectedNiche && (
                <div className="mt-3 space-y-2">
                  <p className="text-sm text-gray-500">{selectedNiche.description}</p>
                  <div className="flex flex-wrap gap-2 text-xs">
                    <span className="px-2 py-1 bg-gray-100 rounded text-gray-600">
                      Platform: {selectedNiche.platform}
                    </span>
                    {selectedNiche.account_name && (
                      <span className="px-2 py-1 bg-blue-50 text-blue-700 rounded">
                        Account: {selectedNiche.account_name}
                      </span>
                    )}
                    <span className="px-2 py-1 bg-purple-50 text-purple-700 rounded">
                      Style: {selectedNiche.style}
                    </span>
                  </div>
                </div>
              )}
            </Card>

            {/* Workflow Pipeline Visualizer */}
            {selectedNiche && (
              <div className="bg-white p-4 rounded-xl border shadow-sm overflow-x-auto">
                <h3 className="text-sm font-medium text-gray-900 mb-4">Pipeline Workflow</h3>
                <div className="flex items-center min-w-max gap-2">
                  {[
                    { label: 'Scrape', icon: '🔍', status: 'ready' },
                    { label: 'Topic', icon: '💡', status: topic ? 'done' : 'waiting' },
                    { label: 'Script', icon: '📝', status: script ? 'done' : 'waiting' },
                    { label: 'TTS', icon: '🗣️', status: script ? 'ready' : 'waiting' },
                    { label: 'Video', icon: '🎬', status: activeJob ? 'processing' : 'waiting' },
                    { label: 'Publish', icon: '🚀', status: 'waiting' }
                  ].map((step, i, arr) => (
                    <div key={step.label} className="flex items-center">
                      <div className={`
                        flex flex-col items-center gap-2 p-3 rounded-lg border w-24
                        ${step.status === 'done' ? 'bg-green-50 border-green-200' :
                          step.status === 'processing' ? 'bg-blue-50 border-blue-200 animate-pulse' :
                            step.status === 'ready' ? 'bg-gray-50 border-gray-200' : 'opacity-50'}
                      `}>
                        <span className="text-xl">{step.icon}</span>
                        <span className="text-xs font-medium">{step.label}</span>
                      </div>
                      {i < arr.length - 1 && (
                        <div className="w-8 h-0.5 bg-gray-200 mx-1" />
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Topic */}
            <Card title="2. Topic">
              <div className="space-y-3">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                    placeholder="Enter a topic or generate one..."
                    className="flex-1 px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                    disabled={activeJob}
                  />
                  <div className="flex gap-1">
                    <Button
                      variant="secondary"
                      onClick={() => handleGenerateTopic('auto')}
                      loading={loading.topic}
                      disabled={activeJob}
                      title="Auto-generate (Smart Mix)"
                    >
                      <Wand2 className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="secondary"
                      onClick={() => handleGenerateTopic('rss')}
                      loading={loading.topic}
                      disabled={activeJob}
                      title="From RSS Feeds"
                    >
                      <span className="text-xs font-bold">RSS</span>
                    </Button>
                    <Button
                      variant="secondary"
                      onClick={() => handleGenerateTopic('trending')}
                      loading={loading.topic}
                      disabled={activeJob}
                      title="From Google Trends"
                    >
                      <TrendingUp className="h-4 w-4" />
                    </Button>
                  </div>
                </div>

                {topicData && (
                  <div className="text-xs flex items-center gap-2 px-1">
                    <span className="font-medium text-green-600 bg-green-50 px-2 py-0.5 rounded">
                      Score: {topicData.score || 'N/A'}
                    </span>
                    {topicData.source && (
                      <span className="text-gray-500 truncate max-w-xs" title={topicData.source}>
                        Source: {topicData.source.startsWith('http') ? new URL(topicData.source).hostname.replace('www.', '') : topicData.source}
                      </span>
                    )}
                  </div>
                )}

                {!script && topic && (
                  <Button onClick={handleGenerateScript} loading={loading.script} disabled={activeJob}>
                    Generate Script Preview
                  </Button>
                )}
              </div>
            </Card>

            {/* Script Preview */}
            {script && (
              <Card title="3. Script Preview">
                <div className="space-y-4">
                  <div>
                    <h4 className="text-sm font-medium text-gray-500 mb-1">Hook</h4>
                    <p className="text-sm text-gray-900 bg-gray-50 p-3 rounded-lg">{script.hook}</p>
                  </div>
                  <div>
                    <h4 className="text-sm font-medium text-gray-500 mb-1">Body</h4>
                    <p className="text-sm text-gray-900 bg-gray-50 p-3 rounded-lg whitespace-pre-wrap">{script.body}</p>
                  </div>
                  <div>
                    <h4 className="text-sm font-medium text-gray-500 mb-1">Call to Action</h4>
                    <p className="text-sm text-gray-900 bg-gray-50 p-3 rounded-lg">{script.cta}</p>
                  </div>
                  <div className="flex items-center justify-between text-sm text-gray-500">
                    <span>Estimated duration: ~{script.estimated_duration}s</span>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={handleGenerateScript}
                      loading={loading.script}
                      disabled={activeJob}
                    >
                      <RefreshCw className="h-4 w-4" />
                      Regenerate
                    </Button>
                  </div>
                </div>
              </Card>
            )}

            {/* Video Model Selection */}
            {script && !activeJob && ltxModels.length > 0 && (
              <Card title="4. Video Model (Optional)">
                <div className="space-y-3">
                  <select
                    value={selectedVideoModel}
                    onChange={(e) => setSelectedVideoModel(e.target.value)}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  >
                    <option value="">Use Default (Recommended)</option>
                    {ltxModels.map(model => (
                      <option key={model.name} value={model.name}>
                        {model.name} - {model.description} ({model.size})
                        {model.recommended && ' ⭐'}
                      </option>
                    ))}
                  </select>
                  <p className="text-xs text-gray-500">
                    Select an LTX-2 model for video generation. Leave blank to use the recommended model.
                  </p>
                </div>
              </Card>
            )}

            {/* Generate Video */}
            {script && !activeJob && (
              <Button onClick={handleGenerateVideo} loading={loading.video} className="w-full">
                <Play className="h-4 w-4" />
                Generate Full Video
              </Button>
            )}
          </div>

          {/* Right: Preview & Status */}
          <div className="space-y-6">
            {activeJob && (
              <Card title="Generation Status">
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-gray-600">Status</span>
                    <StatusBadge status={activeJob.status} />
                  </div>

                  {activeJob.progress !== undefined && activeJob.status !== 'ready_for_review' && (
                    <div>
                      <div className="flex justify-between text-sm text-gray-600 mb-1">
                        <span>Progress</span>
                        <span>{activeJob.progress}%</span>
                      </div>
                      <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-primary-500 transition-all duration-500"
                          style={{ width: `${activeJob.progress}%` }}
                        />
                      </div>
                    </div>
                  )}

                  {activeJob.error && (
                    <div className="p-3 bg-red-50 rounded-lg">
                      <p className="text-sm text-red-700">{activeJob.error}</p>
                    </div>
                  )}
                </div>
              </Card>
            )}

            {/* Video Preview */}
            {activeJob?.status === 'ready_for_review' && activeJob.preview_url && (
              <Card title="Video Preview">
                <VideoPlayer
                  src={activeJob.preview_url}
                  className="w-full max-w-xs mx-auto"
                />

                <div className="mt-4 space-y-2">
                  <Button onClick={() => handleApprove(true)} className="w-full">
                    <Check className="h-4 w-4" />
                    Approve & Publish
                  </Button>
                  <Button variant="secondary" onClick={() => handleApprove(false)} className="w-full">
                    <Eye className="h-4 w-4" />
                    Approve Only (No Publish)
                  </Button>
                </div>
              </Card>
            )}

            {!activeJob && (
              <Card>
                <div className="text-center py-12">
                  <Wand2 className="h-12 w-12 text-gray-300 mx-auto mb-4" />
                  <p className="text-gray-500">
                    Select a niche and topic, then generate a video preview.
                  </p>
                </div>
              </Card>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
