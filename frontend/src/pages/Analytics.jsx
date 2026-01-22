import { useState, useEffect } from 'react'
import { 
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell 
} from 'recharts'
import { TrendingUp, Eye, Heart, MessageCircle, Trophy, AlertTriangle, RefreshCw } from 'lucide-react'
import Card from '../components/Card'
import Button from '../components/Button'
import { 
  getAnalyticsSummary, getAnalyticsTrends, getTopVideos, getUnderperformers,
  getAnalyticsByNiche, getAnalyticsByPlatform, refreshAnalytics, getNiches
} from '../api'

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8']

export default function Analytics() {
  const [summary, setSummary] = useState(null)
  const [trends, setTrends] = useState([])
  const [topVideos, setTopVideos] = useState([])
  const [underperformers, setUnderperformers] = useState([])
  const [byNiche, setByNiche] = useState([])
  const [byPlatform, setByPlatform] = useState([])
  const [niches, setNiches] = useState([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [selectedNiche, setSelectedNiche] = useState('all')

  useEffect(() => {
    loadData()
  }, [selectedNiche])

  const loadData = async () => {
    try {
      const nicheId = selectedNiche === 'all' ? null : parseInt(selectedNiche)
      const [summaryRes, trendsRes, topRes, underRes, nicheRes, platformRes, nichesRes] = await Promise.all([
        getAnalyticsSummary(nicheId),
        getAnalyticsTrends(30, nicheId),
        getTopVideos(5),
        getUnderperformers(5),
        getAnalyticsByNiche(),
        getAnalyticsByPlatform(),
        getNiches()
      ])
      setSummary(summaryRes.data)
      setTrends(trendsRes.data)
      setTopVideos(topRes.data)
      setUnderperformers(underRes.data)
      setByNiche(nicheRes.data)
      setByPlatform(platformRes.data)
      setNiches(nichesRes.data)
    } catch (error) {
      console.error('Failed to load analytics:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleRefresh = async () => {
    setRefreshing(true)
    try {
      await refreshAnalytics()
      // Wait a bit for the background task
      setTimeout(() => {
        loadData()
        setRefreshing(false)
      }, 3000)
    } catch (error) {
      console.error('Failed to refresh analytics:', error)
      setRefreshing(false)
    }
  }

  if (loading) {
    return <div className="flex items-center justify-center h-64">Loading...</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Analytics</h1>
        <div className="flex gap-3">
          <select
            value={selectedNiche}
            onChange={(e) => setSelectedNiche(e.target.value)}
            className="px-3 py-2 border rounded-lg text-sm"
          >
            <option value="all">All Niches</option>
            {niches.map(niche => (
              <option key={niche.id} value={niche.id}>{niche.name}</option>
            ))}
          </select>
          <Button variant="secondary" onClick={handleRefresh} loading={refreshing}>
            <RefreshCw className="h-4 w-4" />
            Refresh Data
          </Button>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="!p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100 rounded-lg">
              <Eye className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Total Views</p>
              <p className="text-xl font-bold text-gray-900">
                {summary?.total_views?.toLocaleString() || 0}
              </p>
            </div>
          </div>
        </Card>
        
        <Card className="!p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-red-100 rounded-lg">
              <Heart className="h-5 w-5 text-red-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Total Likes</p>
              <p className="text-xl font-bold text-gray-900">
                {summary?.total_likes?.toLocaleString() || 0}
              </p>
            </div>
          </div>
        </Card>
        
        <Card className="!p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-green-100 rounded-lg">
              <Trophy className="h-5 w-5 text-green-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Winners</p>
              <p className="text-xl font-bold text-gray-900">
                {summary?.winner_count || 0}
              </p>
            </div>
          </div>
        </Card>
        
        <Card className="!p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-100 rounded-lg">
              <TrendingUp className="h-5 w-5 text-purple-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Avg. Engagement</p>
              <p className="text-xl font-bold text-gray-900">
                {((summary?.avg_engagement_rate || 0) * 100).toFixed(1)}%
              </p>
            </div>
          </div>
        </Card>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Trends Chart */}
        <Card title="Views Trend (30 Days)">
          {trends.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={trends}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" tickFormatter={(d) => new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })} />
                <YAxis />
                <Tooltip />
                <Line type="monotone" dataKey="views" stroke="#0ea5e9" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[300px] flex items-center justify-center text-gray-500">
              No trend data available
            </div>
          )}
        </Card>

        {/* Platform Distribution */}
        <Card title="Performance by Platform">
          {byPlatform.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={byPlatform}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="platform" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="total_views" fill="#0ea5e9" name="Views" />
                <Bar dataKey="total_likes" fill="#ef4444" name="Likes" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[300px] flex items-center justify-center text-gray-500">
              No platform data available
            </div>
          )}
        </Card>
      </div>

      {/* Top & Underperformers */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Videos */}
        <Card 
          title="Top Performers"
          actions={<Trophy className="h-5 w-5 text-yellow-500" />}
        >
          {topVideos.length > 0 ? (
            <div className="space-y-3">
              {topVideos.map((video, i) => (
                <div key={video.video_id} className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50">
                  <span className="w-6 h-6 bg-yellow-100 text-yellow-700 rounded-full flex items-center justify-center text-sm font-bold">
                    {i + 1}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-gray-900 truncate">{video.title}</p>
                    <p className="text-sm text-gray-500">
                      Virality: {video.virality_score.toFixed(1)}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium text-gray-900">{video.views_velocity.toFixed(0)}/hr</p>
                    <p className="text-xs text-gray-500">velocity</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 text-center py-8">No top performers yet</p>
          )}
        </Card>

        {/* Underperformers */}
        <Card 
          title="Needs Improvement"
          actions={<AlertTriangle className="h-5 w-5 text-orange-500" />}
        >
          {underperformers.length > 0 ? (
            <div className="space-y-3">
              {underperformers.map((video) => (
                <div key={video.video_id} className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50">
                  <div className="w-6 h-6 bg-orange-100 text-orange-700 rounded-full flex items-center justify-center">
                    <AlertTriangle className="h-3 w-3" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-gray-900 truncate">{video.title}</p>
                    <p className="text-sm text-gray-500">
                      Engagement: {video.engagement_score.toFixed(1)}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 text-center py-8">No underperformers identified</p>
          )}
        </Card>
      </div>

      {/* By Niche */}
      <Card title="Performance by Niche">
        {byNiche.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-sm text-gray-500 border-b">
                  <th className="pb-3 font-medium">Niche</th>
                  <th className="pb-3 font-medium text-right">Videos</th>
                  <th className="pb-3 font-medium text-right">Views</th>
                  <th className="pb-3 font-medium text-right">Likes</th>
                  <th className="pb-3 font-medium text-right">Winners</th>
                  <th className="pb-3 font-medium text-right">Avg. Engagement</th>
                </tr>
              </thead>
              <tbody>
                {byNiche.map((niche) => (
                  <tr key={niche.niche_id} className="border-b last:border-0">
                    <td className="py-3 font-medium text-gray-900">{niche.niche_name}</td>
                    <td className="py-3 text-right text-gray-600">{niche.total_videos}</td>
                    <td className="py-3 text-right text-gray-600">{niche.total_views.toLocaleString()}</td>
                    <td className="py-3 text-right text-gray-600">{niche.total_likes.toLocaleString()}</td>
                    <td className="py-3 text-right text-gray-600">{niche.winner_count}</td>
                    <td className="py-3 text-right text-gray-600">
                      {((niche.avg_engagement_rate || 0) * 100).toFixed(1)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-gray-500 text-center py-8">No niche data available</p>
        )}
      </Card>
    </div>
  )
}
