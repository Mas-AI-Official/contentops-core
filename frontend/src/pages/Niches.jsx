import { useState, useEffect } from 'react'
import { Plus, Edit, Trash2, Lightbulb, Settings2, Clock } from 'lucide-react'
import Card from '../components/Card'
import Button from '../components/Button'
import Modal from '../components/Modal'
import { getNiches, createNiche, updateNiche, deleteNiche, generateTopics, getModels, automateNiche, smartScheduleNiche, getAccounts } from '../api'

const VIDEO_STYLES = [
  { value: 'narrator_broll', label: 'Narrator + B-Roll' },
  { value: 'stick_caption', label: 'Stick Figure + Captions' },
  { value: 'two_voice', label: 'Two Voice Dialogue' },
  { value: 'faceless', label: 'Faceless (Text on Screen)' },
  { value: 'slideshow', label: 'Image Slideshow' },
]

const TTS_PROVIDERS = [
  { value: '', label: 'Use Global Default' },
  { value: 'xtts', label: 'XTTS (Local)' },
  { value: 'elevenlabs', label: 'ElevenLabs' },
]

const WHISPER_MODELS = [
  { value: '', label: 'Use Global Default' },
  { value: 'tiny', label: 'Tiny (fastest)' },
  { value: 'base', label: 'Base' },
  { value: 'small', label: 'Small' },
  { value: 'medium', label: 'Medium' },
  { value: 'large', label: 'Large (best quality)' },
]

const WHISPER_DEVICES = [
  { value: '', label: 'Use Global Default' },
  { value: 'cuda', label: 'GPU (CUDA)' },
  { value: 'cpu', label: 'CPU' },
]

export default function Niches() {
  const [niches, setNiches] = useState([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [editingNiche, setEditingNiche] = useState(null)
  const [topicSuggestions, setTopicSuggestions] = useState({})
  const [generatingTopics, setGeneratingTopics] = useState(null)
  const [installedModels, setInstalledModels] = useState([])
  const [accounts, setAccounts] = useState([])
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [automating, setAutomating] = useState(null)

  const [form, setForm] = useState({
    name: '',
    description: '',
    style: 'narrator_broll',
    posts_per_day: 1,
    auto_mode: false,
    post_to_youtube: true,
    post_to_instagram: true,
    post_to_tiktok: true,
    youtube_account_id: '',
    instagram_account_id: '',
    tiktok_account_id: '',
    prompt_hook: 'Generate an attention-grabbing hook for a video about {topic}.',
    prompt_body: 'Write the main content script for a 60-second video about {topic}.',
    prompt_cta: 'Write a compelling call-to-action for the end of the video.',
    hashtags: '',
    min_duration_seconds: 30,
    max_duration_seconds: 60,
    // Per-niche AI settings
    llm_model: '',
    llm_temperature: 0.7,
    tts_provider: '',
    voice_id: '',
    voice_name: '',
    whisper_model: '',
    whisper_device: '',
    style_preset: '',
  })

  useEffect(() => {
    loadNiches()
    loadModels()
    loadAccounts()
  }, [])

  const loadNiches = async () => {
    try {
      const res = await getNiches()
      setNiches(res.data)
    } catch (error) {
      console.error('Failed to load niches:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadModels = async () => {
    try {
      const res = await getModels()
      setInstalledModels(res.data || [])
    } catch (error) {
      console.error('Failed to load models:', error)
    }
  }

  const loadAccounts = async () => {
    try {
      const res = await getAccounts()
      setAccounts(res.data || [])
    } catch (error) {
      console.error('Failed to load accounts:', error)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    try {
      const data = {
        ...form,
        hashtags: form.hashtags.split(',').map(t => t.trim()).filter(Boolean),
        // Convert empty strings to null for optional fields
        llm_model: form.llm_model || null,
        tts_provider: form.tts_provider || null,
        voice_id: form.voice_id || null,
        voice_name: form.voice_name || null,
        whisper_model: form.whisper_model || null,
        whisper_device: form.whisper_device || null,
        style_preset: form.style_preset || null,
        youtube_account_id: form.youtube_account_id ? parseInt(form.youtube_account_id) : null,
        instagram_account_id: form.instagram_account_id ? parseInt(form.instagram_account_id) : null,
        tiktok_account_id: form.tiktok_account_id ? parseInt(form.tiktok_account_id) : null,
      }

      if (editingNiche) {
        await updateNiche(editingNiche.id, data)
      } else {
        await createNiche(data)
      }

      setShowModal(false)
      setEditingNiche(null)
      resetForm()
      loadNiches()
    } catch (error) {
      console.error('Failed to save niche:', error)
    }
  }

  const handleEdit = (niche) => {
    setEditingNiche(niche)
    setForm({
      name: niche.name,
      description: niche.description || '',
      style: niche.style,
      posts_per_day: niche.posts_per_day,
      auto_mode: niche.auto_mode || false,
      post_to_youtube: niche.post_to_youtube,
      post_to_instagram: niche.post_to_instagram,
      post_to_tiktok: niche.post_to_tiktok,
      youtube_account_id: niche.youtube_account_id || '',
      instagram_account_id: niche.instagram_account_id || '',
      tiktok_account_id: niche.tiktok_account_id || '',
      prompt_hook: niche.prompt_hook,
      prompt_body: niche.prompt_body,
      prompt_cta: niche.prompt_cta,
      hashtags: (niche.hashtags || []).join(', '),
      min_duration_seconds: niche.min_duration_seconds,
      max_duration_seconds: niche.max_duration_seconds,
      llm_model: niche.llm_model || '',
      llm_temperature: niche.llm_temperature || 0.7,
      tts_provider: niche.tts_provider || '',
      voice_id: niche.voice_id || '',
      voice_name: niche.voice_name || '',
      whisper_model: niche.whisper_model || '',
      whisper_device: niche.whisper_device || '',
      style_preset: niche.style_preset || '',
    })
    setShowAdvanced(Boolean(niche.llm_model || niche.tts_provider || niche.whisper_model))
    setShowModal(true)
  }

  const handleDelete = async (id) => {
    if (!confirm('Are you sure you want to delete this niche?')) return
    try {
      await deleteNiche(id)
      loadNiches()
    } catch (error) {
      console.error('Failed to delete niche:', error)
    }
  }

  const handleGenerateTopics = async (nicheId) => {
    setGeneratingTopics(nicheId)
    try {
      const res = await generateTopics(nicheId, 5)
      setTopicSuggestions(prev => ({
        ...prev,
        [nicheId]: res.data.topics
      }))
    } catch (error) {
      console.error('Failed to generate topics:', error)
    } finally {
      setGeneratingTopics(null)
    }
  }

  const handleAutomateNiche = async (nicheId, videoCount = 1) => {
    setAutomating(nicheId)
    try {
      const res = await automateNiche(nicheId, {
        video_count: videoCount,
        publish: false // Don't auto-publish for now
      })
      alert(`✅ Automation started! Created ${res.data.jobs.length} jobs for "${niches.find(n => n.id === nicheId)?.name}"`)
      // Refresh data to show new jobs
      loadData()
    } catch (error) {
      console.error('Failed to automate niche:', error)
      alert('Failed to start automation. Check console for details.')
    } finally {
      setAutomating(null)
    }
  }

  const handleSmartSchedule = async (nicheId) => {
    const niche = niches.find(n => n.id === nicheId)
    if (!niche) return

    // Get platforms enabled for this niche
    const platforms = []
    if (niche.post_to_youtube) platforms.push('youtube')
    if (niche.post_to_instagram) platforms.push('instagram')
    if (niche.post_to_tiktok) platforms.push('tiktok')

    if (platforms.length === 0) {
      alert('No platforms enabled for this niche. Enable posting platforms first.')
      return
    }

    setAutomating(nicheId)
    try {
      const res = await smartScheduleNiche(nicheId, platforms)
      alert(`✅ Smart scheduling complete! Scheduled ${res.data.jobs_created} posts for "${niche.name}" at optimal times`)
      loadData()
    } catch (error) {
      console.error('Failed to smart schedule:', error)
      alert('Failed to create smart schedule. Check console for details.')
    } finally {
      setAutomating(null)
    }
  }

  const resetForm = () => {
    setForm({
      name: '',
      description: '',
      style: 'narrator_broll',
      posts_per_day: 1,
      auto_mode: false,
      post_to_youtube: true,
      post_to_instagram: true,
      post_to_tiktok: true,
      youtube_account_id: '',
      instagram_account_id: '',
      tiktok_account_id: '',
      prompt_hook: 'Generate an attention-grabbing hook for a video about {topic}.',
      prompt_body: 'Write the main content script for a 60-second video about {topic}.',
      prompt_cta: 'Write a compelling call-to-action for the end of the video.',
      hashtags: '',
      min_duration_seconds: 30,
      max_duration_seconds: 60,
      llm_model: '',
      llm_temperature: 0.7,
      tts_provider: '',
      voice_id: '',
      voice_name: '',
      whisper_model: '',
      whisper_device: '',
      style_preset: '',
    })
    setShowAdvanced(false)
  }

  if (loading) {
    return <div className="flex items-center justify-center h-64">Loading...</div>
  }

  const getPlatformAccounts = (platform) => {
    return accounts.filter(acc => acc.platform === platform)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Niches</h1>
        <Button onClick={() => { resetForm(); setShowModal(true); }}>
          <Plus className="h-4 w-4" />
          Add Niche
        </Button>
      </div>

      {/* Niches Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {niches.map((niche) => (
          <Card key={niche.id} className="!p-0">
            <div className="p-4 border-b">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-semibold text-gray-900">{niche.name}</h3>
                  <p className="text-sm text-gray-500 mt-1">{niche.description}</p>
                </div>
                <div className="flex gap-1">
                  <button
                    onClick={() => handleAutomateNiche(niche.id, 1)}
                    disabled={automating === niche.id}
                    className="p-1.5 rounded hover:bg-gray-100 disabled:opacity-50"
                    title="Automate content generation"
                  >
                    <Lightbulb className={`h-4 w-4 ${niche.auto_mode ? 'text-green-500' : 'text-blue-500'}`} />
                  </button>
                  <button
                    onClick={() => handleSmartSchedule(niche.id)}
                    disabled={automating === niche.id}
                    className="p-1.5 rounded hover:bg-gray-100 disabled:opacity-50"
                    title="Smart schedule at optimal times"
                  >
                    <Clock className="h-4 w-4 text-purple-500" />
                  </button>
                  <button
                    onClick={() => handleEdit(niche)}
                    className="p-1.5 rounded hover:bg-gray-100"
                  >
                    <Edit className="h-4 w-4 text-gray-500" />
                  </button>
                  <button
                    onClick={() => handleDelete(niche.id)}
                    className="p-1.5 rounded hover:bg-gray-100"
                  >
                    <Trash2 className="h-4 w-4 text-red-500" />
                  </button>
                </div>
              </div>
            </div>

            <div className="p-4 space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-500">Style</span>
                <span className="text-gray-900">
                  {VIDEO_STYLES.find(s => s.value === niche.style)?.label}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Posts/Day</span>
                <span className="text-gray-900">{niche.posts_per_day}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Duration</span>
                <span className="text-gray-900">{niche.min_duration_seconds}-{niche.max_duration_seconds}s</span>
              </div>
              {niche.llm_model && (
                <div className="flex justify-between">
                  <span className="text-gray-500">LLM</span>
                  <span className="text-gray-900 text-xs">{niche.llm_model}</span>
                </div>
              )}
              {niche.tts_provider && (
                <div className="flex justify-between">
                  <span className="text-gray-500">TTS</span>
                  <span className="text-gray-900">{niche.tts_provider}</span>
                </div>
              )}
              <div className="flex gap-1 flex-wrap">
                {niche.post_to_youtube && <span className="px-2 py-0.5 bg-red-100 text-red-700 rounded text-xs">YouTube</span>}
                {niche.post_to_instagram && <span className="px-2 py-0.5 bg-pink-100 text-pink-700 rounded text-xs">Instagram</span>}
                {niche.post_to_tiktok && <span className="px-2 py-0.5 bg-gray-100 text-gray-700 rounded text-xs">TikTok</span>}
              </div>
            </div>

            <div className="p-4 border-t bg-gray-50">
              <Button
                size="sm"
                variant="outline"
                onClick={() => handleGenerateTopics(niche.id)}
                loading={generatingTopics === niche.id}
                className="w-full"
              >
                <Lightbulb className="h-4 w-4" />
                Generate Topic Ideas
              </Button>

              {topicSuggestions[niche.id] && (
                <div className="mt-3 space-y-1">
                  {topicSuggestions[niche.id].map((topic, i) => (
                    <p key={i} className="text-xs text-gray-600 py-1 px-2 bg-white rounded">
                      {topic}
                    </p>
                  ))}
                </div>
              )}
            </div>
          </Card>
        ))}
      </div>

      {niches.length === 0 && (
        <Card>
          <div className="text-center py-12">
            <p className="text-gray-500 mb-4">No niches created yet.</p>
            <Button onClick={() => setShowModal(true)}>
              <Plus className="h-4 w-4" />
              Create Your First Niche
            </Button>
          </div>
        </Card>
      )}

      {/* Create/Edit Modal */}
      <Modal
        isOpen={showModal}
        onClose={() => { setShowModal(false); setEditingNiche(null); }}
        title={editingNiche ? 'Edit Niche' : 'Create Niche'}
        size="lg"
      >
        <form onSubmit={handleSubmit} className="space-y-4 max-h-[70vh] overflow-y-auto pr-2">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
              <input
                type="text"
                value={form.name}
                onChange={(e) => setForm(prev => ({ ...prev, name: e.target.value }))}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Style</label>
              <select
                value={form.style}
                onChange={(e) => setForm(prev => ({ ...prev, style: e.target.value }))}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              >
                {VIDEO_STYLES.map(style => (
                  <option key={style.value} value={style.value}>{style.label}</option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <textarea
              value={form.description}
              onChange={(e) => setForm(prev => ({ ...prev, description: e.target.value }))}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              rows={2}
            />
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Posts/Day</label>
              <input
                type="number"
                min="0"
                max="10"
                value={form.posts_per_day}
                onChange={(e) => setForm(prev => ({ ...prev, posts_per_day: parseInt(e.target.value) }))}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Auto Mode</label>
              <div className="flex items-center mt-2">
                <input
                  type="checkbox"
                  checked={form.auto_mode}
                  onChange={(e) => setForm(prev => ({ ...prev, auto_mode: e.target.checked }))}
                  className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                />
                <span className="ml-2 text-sm text-gray-600">Enable automated posting</span>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Min Duration (s)</label>
              <input
                type="number"
                value={form.min_duration_seconds}
                onChange={(e) => setForm(prev => ({ ...prev, min_duration_seconds: parseInt(e.target.value) }))}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Max Duration (s)</label>
              <input
                type="number"
                value={form.max_duration_seconds}
                onChange={(e) => setForm(prev => ({ ...prev, max_duration_seconds: parseInt(e.target.value) }))}
                className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Platforms & Accounts</label>
            <div className="space-y-3">
              <div className="flex items-center gap-4">
                <label className="flex items-center gap-2 w-32">
                  <input
                    type="checkbox"
                    checked={form.post_to_youtube}
                    onChange={(e) => setForm(prev => ({ ...prev, post_to_youtube: e.target.checked }))}
                    className="rounded"
                  />
                  YouTube
                </label>
                <select
                  value={form.youtube_account_id}
                  onChange={(e) => setForm(prev => ({ ...prev, youtube_account_id: e.target.value }))}
                  disabled={!form.post_to_youtube}
                  className="flex-1 px-3 py-1.5 border rounded-lg text-sm disabled:bg-gray-100 disabled:text-gray-400"
                >
                  <option value="">Default Account</option>
                  {getPlatformAccounts('youtube').map(acc => (
                    <option key={acc.id} value={acc.id}>{acc.account_name}</option>
                  ))}
                </select>
              </div>

              <div className="flex items-center gap-4">
                <label className="flex items-center gap-2 w-32">
                  <input
                    type="checkbox"
                    checked={form.post_to_instagram}
                    onChange={(e) => setForm(prev => ({ ...prev, post_to_instagram: e.target.checked }))}
                    className="rounded"
                  />
                  Instagram
                </label>
                <select
                  value={form.instagram_account_id}
                  onChange={(e) => setForm(prev => ({ ...prev, instagram_account_id: e.target.value }))}
                  disabled={!form.post_to_instagram}
                  className="flex-1 px-3 py-1.5 border rounded-lg text-sm disabled:bg-gray-100 disabled:text-gray-400"
                >
                  <option value="">Default Account</option>
                  {getPlatformAccounts('instagram').map(acc => (
                    <option key={acc.id} value={acc.id}>{acc.account_name}</option>
                  ))}
                </select>
              </div>

              <div className="flex items-center gap-4">
                <label className="flex items-center gap-2 w-32">
                  <input
                    type="checkbox"
                    checked={form.post_to_tiktok}
                    onChange={(e) => setForm(prev => ({ ...prev, post_to_tiktok: e.target.checked }))}
                    className="rounded"
                  />
                  TikTok
                </label>
                <select
                  value={form.tiktok_account_id}
                  onChange={(e) => setForm(prev => ({ ...prev, tiktok_account_id: e.target.value }))}
                  disabled={!form.post_to_tiktok}
                  className="flex-1 px-3 py-1.5 border rounded-lg text-sm disabled:bg-gray-100 disabled:text-gray-400"
                >
                  <option value="">Default Account</option>
                  {getPlatformAccounts('tiktok').map(acc => (
                    <option key={acc.id} value={acc.id}>{acc.account_name}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Hashtags (comma-separated)</label>
            <input
              type="text"
              value={form.hashtags}
              onChange={(e) => setForm(prev => ({ ...prev, hashtags: e.target.value }))}
              placeholder="viral, trending, fyp"
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
            />
          </div>

          {/* Advanced AI Settings Toggle */}
          <div className="border-t pt-4">
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="flex items-center gap-2 text-sm font-medium text-gray-700 hover:text-gray-900"
            >
              <Settings2 className="h-4 w-4" />
              Advanced AI Settings
              <span className="text-xs text-gray-400">{showAdvanced ? '(hide)' : '(show)'}</span>
            </button>
          </div>

          {showAdvanced && (
            <div className="space-y-4 pl-4 border-l-2 border-primary-200">
              <p className="text-xs text-gray-500">
                Override global settings for this niche. Leave empty to use defaults.
              </p>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">LLM Model</label>
                  <select
                    value={form.llm_model}
                    onChange={(e) => setForm(prev => ({ ...prev, llm_model: e.target.value }))}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-sm"
                  >
                    <option value="">Use Global Default</option>
                    {installedModels.map(model => (
                      <option key={model.name} value={model.name}>{model.name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Temperature</label>
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    max="2"
                    value={form.llm_temperature}
                    onChange={(e) => setForm(prev => ({ ...prev, llm_temperature: parseFloat(e.target.value) }))}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">TTS Provider</label>
                  <select
                    value={form.tts_provider}
                    onChange={(e) => setForm(prev => ({ ...prev, tts_provider: e.target.value }))}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  >
                    {TTS_PROVIDERS.map(p => (
                      <option key={p.value} value={p.value}>{p.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Voice ID / Speaker WAV</label>
                  <input
                    type="text"
                    value={form.voice_id}
                    onChange={(e) => setForm(prev => ({ ...prev, voice_id: e.target.value }))}
                    placeholder="ElevenLabs ID or XTTS wav path"
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-sm"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Whisper Model</label>
                  <select
                    value={form.whisper_model}
                    onChange={(e) => setForm(prev => ({ ...prev, whisper_model: e.target.value }))}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  >
                    {WHISPER_MODELS.map(m => (
                      <option key={m.value} value={m.value}>{m.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Whisper Device</label>
                  <select
                    value={form.whisper_device}
                    onChange={(e) => setForm(prev => ({ ...prev, whisper_device: e.target.value }))}
                    className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  >
                    {WHISPER_DEVICES.map(d => (
                      <option key={d.value} value={d.value}>{d.label}</option>
                    ))}
                  </select>
                </div>
              </div>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Hook Prompt</label>
            <textarea
              value={form.prompt_hook}
              onChange={(e) => setForm(prev => ({ ...prev, prompt_hook: e.target.value }))}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-sm"
              rows={2}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Body Prompt</label>
            <textarea
              value={form.prompt_body}
              onChange={(e) => setForm(prev => ({ ...prev, prompt_body: e.target.value }))}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-sm"
              rows={2}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">CTA Prompt</label>
            <textarea
              value={form.prompt_cta}
              onChange={(e) => setForm(prev => ({ ...prev, prompt_cta: e.target.value }))}
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-sm"
              rows={2}
            />
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t">
            <Button type="button" variant="secondary" onClick={() => { setShowModal(false); setEditingNiche(null); }}>
              Cancel
            </Button>
            <Button type="submit">
              {editingNiche ? 'Save Changes' : 'Create Niche'}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  )
}
