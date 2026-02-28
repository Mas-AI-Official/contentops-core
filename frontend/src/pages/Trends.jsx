import { useState, useEffect } from 'react'
import { TrendingUp, RefreshCw, ExternalLink, Sparkles, FlaskConical } from 'lucide-react'
import { Link } from 'react-router-dom'
import Card from '../components/Card'
import Button from '../components/Button'
import { getNiches, scanTrends, getTrendCandidates } from '../api'

export default function Trends() {
  const [niches, setNiches] = useState([])
  const [selectedNicheId, setSelectedNicheId] = useState('')
  const [candidates, setCandidates] = useState([])
  const [loading, setLoading] = useState(false)
  const [scanning, setScanning] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    getNiches().then(res => {
      const list = res.data || []
      setNiches(list)
      if (list.length > 0 && !selectedNicheId) setSelectedNicheId(String(list[0].id))
    }).catch(err => setError('Failed to load niches'))
  }, [])

  useEffect(() => {
    if (selectedNicheId) loadCandidates()
    else setCandidates([])
  }, [selectedNicheId])

  const loadCandidates = async () => {
    if (!selectedNicheId) return
    setLoading(true)
    setError(null)
    try {
      const res = await getTrendCandidates(parseInt(selectedNicheId, 10))
      setCandidates(Array.isArray(res.data) ? res.data : [])
    } catch (err) {
      setCandidates([])
    } finally {
      setLoading(false)
    }
  }

  const handleScan = async () => {
    if (!selectedNicheId) return
    setScanning(true)
    setError(null)
    try {
      const res = await scanTrends({
        niche_id: parseInt(selectedNicheId, 10),
        platforms: ['instagram', 'tiktok', 'youtube'],
        region: 'US',
        limit: 15
      })
      setCandidates(Array.isArray(res.data) ? res.data : [])
    } catch (err) {
      setError(err.response?.data?.detail || 'Scan failed')
    } finally {
      setScanning(false)
    }
  }

  const selectedNiche = niches.find(n => String(n.id) === selectedNicheId)

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Trend Discovery</h1>

      <Card title="1. Select Niche and scan">
        <p className="text-sm text-gray-500 mb-4">
          Choose a niche, then scan for trending content. Use the best ideas in Prompt Lab or Generator.
        </p>
        <div className="flex flex-wrap items-center gap-4">
          <select
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white text-gray-900 min-w-[200px]"
            value={selectedNicheId}
            onChange={e => setSelectedNicheId(e.target.value)}
          >
            <option value="">Select Niche</option>
            {niches.map(n => (
              <option key={n.id} value={n.id}>{n.name}</option>
            ))}
          </select>
          <Button onClick={handleScan} loading={scanning} disabled={!selectedNicheId || scanning}>
            <TrendingUp className="h-4 w-4 mr-2" />
            {scanning ? 'Scanning...' : 'Scan Trends'}
          </Button>
          {selectedNicheId && (
            <Button variant="secondary" onClick={loadCandidates} disabled={loading}>
              <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
              Refresh list
            </Button>
          )}
        </div>
        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
      </Card>

      <Card title="2. Trending candidates">
        {!selectedNicheId ? (
          <p className="text-gray-500 py-8 text-center">Select a niche and click Scan Trends.</p>
        ) : loading && candidates.length === 0 ? (
          <div className="py-12 flex flex-col items-center justify-center text-gray-500">
            <RefreshCw className="h-10 w-10 animate-spin mb-2" />
            Loading candidates...
          </div>
        ) : candidates.length === 0 ? (
          <div className="py-12 text-center">
            <p className="text-gray-500 mb-4">No trend candidates yet. Hit Scan Trends.</p>
            <Button onClick={handleScan} loading={scanning}>
              <Sparkles className="h-4 w-4 mr-2" />
              Scan now
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {candidates.map(c => (
              <div key={c.id} className="p-4 rounded-xl border border-gray-200 bg-white shadow-sm hover:border-primary-300">
                <div className="flex justify-between items-start gap-2 mb-2">
                  <span className="px-2 py-0.5 rounded text-xs font-medium bg-primary-100 text-primary-700 uppercase">{c.platform}</span>
                  <span className="text-xs text-gray-400">{c.discovered_at ? new Date(c.discovered_at).toLocaleDateString() : ''}</span>
                </div>
                <p className="font-medium text-gray-900 text-sm line-clamp-3 mb-3">{c.caption || 'No caption'}</p>
                <div className="flex gap-2 text-xs text-gray-500 mb-3">
                  {c.metrics?.views != null && <span>{Number(c.metrics.views).toLocaleString()} views</span>}
                  {c.metrics?.likes != null && <span>{Number(c.metrics.likes).toLocaleString()} likes</span>}
                </div>
                <div className="flex flex-wrap gap-2">
                  {c.url && (
                    <a href={c.url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center text-xs text-primary-600 hover:underline">
                      <ExternalLink className="h-3 w-3 mr-1" /> Source
                    </a>
                  )}
                  <Link to={`/promptlab?niche_id=${selectedNicheId}&candidate_id=${c.id}`} className="inline-flex items-center text-xs text-primary-600 hover:underline">
                    <FlaskConical className="h-3 w-3 mr-1" /> Use in Prompt Lab
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  )
}
