import { useState, useEffect } from 'react'
import { Play, Pause, Settings, Clock, Users, TrendingUp, Zap } from 'lucide-react'
import Card from '../components/Card'
import Button from '../components/Button'
import Modal from '../components/Modal'
import { getNiches, updateNiche, triggerGeneration, getPlatformStats as apiGetPlatformStats } from '../api'

const PLATFORMS = {
  youtube: {
    name: 'YouTube Shorts',
    color: 'red',
    icon: '📺',
    description: 'Vertical video content for YouTube'
  },
  instagram: {
    name: 'Instagram Reels',
    color: 'pink',
    icon: '📸',
    description: 'Short-form video content for Instagram'
  },
  tiktok: {
    name: 'TikTok',
    color: 'gray',
    icon: '🎵',
    description: 'Trending short videos for TikTok'
  }
}

export default function Platforms() {
  const [niches, setNiches] = useState([])
  const [platformStats, setPlatformStats] = useState({})
  const [loading, setLoading] = useState(true)
  const [selectedPlatform, setSelectedPlatform] = useState('youtube')
  const [showScheduleModal, setShowScheduleModal] = useState(false)
  const [editingNiche, setEditingNiche] = useState(null)
  const [generating, setGenerating] = useState(false)
  const [scheduleForm, setScheduleForm] = useState({
    posting_schedule: ['09:00', '19:00']
  })

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const [nichesRes, statsRes] = await Promise.all([
        getNiches(),
        apiGetPlatformStats()
      ])
      setNiches(nichesRes.data || [])
      setPlatformStats(statsRes.data || {})
    } catch (error) {
      console.error('Failed to load data:', error)
    } finally {
      setLoading(false)
    }
  }

  const toggleAutoMode = async (niche) => {
    try {
      await updateNiche(niche.id, {
        auto_mode: !niche.auto_mode
      })
      await loadData()
    } catch (error) {
      console.error('Failed to toggle auto mode:', error)
    }
  }

  const updateSchedule = async () => {
    if (!editingNiche) return

    try {
      await updateNiche(editingNiche.id, {
        posting_schedule: scheduleForm.posting_schedule
      })
      setShowScheduleModal(false)
      setEditingNiche(null)
      await loadData()
    } catch (error) {
      console.error('Failed to update schedule:', error)
    }
  }

  const getPlatformNiches = (platform) => {
    return niches.filter(niche => niche.platform === platform)
  }

  const getPlatformStatsLocal = (platform) => {
    const platformNiches = getPlatformNiches(platform)
    return {
      total: platformNiches.length,
      active: platformNiches.filter(n => n.auto_mode).length,
      postsPerDay: platformNiches.filter(n => n.auto_mode).reduce((sum, n) => sum + n.posts_per_day, 0)
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-500"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Platform Management</h1>
          <p className="text-gray-600 mt-1">Manage your content across different platforms</p>
        </div>
      </div>

      {/* Platform Tabs */}
      <div className="flex space-x-1 bg-gray-100 p-1 rounded-lg">
        {Object.entries(PLATFORMS).map(([key, platform]) => {
          const apiStats = platformStats[key] || {}
          const localStats = getPlatformStatsLocal(key)
          const stats = {
            total: apiStats.total_niches || localStats.total,
            active: apiStats.active_niches || localStats.active,
            postsPerDay: apiStats.total_posts_per_day || localStats.postsPerDay
          }
          return (
            <button
              key={key}
              onClick={() => setSelectedPlatform(key)}
              className={`flex-1 px-4 py-3 rounded-md text-sm font-medium transition-all ${
                selectedPlatform === key
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              <div className="flex items-center justify-center space-x-2">
                <span className="text-lg">{platform.icon}</span>
                <span>{platform.name}</span>
              </div>
              <div className="text-xs mt-1 text-gray-500">
                {stats.active}/{stats.total} active • {stats.postsPerDay} posts/day
              </div>
            </button>
          )
        })}
      </div>

      {/* Platform Overview */}
      <Card>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <span className="text-2xl">{PLATFORMS[selectedPlatform].icon}</span>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">
                {PLATFORMS[selectedPlatform].name}
              </h3>
              <p className="text-sm text-gray-600">
                {PLATFORMS[selectedPlatform].description}
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-4 text-sm">
            <div className="flex items-center space-x-1">
              <Users className="h-4 w-4 text-gray-400" />
              <span>{getPlatformStatsLocal(selectedPlatform).total} niches</span>
            </div>
            <div className="flex items-center space-x-1">
              <Zap className="h-4 w-4 text-green-500" />
              <span>{getPlatformStatsLocal(selectedPlatform).active} active</span>
            </div>
            <div className="flex items-center space-x-1">
              <TrendingUp className="h-4 w-4 text-blue-500" />
              <span>{getPlatformStatsLocal(selectedPlatform).postsPerDay} posts/day</span>
            </div>
          </div>
        </div>

        <div className="flex space-x-3">
          <Button
            variant="outline"
            onClick={async () => {
              setGenerating(true)
              try {
                await triggerGeneration(getPlatformNiches(selectedPlatform).map(n => n.id))
                alert('Content generation triggered for all niches on this platform!')
                await loadData()
              } catch (error) {
                console.error('Failed to trigger generation:', error)
                alert('Failed to trigger content generation')
              } finally {
                setGenerating(false)
              }
            }}
            loading={generating}
            disabled={getPlatformStatsLocal(selectedPlatform).active === 0}
          >
            Generate Now
          </Button>
          <p className="text-sm text-gray-600 self-center">
            Manually trigger content generation for all active niches
          </p>
        </div>
      </Card>

      {/* Platform Niches */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {getPlatformNiches(selectedPlatform).map((niche) => (
          <Card key={niche.id}>
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-gray-900">{niche.name}</h3>
                <p className="text-sm text-gray-600 mt-1">{niche.description}</p>

                <div className="flex items-center space-x-2 mt-3">
                  <span className="px-2 py-1 bg-gray-100 text-gray-700 rounded-full text-xs">
                    {niche.account_name || 'No Account'}
                  </span>
                  <span className={`px-2 py-1 rounded-full text-xs ${
                    niche.auto_mode
                      ? 'bg-green-100 text-green-700'
                      : 'bg-gray-100 text-gray-700'
                  }`}>
                    {niche.auto_mode ? 'Auto ON' : 'Auto OFF'}
                  </span>
                </div>

                <div className="flex items-center space-x-2 mt-2 text-sm text-gray-500">
                  <Clock className="h-4 w-4" />
                  <span>{niche.posting_schedule?.join(', ') || 'No schedule'}</span>
                </div>

                <div className="flex items-center space-x-2 mt-1 text-sm text-gray-500">
                  <TrendingUp className="h-4 w-4" />
                  <span>{niche.posts_per_day} posts/day</span>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between mt-4 pt-4 border-t">
              <div className="flex space-x-2">
                <Button
                  size="sm"
                  variant={niche.auto_mode ? "secondary" : "primary"}
                  onClick={() => toggleAutoMode(niche)}
                  className="flex items-center space-x-1"
                >
                  {niche.auto_mode ? (
                    <>
                      <Pause className="h-3 w-3" />
                      <span>Stop Auto</span>
                    </>
                  ) : (
                    <>
                      <Play className="h-3 w-3" />
                      <span>Start Auto</span>
                    </>
                  )}
                </Button>

                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    setEditingNiche(niche)
                    setScheduleForm({
                      posting_schedule: niche.posting_schedule || ['09:00', '19:00']
                    })
                    setShowScheduleModal(true)
                  }}
                  className="flex items-center space-x-1"
                >
                  <Settings className="h-3 w-3" />
                  <span>Schedule</span>
                </Button>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {getPlatformNiches(selectedPlatform).length === 0 && (
        <Card>
          <div className="text-center py-12">
            <span className="text-4xl mb-4 block">{PLATFORMS[selectedPlatform].icon}</span>
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              No niches for {PLATFORMS[selectedPlatform].name}
            </h3>
            <p className="text-gray-600 mb-4">
              Create niches in the Niches page and assign them to this platform.
            </p>
            <Button onClick={() => window.location.href = '/niches'}>
              Go to Niches
            </Button>
          </div>
        </Card>
      )}

      {/* Schedule Modal */}
      <Modal
        isOpen={showScheduleModal}
        onClose={() => {
          setShowScheduleModal(false)
          setEditingNiche(null)
        }}
        title={`Edit Schedule - ${editingNiche?.name}`}
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Posting Times (UTC)
            </label>
            <div className="space-y-2">
              {scheduleForm.posting_schedule.map((time, index) => (
                <div key={index} className="flex items-center space-x-2">
                  <input
                    type="time"
                    value={time}
                    onChange={(e) => {
                      const newSchedule = [...scheduleForm.posting_schedule]
                      newSchedule[index] = e.target.value
                      setScheduleForm({ posting_schedule: newSchedule })
                    }}
                    className="px-3 py-2 border rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                  />
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      const newSchedule = scheduleForm.posting_schedule.filter((_, i) => i !== index)
                      setScheduleForm({ posting_schedule: newSchedule })
                    }}
                    disabled={scheduleForm.posting_schedule.length <= 1}
                  >
                    Remove
                  </Button>
                </div>
              ))}
            </div>
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                setScheduleForm({
                  posting_schedule: [...scheduleForm.posting_schedule, '12:00']
                })
              }}
              className="mt-2"
            >
              Add Time Slot
            </Button>
          </div>

          <div className="flex justify-end space-x-3 pt-4">
            <Button
              variant="outline"
              onClick={() => {
                setShowScheduleModal(false)
                setEditingNiche(null)
              }}
            >
              Cancel
            </Button>
            <Button onClick={updateSchedule}>
              Save Schedule
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}