import { useState, useEffect } from 'react'
import { FileText, Download, Calendar, Search, FolderOpen } from 'lucide-react'
import Card from '../components/Card'
import Button from '../components/Button'
import Modal from '../components/Modal'
import api from '../api'

export default function Scripts() {
  const [scripts, setScripts] = useState([])
  const [stats, setStats] = useState(null)
  const [dates, setDates] = useState([])
  const [niches, setNiches] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedScript, setSelectedScript] = useState(null)
  const [scriptContent, setScriptContent] = useState(null)
  const [filter, setFilter] = useState({ niche: '', date: '' })

  useEffect(() => {
    loadData()
  }, [filter])

  const loadData = async () => {
    try {
      const params = {}
      if (filter.niche) params.niche = filter.niche
      if (filter.date) params.date = filter.date

      const [scriptsRes, statsRes, datesRes, nichesRes] = await Promise.all([
        api.get('/scripts/', { params }),
        api.get('/scripts/stats'),
        api.get('/scripts/dates'),
        api.get('/scripts/niches')
      ])
      
      setScripts(scriptsRes.data.scripts)
      setStats(statsRes.data)
      setDates(datesRes.data.dates)
      setNiches(nichesRes.data.niches)
    } catch (error) {
      console.error('Failed to load scripts:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleViewScript = async (script) => {
    setSelectedScript(script)
    try {
      const res = await api.get('/scripts/by-path', { params: { path: script.path } })
      setScriptContent(res.data)
    } catch (error) {
      console.error('Failed to load script content:', error)
    }
  }

  const handleDownload = async (jobId, format) => {
    try {
      const response = await api.get(`/scripts/download/${jobId}`, {
        params: { format },
        responseType: 'blob'
      })
      
      const url = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = url
      link.setAttribute('download', `script_${jobId}.${format}`)
      document.body.appendChild(link)
      link.click()
      link.remove()
    } catch (error) {
      console.error('Failed to download script:', error)
    }
  }

  if (loading) {
    return <div className="flex items-center justify-center h-64">Loading...</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Script Library</h1>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="!p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100 rounded-lg">
              <FileText className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Total Scripts</p>
              <p className="text-xl font-bold text-gray-900">{stats?.total || 0}</p>
            </div>
          </div>
        </Card>
        
        <Card className="!p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-green-100 rounded-lg">
              <FolderOpen className="h-5 w-5 text-green-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Niches</p>
              <p className="text-xl font-bold text-gray-900">{Object.keys(stats?.by_niche || {}).length}</p>
            </div>
          </div>
        </Card>
        
        <Card className="!p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-100 rounded-lg">
              <Calendar className="h-5 w-5 text-purple-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Days with Scripts</p>
              <p className="text-xl font-bold text-gray-900">{Object.keys(stats?.by_date || {}).length}</p>
            </div>
          </div>
        </Card>
        
        <Card className="!p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-orange-100 rounded-lg">
              <FileText className="h-5 w-5 text-orange-600" />
            </div>
            <div>
              <p className="text-sm text-gray-500">Today's Scripts</p>
              <p className="text-xl font-bold text-gray-900">
                {stats?.by_date?.[new Date().toISOString().split('T')[0]] || 0}
              </p>
            </div>
          </div>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <div className="flex flex-wrap gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Filter by Niche</label>
            <select
              value={filter.niche}
              onChange={(e) => setFilter(prev => ({ ...prev, niche: e.target.value }))}
              className="px-3 py-2 border rounded-lg text-sm min-w-[150px]"
            >
              <option value="">All Niches</option>
              {niches.map(niche => (
                <option key={niche} value={niche}>{niche}</option>
              ))}
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Filter by Date</label>
            <select
              value={filter.date}
              onChange={(e) => setFilter(prev => ({ ...prev, date: e.target.value }))}
              className="px-3 py-2 border rounded-lg text-sm min-w-[150px]"
            >
              <option value="">All Dates</option>
              {dates.map(date => (
                <option key={date} value={date}>{date}</option>
              ))}
            </select>
          </div>
          
          {(filter.niche || filter.date) && (
            <div className="flex items-end">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setFilter({ niche: '', date: '' })}
              >
                Clear Filters
              </Button>
            </div>
          )}
        </div>
      </Card>

      {/* Scripts List */}
      <Card title={`Scripts (${scripts.length})`}>
        {scripts.length === 0 ? (
          <div className="text-center py-12">
            <FileText className="h-12 w-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500">No scripts found.</p>
            <p className="text-sm text-gray-400">Generate some videos to see scripts here.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {scripts.map((script) => (
              <div
                key={script.path}
                className="flex items-center justify-between p-4 border rounded-lg hover:bg-gray-50 cursor-pointer"
                onClick={() => handleViewScript(script)}
              >
                <div className="flex items-center gap-3 flex-1 min-w-0">
                  <FileText className="h-5 w-5 text-gray-400 flex-shrink-0" />
                  <div className="min-w-0">
                    <p className="font-medium text-gray-900 truncate">{script.topic}</p>
                    <div className="flex items-center gap-2 text-sm text-gray-500">
                      <span className="px-2 py-0.5 bg-gray-100 rounded text-xs">{script.niche}</span>
                      <span>Job #{script.job_id}</span>
                      <span>•</span>
                      <span>{new Date(script.created_at).toLocaleString()}</span>
                      {script.estimated_duration && (
                        <>
                          <span>•</span>
                          <span>~{script.estimated_duration}s</span>
                        </>
                      )}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => handleDownload(script.job_id, 'txt')}
                  >
                    <Download className="h-4 w-4" />
                    TXT
                  </Button>
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => handleDownload(script.job_id, 'json')}
                  >
                    JSON
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      {/* Script Detail Modal */}
      <Modal
        isOpen={!!selectedScript}
        onClose={() => { setSelectedScript(null); setScriptContent(null); }}
        title="Script Details"
        size="lg"
      >
        {scriptContent && (
          <div className="space-y-4">
            <div>
              <h3 className="font-semibold text-gray-900">{scriptContent.topic}</h3>
              <p className="text-sm text-gray-500">
                {scriptContent.niche} • Job #{scriptContent.job_id} • {new Date(scriptContent.created_at).toLocaleString()}
              </p>
            </div>
            
            <div className="space-y-4">
              <div>
                <h4 className="text-sm font-medium text-gray-500 mb-1">Hook</h4>
                <div className="p-3 bg-yellow-50 rounded-lg border border-yellow-100">
                  <p className="text-gray-900">{scriptContent.hook}</p>
                </div>
              </div>
              
              <div>
                <h4 className="text-sm font-medium text-gray-500 mb-1">Body</h4>
                <div className="p-3 bg-blue-50 rounded-lg border border-blue-100">
                  <p className="text-gray-900 whitespace-pre-wrap">{scriptContent.body}</p>
                </div>
              </div>
              
              <div>
                <h4 className="text-sm font-medium text-gray-500 mb-1">Call to Action</h4>
                <div className="p-3 bg-green-50 rounded-lg border border-green-100">
                  <p className="text-gray-900">{scriptContent.cta}</p>
                </div>
              </div>
            </div>
            
            <div className="flex items-center justify-between pt-4 border-t">
              <p className="text-sm text-gray-500">
                Estimated duration: ~{scriptContent.estimated_duration}s
              </p>
              <div className="flex gap-2">
                <Button
                  variant="secondary"
                  onClick={() => handleDownload(scriptContent.job_id, 'txt')}
                >
                  <Download className="h-4 w-4" />
                  Download TXT
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => handleDownload(scriptContent.job_id, 'json')}
                >
                  Download JSON
                </Button>
              </div>
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}
