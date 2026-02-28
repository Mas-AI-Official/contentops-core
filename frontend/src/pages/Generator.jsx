import { useState, useEffect } from 'react'
import { Wand2, Play, RefreshCw, Check, Eye, TrendingUp, AlertTriangle, Zap, Settings } from 'lucide-react'
import { Link } from 'react-router-dom'
import Card from '../components/Card'
import Button from '../components/Button'
import VideoPlayer from '../components/VideoPlayer'
import StatusBadge from '../components/StatusBadge'
import { getNiches, generateTopic, generateScript, generateVideo, getGenerationStatus, approveAndPublish, getLTXModels, getVoices, automateNiche, getJobs } from '../api'

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
  // Platform format (aspect ratio) for LTX
  const [platformFormat, setPlatformFormat] = useState('9:16') // '9:16' | '16:9' | '1:1'
  // Character reference for consistent face/scene
  const [characterDescription, setCharacterDescription] = useState('')
  const [startFrameFile, setStartFrameFile] = useState(null)   // File for Start Frame / Character Reference
  const [endFrameFile, setEndFrameFile] = useState(null)      // File for End Frame
  // Manual prompt: use as topic (LLM expands to script) or as full script (no LLM)
  const [manualPrompt, setManualPrompt] = useState('')
  const [usePromptAsFullScript, setUsePromptAsFullScript] = useState(false)
  const [videoName, setVideoName] = useState('')  // Display name/title for the video (manual mode)
  const [scenesInput, setScenesInput] = useState('')  // One scene per line; blank = auto from script/LLM
  const [voices, setVoices] = useState([])  // { voice_id, name, provider }; empty selection = niche default
  const [selectedVoiceId, setSelectedVoiceId] = useState('')  // '' = use niche/account default
  const [batchCount, setBatchCount] = useState(1)  // 1, 2, or 3 videos per Generate click
  const [lastQueuedCount, setLastQueuedCount] = useState(0)  // Show "N queued" after generate; 0 = hide
  const [targetDuration, setTargetDuration] = useState(60)  // 20, 30, 60, 90, 120 sec or custom
  const [customDuration, setCustomDuration] = useState('')  // custom seconds when targetDuration === 'custom'

  useEffect(() => {
    loadNiches()
    return () => {
      if (pollInterval) clearInterval(pollInterval)
    }
  }, [])

  // Prefill from Prompt Lab or Scrape (localStorage)
  useEffect(() => {
    const fromPromptLab = localStorage.getItem('promptlab_script')
    if (fromPromptLab) {
      setManualPrompt(fromPromptLab)
      setUsePromptAsFullScript(true)
      localStorage.removeItem('promptlab_script')
    }
    const pickedTopic = localStorage.getItem('picked_topic')
    if (pickedTopic) {
      try {
        const { title, niche_id } = JSON.parse(pickedTopic)
        if (title) setTopic(title)
        if (niche_id && niches.length) {
          const niche = niches.find(n => n.id === niche_id)
          if (niche) setSelectedNiche(niche)
        }
        localStorage.removeItem('picked_topic')
      } catch (_) {}
    }
  }, [niches.length])

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
      const [nichesRes, modelsRes, voicesRes] = await Promise.all([
        getNiches(),
        getLTXModels().catch(() => ({ data: { models: [] } })),
        getVoices().catch(() => ({ data: [] }))
      ])
      setNiches(nichesRes.data)
      setLtxModels(modelsRes.data?.models || [])
      setVoices(Array.isArray(voicesRes.data) ? voicesRes.data : [])

      if (nichesRes.data.length > 0) {
        setSelectedNiche(nichesRes.data[0])
      }

      const recommendedModel = modelsRes.data?.models?.find(m => m.recommended)
      if (recommendedModel) {
        setSelectedVideoModel(recommendedModel.name)
      }
    } catch (error) {
      console.error('Failed to load niches:', error)
      setError('Backend connection failed. Start the backend (e.g. run launch.bat or: cd backend && python -m app.main). It runs on port 8100 by default.')
    } finally {
      setLoading(prev => ({ ...prev, niches: false }))
    }
  }

  const [topicData, setTopicData] = useState(null)

  // When manual prompt is set and not "use as full script", it becomes the topic for LLM script generation
  const effectiveTopic = (manualPrompt && manualPrompt.trim()) ? manualPrompt.trim() : topic

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
    if (!selectedNiche || !effectiveTopic) return
    setLoading(prev => ({ ...prev, script: true }))
    try {
      const res = await generateScript({
        niche_id: selectedNiche.id,
        topic: effectiveTopic,
        character_description: characterDescription || undefined,
      })
      setScript(res.data)
      if (res.data.visual_cues) {
        if (Array.isArray(res.data.visual_cues)) {
          setScenesInput(res.data.visual_cues.join('\n'))
        } else if (typeof res.data.visual_cues === 'string') {
          try {
            const arr = JSON.parse(res.data.visual_cues)
            setScenesInput(Array.isArray(arr) ? arr.join('\n') : '')
          } catch {
            setScenesInput('')
          }
        }
      }
    } catch (error) {
      console.error('Failed to generate script:', error)
    } finally {
      setLoading(prev => ({ ...prev, script: false }))
    }
  }

  const handleGenerateVideo = async () => {
    const canUseTopic = selectedNiche && effectiveTopic
    const canUseFullScript = selectedNiche && usePromptAsFullScript && manualPrompt && manualPrompt.trim()
    if (!canUseTopic && !canUseFullScript) return
    setLoading(prev => ({ ...prev, video: true }))
    try {
      const sceneLines = scenesInput.trim() ? scenesInput.trim().split(/\n/).map(s => s.trim()).filter(Boolean) : []
      const voice = selectedVoiceId ? voices.find(v => v.voice_id === selectedVoiceId) : null
      // Use exact script: preview if user generated one, else whatever they typed in "Your idea or script"
      const effectiveScript = script?.full_script || (manualPrompt?.trim() || null)
      const payload = {
        niche_id: selectedNiche.id,
        topic: effectiveTopic || 'Manual script',
        video_model: selectedVideoModel || null,
        platform_format: platformFormat,
        character_description: characterDescription || null,
        ...(videoName && videoName.trim() && { video_name: videoName.trim() }),
        ...(effectiveScript && { custom_script: effectiveScript }),
        ...(sceneLines.length > 0 && { scenes: sceneLines }),
        ...(selectedVoiceId && { voice_id: selectedVoiceId, ...(voice?.name && { voice_name: voice.name }) }),
        count: batchCount,
        target_duration_seconds: targetDuration === 'custom' ? (parseInt(customDuration, 10) || 60) : (typeof targetDuration === 'number' ? targetDuration : 60),
      }
      if (startFrameFile) {
        const base64 = await fileToBase64(startFrameFile)
        payload.start_frame_base64 = base64
        payload.start_frame_filename = startFrameFile.name
      }
      if (endFrameFile) {
        const base64 = await fileToBase64(endFrameFile)
        payload.end_frame_base64 = base64
        payload.end_frame_filename = endFrameFile.name
      }
      const res = await generateVideo(payload)
      const jobIds = res.data.job_ids || [res.data.job_id]
      const count = jobIds.length
      setLastQueuedCount(count)
      setLoading(prev => ({ ...prev, video: false }))
      // Do not set activeJob – job goes to Queue; form stays so user can generate another
    } catch (error) {
      console.error('Failed to start video generation:', error)
      setLoading(prev => ({ ...prev, video: false }))
    }
  }

  const fileToBase64 = (file) =>
    new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.readAsDataURL(file)
      reader.onload = () => {
        const dataUrl = reader.result
        const base64 = dataUrl.indexOf(',') >= 0 ? dataUrl.split(',')[1] : dataUrl
        resolve(base64)
      }
      reader.onerror = reject
    })

  const startPolling = (jobId) => {
    const interval = setInterval(async () => {
      try {
        const res = await getGenerationStatus(jobId)
        setActiveJob(prev => ({ ...res.data, count: prev?.count ?? res.data?.count }))

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
    setStartFrameFile(null)
    setEndFrameFile(null)
    setManualPrompt('')
    setUsePromptAsFullScript(false)
    setVideoName('')
    setScenesInput('')
    setSelectedVoiceId('')
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
          {mode === 'manual' && (
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
        <div className="max-w-6xl mx-auto space-y-6">
            {/* Top row: Format + Video Model + Voice + Duration – full width */}
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
              <Card title="Platform Format">
                <p className="text-sm text-gray-500 mb-2">Aspect ratio (LTX uses 32 multiples).</p>
                <select
                  value={platformFormat}
                  onChange={(e) => setPlatformFormat(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  disabled={activeJob}
                >
                  <option value="9:16">TikTok / Shorts (9:16)</option>
                  <option value="16:9">YouTube (16:9)</option>
                  <option value="1:1">Instagram (1:1)</option>
                </select>
              </Card>
              <Card title="Video Model">
                <p className="text-sm text-gray-500 mb-2">Auto or choose LTX model.</p>
                <select
                  value={selectedVideoModel}
                  onChange={(e) => setSelectedVideoModel(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  disabled={activeJob}
                >
                  <option value="">Auto (recommended)</option>
                  {ltxModels.map(model => (
                    <option key={model.name} value={model.name}>
                      {model.name}{model.recommended ? ' ⭐' : ''}
                    </option>
                  ))}
                </select>
              </Card>
              <Card title="Voice">
                <p className="text-sm text-gray-500 mb-2">TTS voice (niche default or choose).</p>
                <select
                  value={selectedVoiceId}
                  onChange={(e) => setSelectedVoiceId(e.target.value)}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  disabled={activeJob}
                >
                  <option value="">Niche / account default</option>
                  {voices.map(v => (
                    <option key={v.voice_id} value={v.voice_id}>
                      {v.name} ({v.provider})
                    </option>
                  ))}
                </select>
                {selectedNiche?.voice_name && (
                  <p className="text-xs text-gray-500 mt-1">Niche default: {selectedNiche.voice_name || 'global'}</p>
                )}
              </Card>
              <Card title="Video length">
                <p className="text-sm text-gray-500 mb-2">Target duration (seconds).</p>
                <div className="flex flex-wrap gap-2 mb-2">
                  {[20, 30, 60, 90, 120].map((sec) => (
                    <button
                      key={sec}
                      type="button"
                      onClick={() => setTargetDuration(sec)}
                      className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${targetDuration === sec ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}
                    >
                      {sec}s
                    </button>
                  ))}
                  <button
                    type="button"
                    onClick={() => setTargetDuration('custom')}
                    className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${targetDuration === 'custom' ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}
                  >
                    Custom
                  </button>
                </div>
                {targetDuration === 'custom' && (
                  <div className="flex items-center gap-2">
                    <input
                      type="number"
                      min={15}
                      max={600}
                      value={customDuration}
                      onChange={(e) => setCustomDuration(e.target.value)}
                      placeholder="e.g. 45"
                      className="w-24 px-2 py-1.5 border rounded-lg text-sm"
                    />
                    <span className="text-xs text-gray-500">seconds</span>
                  </div>
                )}
              </Card>
            </div>

            {/* Cards in 2 columns on xl to use space better */}
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
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
                    { label: 'Topic', icon: '💡', status: effectiveTopic ? 'done' : 'waiting' },
                    { label: 'Script', icon: '📝', status: script ? 'done' : 'waiting' },
                    { label: 'Scenes', icon: '🎞️', status: script || scenesInput.trim() ? 'done' : 'waiting' },
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

            {/* Manual prompt: name + idea → script → video */}
            <Card title="2. Manual – Name & prompt">
              <div className="space-y-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Video name</label>
                  <input
                    type="text"
                    value={videoName}
                    onChange={(e) => setVideoName(e.target.value)}
                    placeholder="e.g. 5 AI tools that save you money"
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                    disabled={activeJob}
                  />
                  <p className="text-xs text-gray-500 mt-1">Title for the video (job and library).</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Your idea or script</label>
                  <textarea
                    value={manualPrompt}
                    onChange={(e) => setManualPrompt(e.target.value)}
                    placeholder="Describe your video idea (LLM will turn it into a script). Or check below to use this text as the full narration."
                    rows={4}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 resize-y"
                    disabled={activeJob}
                  />
                </div>
                <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={usePromptAsFullScript}
                    onChange={(e) => setUsePromptAsFullScript(e.target.checked)}
                    disabled={activeJob}
                    className="rounded border-gray-300"
                  />
                  Use as full script (no LLM expansion — this text goes straight to TTS and video)
                </label>
              </div>
            </Card>

            {/* Scenes: optional order; leave blank for auto from script/LLM */}
            <Card title="4. Scenes (order or leave blank for auto)">
              <div className="space-y-2">
                <textarea
                  value={scenesInput}
                  onChange={(e) => setScenesInput(e.target.value)}
                  placeholder={'One scene per line, in order. E.g.\nOpening shot of host at desk\nCut to screen showing the first tip\nLeave blank to auto-generate from script.'}
                  rows={4}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 resize-y text-sm"
                  disabled={activeJob}
                />
                <p className="text-xs text-gray-500">
                  Give the scene order here, or leave empty and scenes will be created automatically from the script.
                </p>
              </div>
            </Card>

            {/* Topic: one-line or from buttons; optional if manual prompt is set */}
            <Card title="3. Topic (or use manual prompt above)">
              <div className="space-y-3">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                    placeholder="One-line topic, or leave blank when using manual prompt..."
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

                {!script && effectiveTopic && (
                  <Button onClick={handleGenerateScript} loading={loading.script} disabled={activeJob}>
                    Generate Script Preview
                  </Button>
                )}
              </div>
            </Card>

            {/* Manual Script Mode: Character reference and start/end frames */}
            <Card title="Manual Script Mode – Character & Frames">
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Character Name / Description</label>
                  <input
                    type="text"
                    value={characterDescription}
                    onChange={(e) => setCharacterDescription(e.target.value)}
                    placeholder="e.g. Daena, a futuristic AI agent with silver hair and a glowing green eDNA jacket"
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-sm"
                    disabled={activeJob}
                  />
                  <p className="text-xs text-gray-500 mt-1">Anchors the character in the scene so LTX keeps them as the focal point.</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Start Frame / Character Reference</label>
                  <div className="border-2 border-dashed border-gray-200 rounded-lg p-4 text-center">
                    <input
                      type="file"
                      accept="image/*"
                      onChange={(e) => setStartFrameFile(e.target.files?.[0] || null)}
                      className="hidden"
                      id="start-frame-upload"
                      disabled={activeJob}
                    />
                    <label htmlFor="start-frame-upload" className="cursor-pointer text-sm text-gray-600 hover:text-primary-600">
                      {startFrameFile ? startFrameFile.name : 'Upload image (first frame / character reference)'}
                    </label>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">Use a high-quality image of your character; LTX will use it as the first frame and animate from it.</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">End Frame</label>
                  <div className="border-2 border-dashed border-gray-200 rounded-lg p-4 text-center">
                    <input
                      type="file"
                      accept="image/*"
                      onChange={(e) => setEndFrameFile(e.target.files?.[0] || null)}
                      className="hidden"
                      id="end-frame-upload"
                      disabled={activeJob}
                    />
                    <label htmlFor="end-frame-upload" className="cursor-pointer text-sm text-gray-600 hover:text-primary-600">
                      {endFrameFile ? endFrameFile.name : 'Upload image (optional end frame)'}
                    </label>
                  </div>
                </div>
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

            {/* Generate Video: always visible in manual mode; button disabled until niche + topic or prompt */}
            <Card title="Generate video">
              <div className="space-y-3">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm text-gray-600">Generate:</span>
                  {[1, 2, 3].map((n) => (
                    <button
                      key={n}
                      type="button"
                      onClick={() => setBatchCount(n)}
                      className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${batchCount === n ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}
                    >
                      {n}
                    </button>
                  ))}
                  <span className="text-sm text-gray-500">{batchCount === 1 ? 'video' : 'videos'}</span>
                </div>
                <Button
                  onClick={handleGenerateVideo}
                  loading={loading.video}
                  disabled={!selectedNiche || (!effectiveTopic && !(manualPrompt && manualPrompt.trim()))}
                  className="w-full"
                >
                  <Play className="h-4 w-4" />
                  {batchCount > 1 ? `Generate ${batchCount} Videos` : (usePromptAsFullScript && manualPrompt?.trim() ? 'Generate Video from Manual Script' : 'Generate Video')}
                </Button>
                {lastQueuedCount > 0 && (
                  <p className="text-sm text-green-600 flex items-center gap-2">
                    <Check className="h-4 w-4" />
                    {lastQueuedCount} video{lastQueuedCount !== 1 ? 's' : ''} queued. <Link to="/queue" className="underline font-medium">View Queue</Link> to preview and approve.
                  </p>
                )}
              </div>
            </Card>
            </div>
        </div>
      )}
    </div>
  )
}
