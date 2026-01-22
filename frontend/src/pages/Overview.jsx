import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { 
  Video, 
  Clock, 
  CheckCircle, 
  XCircle, 
  TrendingUp,
  Play,
  AlertCircle
} from 'lucide-react'
import Card from '../components/Card'
import StatusBadge from '../components/StatusBadge'
import { getTodaysJobs, getJobs, getAnalyticsSummary, checkServices } from '../api'

export default function Overview() {
  const [todayStats, setTodayStats] = useState(null)
  const [recentJobs, setRecentJobs] = useState([])
  const [analytics, setAnalytics] = useState(null)
  const [services, setServices] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const [todayRes, jobsRes, analyticsRes, servicesRes] = await Promise.all([
        getTodaysJobs(),
        getJobs({ limit: 5 }),
        getAnalyticsSummary(),
        checkServices()
      ])
      setTodayStats(todayRes.data)
      setRecentJobs(jobsRes.data)
      setAnalytics(analyticsRes.data)
      setServices(servicesRes.data)
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
        {/* Recent Jobs */}
        <Card title="Recent Jobs" className="lg:col-span-2">
          {recentJobs.length === 0 ? (
            <p className="text-gray-500 text-center py-8">No jobs yet. Create your first video!</p>
          ) : (
            <div className="space-y-3">
              {recentJobs.map((job) => (
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

        {/* Quick Stats & Services */}
        <div className="space-y-6">
          {/* Analytics Summary */}
          <Card title="Performance">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-gray-500">Total Videos</span>
                <span className="font-semibold">{analytics?.total_videos || 0}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-500">Total Views</span>
                <span className="font-semibold">{analytics?.total_views?.toLocaleString() || 0}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-500">Winners</span>
                <span className="font-semibold text-green-600">{analytics?.winner_count || 0}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-500">Avg. Engagement</span>
                <span className="font-semibold">
                  {((analytics?.avg_engagement_rate || 0) * 100).toFixed(1)}%
                </span>
              </div>
            </div>
            <div className="mt-4 pt-4 border-t">
              <Link to="/analytics" className="text-primary-600 hover:text-primary-700 text-sm font-medium">
                View analytics →
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
