import { useState, useEffect } from 'react'
import { Wand2, Play, RefreshCw, Check, Eye } from 'lucide-react'
import Card from '../components/Card'
import Button from '../components/Button'
import VideoPlayer from '../components/VideoPlayer'
import StatusBadge from '../components/StatusBadge'
import { getNiches, generateTopic, generateScript, generateVideo, getGenerationStatus, approveAndPublish } from '../api'

export default function Generator() {
  const [niches, setNiches] = useState([])
  const [selectedNiche, setSelectedNiche] = useState(null)
  const [topic, setTopic] = useState('')
  const [script, setScript] = useState(null)
  const [loading, setLoading] = useState({ niches: true, topic: false, script: false, video: false })
  const [activeJob, setActiveJob] = useState(null)
  const [pollInterval, setPollInterval] = useState(null)

  useEffect(() => {
    loadNiches()
    return () => {
      if (pollInterval) clearInterval(pollInterval)
    }
  }, [])

  const loadNiches = async () => {
    try {
      const res = await getNiches()
      setNiches(res.data)
      if (res.data.length > 0) {
        setSelectedNiche(res.data[0])
      }
    } catch (error) {
      console.error('Failed to load niches:', error)
    } finally {
      setLoading(prev => ({ ...prev, niches: false }))
    }
  }

  const handleGenerateTopic = async () => {
    if (!selectedNiche) return
    setLoading(prev => ({ ...prev, topic: true }))
    try {
      const res = await generateTopic(selectedNiche.id)
      setTopic(res.data.topic)
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
      const res = await generateVideo({ niche_id: selectedNiche.id, topic })
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

  const resetGenerator = () => {
    setTopic('')
    setScript(null)
    setActiveJob(null)
    if (pollInterval) {
      clearInterval(pollInterval)
      setPollInterval(null)
    }
    setLoading({ niches: false, topic: false, script: false, video: false })
  }

  if (loading.niches) {
    return <div className="flex items-center justify-center h-64">Loading...</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Video Generator</h1>
        {activeJob && (
          <Button variant="secondary" onClick={resetGenerator}>
            <RefreshCw className="h-4 w-4" />
            Start Over
          </Button>
        )}
      </div>

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
              <p className="mt-2 text-sm text-gray-500">{selectedNiche.description}</p>
            )}
          </Card>

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
                <Button
                  variant="secondary"
                  onClick={handleGenerateTopic}
                  loading={loading.topic}
                  disabled={activeJob}
                >
                  <Wand2 className="h-4 w-4" />
                </Button>
              </div>
              
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
    </div>
  )
}
