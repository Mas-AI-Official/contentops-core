import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  Video,
  Clock,
  CheckCircle,
  XCircle,
  TrendingUp,
  Play,
  AlertCircle,
  Settings2,
  Activity,
  Zap
} from 'lucide-react'
import Card from '../components/Card'
import StatusBadge from '../components/StatusBadge'
import { getTodaysJobs, getJobs, getAnalyticsSummary, checkServices, getNiches, automateNiche, bulkAutomateNiches } from '../api'

export default function Overview() {
  const [todayStats, setTodayStats] = useState(null)
  const [recentJobs, setRecentJobs] = useState([])
  const [analytics, setAnalytics] = useState(null)
  const [services, setServices] = useState(null)
  const [niches, setNiches] = useState([])
  const [automationStatus, setAutomationStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [alerts, setAlerts] = useState([])
  const [pipelineHealth, setPipelineHealth] = useState(null)
  const [activityLog, setActivityLog] = useState([])

  useEffect(() => {
    loadData()

    // Set up real-time monitoring
    const interval = setInterval(() => {
      loadData() // Refresh data every 5 seconds
      checkForAlerts()
    }, 5000)

    return () => clearInterval(interval)
  }, [])

  // Simulate activity log based on job status changes (in a real app, this would be a websocket)
  useEffect(() => {
    if (recentJobs.length > 0) {
      const activities = recentJobs.slice(0, 5).map(job => ({
        id: job.id,
        message: `${job.job_type === 'generate_only' ? 'Generating' : 'Processing'} video for "${job.topic}"`,
        time: new Date(job.updated_at || job.created_at),
        type: job.status === 'failed' ? 'error' : job.status === 'completed' ? 'success' : 'info'
      }))
      setActivityLog(activities)
    }
  }, [recentJobs])

  const handleQuickAutomate = async (nicheId) => {
    try {
      const res = await automateNiche(nicheId, {
        video_count: 1,
        publish: false
      })
      alert(`✅ Automation started! Created ${res.data.jobs.length} job(s)`)
      loadData() // Refresh data
    } catch (error) {
      console.error('Failed to automate niche:', error)
      alert('Failed to start automation')
    }
  }

  const handleBulkAutomate = async () => {
    const activeNicheIds = niches.filter(n => n.auto_mode).map(n => n.id)
    if (activeNicheIds.length === 0) {
      alert('No active niches found. Enable automation for niches first.')
      return
    }

    const count = prompt(`Generate videos for ${activeNicheIds.length} active niches. How many videos per niche?`, '1')
    if (!count || isNaN(count)) return

    try {
      const res = await bulkAutomateNiches(activeNicheIds, {
        videos_per_niche: parseInt(count),
        publish: false
      })
      alert(`✅ Bulk automation started! Created ${res.data.total_jobs} jobs across ${res.data.niches.length} niches`)
      loadData() // Refresh data
    } catch (error) {
      console.error('Failed to bulk automate:', error)
      alert('Failed to start bulk automation')
    }
  }

  const checkForAlerts = () => {
    const newAlerts = []

    // Check for failed jobs in the last hour
    const recentFailures = recentJobs.filter(job => {
      const jobTime = new Date(job.created_at)
      const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000)
      return job.status === 'failed' && jobTime > oneHourAgo
    })

    if (recentFailures.length > 0) {
      newAlerts.push({
        type: 'error',
        message: `${recentFailures.length} jobs failed in the last hour`,
        time: new Date()
      })
    }

    // Check service health
    if (services) {
      Object.entries(services).forEach(([service, status]) => {
        if (status.status === 'error' || status.status === 'not_running') {
          newAlerts.push({
            type: 'warning',
            message: `${service} service is ${status.status}`,
            time: new Date()
          })
        }
      })
    }

    // Check if automation is not running
    if (!automationStatus?.schedulerRunning && niches.some(n => n.auto_mode)) {
      newAlerts.push({
        type: 'warning',
        message: 'Automation is enabled but scheduler is not running',
        time: new Date()
      })
    }

    setAlerts(newAlerts.slice(0, 5)) // Keep only latest 5 alerts
  }

  const getPipelineHealth = () => {
    if (!todayStats || !services) return null

    const totalJobs = todayStats.total || 0
    const completedJobs = todayStats.completed || 0
    const failedJobs = todayStats.failed || 0

    let healthScore = 0
    let issues = []

    // Success rate
    if (totalJobs > 0) {
      const successRate = completedJobs / totalJobs
      if (successRate >= 0.9) healthScore += 40
      else if (successRate >= 0.7) healthScore += 25
      else if (successRate >= 0.5) healthScore += 10
      else issues.push('Low success rate')
    }

    // Service health
    const healthyServices = Object.values(services).filter(s =>
      s.status === 'running' || s.status === 'ok' || s.status === 'installed'
    ).length
    const totalServices = Object.keys(services).length
    const serviceHealth = healthyServices / totalServices

    if (serviceHealth >= 0.8) healthScore += 35
    else if (serviceHealth >= 0.6) healthScore += 20
    else issues.push('Service issues detected')

    // Automation status
    if (automationStatus?.schedulerRunning) healthScore += 25
    else issues.push('Automation not running')

    return {
      score: Math.min(100, healthScore),
      status: healthScore >= 80 ? 'healthy' : healthScore >= 60 ? 'warning' : 'critical',
      issues
    }
  }

  const loadData = async () => {
    try {
      const [todayRes, jobsRes, analyticsRes, servicesRes, nichesRes] = await Promise.all([
        getTodaysJobs(),
        getJobs({ limit: 10 }), // Fetch more jobs for activity log
        getAnalyticsSummary(),
        checkServices(),
        getNiches()
      ])
      setTodayStats(todayRes.data)
      setRecentJobs(jobsRes.data)
      setAnalytics(analyticsRes.data)
      setServices(servicesRes.data)
      setNiches(nichesRes.data || [])

      // Check automation status
      const activeNiches = nichesRes.data?.filter(n => n.auto_mode) || []
      const schedulerRunning = servicesRes.data?.scheduler?.status === 'running'
      setAutomationStatus({
        schedulerRunning,
        activeNiches: activeNiches.length,
        totalNiches: nichesRes.data?.length || 0,
        jobsInProgress: todayRes.data?.in_progress || 0
      })

      // Calculate pipeline health (will be calculated when needed)
      setPipelineHealth(null)

      // Check for alerts (will be called after state is set)
      setTimeout(checkForAlerts, 100)
    } catch (error) {
      console.error('Failed to load overview data:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <div className="flex items-center justify-center h-64">Loading...</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard Overview</h1>
        <Link
          to="/generator"
          className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
        >
          <Play className="h-4 w-4" />
          Generate Video
        </Link>
      </div>

      {/* Automation Status & Health */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card className="!p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <div className={`w-3 h-3 rounded-full ${automationStatus?.schedulerRunning ? 'bg-green-500' : 'bg-gray-400'}`}></div>
                <span className="font-medium text-gray-900">
                  {automationStatus?.schedulerRunning ? 'Automation Active' : 'Automation Inactive'}
                </span>
              </div>
              <div className="flex items-center gap-4 text-sm text-gray-600">
                <span>{automationStatus?.activeNiches || 0} active niches</span>
                <span>{automationStatus?.jobsInProgress || 0} jobs in progress</span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Link
                to="/niches"
                className="text-primary-600 hover:text-primary-700 text-sm font-medium"
              >
                Manage Niches →
              </Link>
            </div>
          </div>
        </Card>

        <Card className="!p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`w-3 h-3 rounded-full ${getPipelineHealth()?.status === 'healthy' ? 'bg-green-500' :
                getPipelineHealth()?.status === 'warning' ? 'bg-yellow-500' : 'bg-red-500'
                }`}></div>
              <div>
                <span className="font-medium text-gray-900">Pipeline Health</span>
                <div className="text-sm text-gray-600">
                  {getPipelineHealth()?.score || 0}% healthy
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {getPipelineHealth()?.issues?.length > 0 && (
                <span className="text-xs text-red-600 bg-red-50 px-2 py-1 rounded">
                  {getPipelineHealth().issues.length} issues
                </span>
              )}
            </div>
          </div>
        </Card>
      </div>

      {/* Alerts */}
      {alerts.length > 0 && (
        <Card className="!p-4 border-red-200 bg-red-50">
          <div className="flex items-center gap-2 mb-2">
            <AlertCircle className="h-5 w-5 text-red-600" />
            <span className="font-medium text-red-900">Alerts</span>
          </div>
          <div className="space-y-2">
            {alerts.map((alert, index) => (
              <div key={index} className={`text-sm p-2 rounded ${alert.type === 'error' ? 'bg-red-100 text-red-800' : 'bg-yellow-100 text-yellow-800'
                }`}>
                {alert.message}
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="!p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100 rounded-lg">
              <Video className="h-6 w-6 text-blue-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Today's Jobs</p>
              <p className="text-2xl font-bold text-gray-900">{todayStats?.total || 0}</p>
            </div>
          </div>
        </Card>

        <Card className="!p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-yellow-100 rounded-lg">
              <Clock className="h-6 w-6 text-yellow-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">In Progress</p>
              <p className="text-2xl font-bold text-gray-900">{todayStats?.in_progress || 0}</p>
            </div>
          </div>
        </Card>

        <Card className="!p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-green-100 rounded-lg">
              <CheckCircle className="h-6 w-6 text-green-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Completed</p>
              <p className="text-2xl font-bold text-gray-900">{todayStats?.completed || 0}</p>
            </div>
          </div>
        </Card>

        <Card className="!p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-red-100 rounded-lg">
              <XCircle className="h-6 w-6 text-red-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Failed</p>
              <p className="text-2xl font-bold text-gray-900">{todayStats?.failed || 0}</p>
            </div>
          </div>
        </Card>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column */}
        <div className="lg:col-span-2 space-y-6">
          {/* Live Activity */}
          <Card title="Live Activity" icon={Activity}>
            {activityLog.length === 0 ? (
              <p className="text-gray-500 text-center py-8">No recent activity.</p>
            ) : (
              <div className="space-y-4">
                {activityLog.map((activity, index) => (
                  <div key={index} className="flex items-start gap-3">
                    <div className={`mt-1 w-2 h-2 rounded-full flex-shrink-0 ${activity.type === 'error' ? 'bg-red-500' :
                      activity.type === 'success' ? 'bg-green-500' : 'bg-blue-500'
                      }`} />
                    <div>
                      <p className="text-sm text-gray-900">{activity.message}</p>
                      <p className="text-xs text-gray-500">{activity.time.toLocaleTimeString()}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>

          {/* Recent Jobs */}
          <Card title="Recent Jobs">
            {recentJobs.length === 0 ? (
              <p className="text-gray-500 text-center py-8">No jobs yet. Create your first video!</p>
            ) : (
              <div className="space-y-3">
                {recentJobs.slice(0, 5).map((job) => (
                  <Link
                    key={job.id}
                    to={`/queue?job=${job.id}`}
                    className="flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center">
                        <Video className="h-5 w-5 text-gray-500" />
                      </div>
                      <div>
                        <p className="font-medium text-gray-900 line-clamp-1">{job.topic}</p>
                        <p className="text-sm text-gray-500">
                          {new Date(job.created_at).toLocaleString()}
                        </p>
                      </div>
                    </div>
                    <StatusBadge status={job.status} />
                  </Link>
                ))}
              </div>
            )}
            <div className="mt-4 pt-4 border-t">
              <Link to="/queue" className="text-primary-600 hover:text-primary-700 text-sm font-medium">
                View all jobs →
              </Link>
            </div>
          </Card>
        </div>

        {/* Right Column */}
        <div className="space-y-6">
          {/* Quick Actions */}
          <Card title="Quick Actions">
            <div className="space-y-3">
              <Link
                to="/generator"
                className="w-full inline-flex items-center justify-center gap-2 px-4 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
              >
                <Video className="h-5 w-5" />
                Generate Video
              </Link>
              <Link
                to="/niches"
                className="w-full inline-flex items-center justify-center gap-2 px-4 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
              >
                <Settings2 className="h-5 w-5" />
                Setup Automation
              </Link>
              <Link
                to="/queue"
                className="w-full inline-flex items-center justify-center gap-2 px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                <Clock className="h-5 w-5" />
                View Queue
              </Link>
              <button
                onClick={handleBulkAutomate}
                className="w-full inline-flex items-center justify-center gap-2 px-4 py-3 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition-colors"
              >
                <Zap className="h-5 w-5" />
                Bulk Generate
              </button>
              <Link
                to="/models"
                className="w-full inline-flex items-center justify-center gap-2 px-4 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
              >
                <TrendingUp className="h-5 w-5" />
                Manage Models
              </Link>
            </div>
          </Card>

          {/* Active Niches */}
          <Card title="Active Niches">
            {niches.filter(n => n.auto_mode).length === 0 ? (
              <div className="text-center py-8">
                <AlertCircle className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-500 mb-4">No active niches</p>
                <Link
                  to="/niches"
                  className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors text-sm"
                >
                  <Settings2 className="h-4 w-4" />
                  Enable Automation
                </Link>
              </div>
            ) : (
              <div className="space-y-3">
                {niches.filter(n => n.auto_mode).map((niche) => (
                  <div key={niche.id} className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
                    <div>
                      <p className="font-medium text-gray-900">{niche.name}</p>
                      <p className="text-sm text-gray-600 line-clamp-1">{niche.description}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleQuickAutomate(niche.id)}
                        className="px-3 py-1 bg-green-600 text-white text-xs rounded hover:bg-green-700 transition-colors"
                      >
                        Generate
                      </button>
                      <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                      <span className="text-xs text-green-700 font-medium">Auto</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
            <div className="mt-4 pt-4 border-t">
              <Link to="/niches" className="text-primary-600 hover:text-primary-700 text-sm font-medium">
                View all niches →
              </Link>
            </div>
          </Card>

          {/* Services Status */}
          <Card title="Services">
            <div className="space-y-3">
              {services && Object.entries(services).map(([name, info]) => (
                <div key={name} className="flex items-center justify-between">
                  <span className="text-gray-700 capitalize">{name.replace('_', ' ')}</span>
                  {info.status === 'running' || info.status === 'installed' || info.status === 'cli_available' ? (
                    <span className="flex items-center gap-1 text-green-600 text-sm">
                      <CheckCircle className="h-4 w-4" />
                      OK
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-red-600 text-sm">
                      <AlertCircle className="h-4 w-4" />
                      {info.status}
                    </span>
                  )}
                </div>
              ))}
            </div>
            <div className="mt-4 pt-4 border-t">
              <Link to="/settings" className="text-primary-600 hover:text-primary-700 text-sm font-medium">
                View settings →
              </Link>
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}
