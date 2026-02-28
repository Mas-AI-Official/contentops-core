import { useState, useEffect } from 'react'
import { RefreshCw, Play, RotateCcw, XCircle, Eye, ChevronDown, ChevronUp, Trash2, Check, AlertCircle } from 'lucide-react'
import Card from '../components/Card'
import Button from '../components/Button'
import StatusBadge from '../components/StatusBadge'
import Modal from '../components/Modal'
import VideoPlayer from '../components/VideoPlayer'
import { getJobs, runJob, retryJob, cancelJob, approveJob, deleteJob, getJobLogs } from '../api'

export default function Queue() {
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all')
  const [expandedJob, setExpandedJob] = useState(null)
  const [jobLogs, setJobLogs] = useState({})
  const [showLogsModal, setShowLogsModal] = useState(false)
  const [selectedJobLogs, setSelectedJobLogs] = useState([])
  const [selectedIds, setSelectedIds] = useState(new Set())
  const [previewJobId, setPreviewJobId] = useState(null)
  const [approving, setApproving] = useState(null)

  useEffect(() => {
    loadJobs()
    const interval = setInterval(loadJobs, 5000)
    return () => clearInterval(interval)
  }, [filter])

  const loadJobs = async () => {
    try {
      const params = {}
      if (filter !== 'all') {
        params.status = filter
      }
      const res = await getJobs(params)
      setJobs(res.data)
    } catch (error) {
      console.error('Failed to load jobs:', error)
    } finally {
      setLoading(false)
    }
  }

  // ... handlers ...
  const handleRun = async (jobId) => {
    try {
      await runJob(jobId)
      loadJobs()
    } catch (error) {
      console.error('Failed to run job:', error)
    }
  }

  const handleRetry = async (jobId) => {
    try {
      await retryJob(jobId)
      loadJobs()
    } catch (error) {
      console.error('Failed to retry job:', error)
    }
  }

  const handleCancel = async (jobId) => {
    if (!confirm('Are you sure you want to cancel this job?')) return
    try {
      await cancelJob(jobId)
      loadJobs()
    } catch (error) {
      console.error('Failed to cancel job:', error)
    }
  }

  const handleViewLogs = async (jobId) => {
    try {
      const res = await getJobLogs(jobId)
      setSelectedJobLogs(res.data)
      setShowLogsModal(true)
    } catch (error) {
      console.error('Failed to load logs:', error)
    }
  }

  const handleDelete = async (jobId) => {
    if (!confirm('Delete this job? This cannot be undone.')) return
    try {
      await deleteJob(jobId)
      setSelectedIds(prev => { const s = new Set(prev); s.delete(jobId); return s })
      loadJobs()
    } catch (error) {
      console.error('Failed to delete job:', error)
    }
  }

  const handleDeleteSelected = async () => {
    if (selectedIds.size === 0) return
    if (!confirm(`Delete ${selectedIds.size} selected job(s)? This cannot be undone.`)) return
    try {
      await Promise.all([...selectedIds].map(id => deleteJob(id)))
      setSelectedIds(new Set())
      loadJobs()
    } catch (error) {
      console.error('Failed to delete jobs:', error)
    }
  }

  const toggleSelect = (jobId) => {
    setSelectedIds(prev => {
      const next = new Set(prev)
      if (next.has(jobId)) next.delete(jobId)
      else next.add(jobId)
      return next
    })
  }

  const toggleSelectAll = () => {
    if (selectedIds.size === filteredJobs.length) setSelectedIds(new Set())
    else setSelectedIds(new Set(filteredJobs.map(j => j.id)))
  }

  const handleApprove = async (jobId, publish) => {
    setApproving(jobId)
    try {
      await approveJob(jobId, publish)
      setPreviewJobId(null)
      loadJobs()
    } catch (error) {
      console.error('Failed to approve:', error)
    } finally {
      setApproving(null)
    }
  }

  const toggleExpand = async (jobId) => {
    if (expandedJob === jobId) {
      setExpandedJob(null)
    } else {
      setExpandedJob(jobId)
      if (!jobLogs[jobId]) {
        try {
          const res = await getJobLogs(jobId)
          setJobLogs(prev => ({ ...prev, [jobId]: res.data }))
        } catch (error) {
          console.error('Failed to load logs:', error)
        }
      }
    }
  }

  const filteredJobs = filter === 'all'
    ? jobs
    : jobs.filter(j => j.status === filter)

  if (loading) {
    return <div className="flex items-center justify-center h-64">Loading...</div>
  }

  const pendingReviewCount = jobs.filter(j => j.status === 'ready_for_review').length

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <h1 className="text-2xl font-bold text-gray-900">Job Queue</h1>
        <div className="flex items-center gap-2 flex-wrap">
          {filteredJobs.length > 0 && (
            <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
              <input
                type="checkbox"
                checked={selectedIds.size === filteredJobs.length && filteredJobs.length > 0}
                onChange={toggleSelectAll}
                className="rounded border-gray-300"
              />
              Select all
            </label>
          )}
          {selectedIds.size > 0 && (
            <Button variant="danger" size="sm" onClick={handleDeleteSelected}>
              <Trash2 className="h-4 w-4 mr-1" />
              Delete selected ({selectedIds.size})
            </Button>
          )}
          {pendingReviewCount > 0 && (
            <Button onClick={() => setFilter('ready_for_review')} className="bg-amber-500 hover:bg-amber-600 border-amber-600">
              <Eye className="h-4 w-4 mr-2" />
              Review {pendingReviewCount} Items
            </Button>
          )}
          <Button variant="secondary" onClick={loadJobs}>
            <RefreshCw className="h-4 w-4" />
            Refresh
          </Button>
        </div>
      </div>

      {pendingReviewCount > 0 && filter !== 'ready_for_review' && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <AlertCircle className="h-5 w-5 text-amber-600" />
            <div>
              <h3 className="font-medium text-amber-900">Governance Action Required</h3>
              <p className="text-sm text-amber-700">You have {pendingReviewCount} videos waiting for review before publishing.</p>
            </div>
          </div>
          <Button size="sm" onClick={() => setFilter('ready_for_review')} className="bg-amber-600 hover:bg-amber-700 text-white border-transparent">
            Review Now
          </Button>
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-2 flex-wrap">
        {['all', 'pending', 'queued', 'rendering', 'ready_for_review', 'published', 'failed'].map(status => (
          <button
            key={status}
            onClick={() => setFilter(status)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${filter === status
              ? 'bg-primary-100 text-primary-700'
              : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
          >
            {status.replace(/_/g, ' ')}
          </button>
        ))}
      </div>

      {/* Jobs List */}
      <div className="space-y-3">
        {filteredJobs.length === 0 ? (
          <Card>
            <div className="text-center py-12">
              <p className="text-gray-500">No jobs found.</p>
            </div>
          </Card>
        ) : (
          filteredJobs.map(job => (
            <Card key={job.id} className="!p-0">
              <div className="p-4">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-start gap-3 flex-1 min-w-0">
                    <label className="flex items-center pt-0.5 cursor-pointer shrink-0">
                      <input
                        type="checkbox"
                        checked={selectedIds.has(job.id)}
                        onChange={() => toggleSelect(job.id)}
                        className="rounded border-gray-300"
                      />
                    </label>
                    <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-2">
                      <span className="text-sm font-medium text-gray-500">#{job.id}</span>
                      <StatusBadge status={job.status} />
                      {job.progress_percent > 0 && job.progress_percent < 100 && (
                        <span className="text-sm text-gray-500">{job.progress_percent}%</span>
                      )}
                    </div>
                    <h3 className="font-medium text-gray-900">{job.topic}</h3>
                    {job.caption && (
                      <p className="text-sm text-gray-600 mt-1 line-clamp-2">{job.caption}</p>
                    )}
                    <p className="text-sm text-gray-500 mt-1">
                      Created: {new Date(job.created_at).toLocaleString()}
                    </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    {job.status === 'pending' && (
                      <>
                        <Button size="sm" onClick={() => handleRun(job.id)}>
                          <Play className="h-4 w-4" />
                          Run
                        </Button>
                        <Button size="sm" variant="secondary" onClick={() => handleCancel(job.id)}>
                          <XCircle className="h-4 w-4" />
                        </Button>
                      </>
                    )}
                    {job.status === 'failed' && (
                      <Button size="sm" variant="secondary" onClick={() => handleRetry(job.id)}>
                        <RotateCcw className="h-4 w-4" />
                        Retry
                      </Button>
                    )}
                    {job.status === 'ready_for_review' && (
                      <>
                        <Button size="sm" variant="secondary" onClick={() => setPreviewJobId(job.id)}>
                          <Eye className="h-4 w-4" />
                          View
                        </Button>
                        <Button size="sm" onClick={() => handleApprove(job.id, true)} loading={approving === job.id}>
                          <Check className="h-4 w-4" />
                          Publish
                        </Button>
                        <Button size="sm" variant="secondary" onClick={() => handleApprove(job.id, false)} loading={approving === job.id}>
                          Approve only
                        </Button>
                      </>
                    )}
                    <Button size="sm" variant="secondary" onClick={() => handleDelete(job.id)} title="Delete job">
                      <Trash2 className="h-4 w-4 text-red-600" />
                    </Button>
                    <button
                      onClick={() => toggleExpand(job.id)}
                      className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                    >
                      {expandedJob === job.id ? (
                        <ChevronUp className="h-4 w-4 text-gray-500" />
                      ) : (
                        <ChevronDown className="h-4 w-4 text-gray-500" />
                      )}
                    </button>
                  </div>
                </div>

                {/* Progress bar */}
                {job.progress_percent > 0 && job.progress_percent < 100 && (
                  <div className="mt-3">
                    <div className="h-1 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-primary-500 transition-all duration-500"
                        style={{ width: `${job.progress_percent}%` }}
                      />
                    </div>
                  </div>
                )}

                {/* Error message */}
                {job.error_message && (
                  <div className="mt-3 p-3 bg-red-50 rounded-lg">
                    <p className="text-sm text-red-700">{job.error_message}</p>
                  </div>
                )}
              </div>

              {/* Expanded Details */}
              {expandedJob === job.id && (
                <div className="border-t p-4 bg-gray-50">
                  <div className="grid grid-cols-2 gap-4 text-sm mb-4">
                    <div>
                      <span className="text-gray-500">Type:</span>{' '}
                      <span className="text-gray-900">{job.job_type}</span>
                    </div>
                    <div>
                      <span className="text-gray-500">Source:</span>{' '}
                      <span className="text-gray-900">{job.topic_source}</span>
                    </div>
                    {job.duration_seconds && (
                      <div>
                        <span className="text-gray-500">Duration:</span>{' '}
                        <span className="text-gray-900">{job.duration_seconds.toFixed(1)}s</span>
                      </div>
                    )}
                    {job.file_size_bytes && (
                      <div>
                        <span className="text-gray-500">Size:</span>{' '}
                        <span className="text-gray-900">{(job.file_size_bytes / 1024 / 1024).toFixed(2)} MB</span>
                      </div>
                    )}
                  </div>

                  {/* Logs */}
                  {jobLogs[job.id] && jobLogs[job.id].length > 0 && (
                    <div>
                      <h4 className="text-sm font-medium text-gray-700 mb-2">Logs</h4>
                      <div className="bg-gray-900 rounded-lg p-3 max-h-48 overflow-y-auto">
                        {jobLogs[job.id].slice(-10).map((log, i) => (
                          <div key={i} className={`text-xs font-mono ${log.level === 'ERROR' ? 'text-red-400' :
                            log.level === 'WARNING' ? 'text-yellow-400' :
                              'text-gray-300'
                            }`}>
                            <span className="text-gray-500">{new Date(log.timestamp).toLocaleTimeString()}</span>{' '}
                            [{log.level}] {log.message}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Publish Results */}
                  {job.publish_results && Object.keys(job.publish_results).length > 0 && (
                    <div className="mt-4">
                      <h4 className="text-sm font-medium text-gray-700 mb-2">Publish Results</h4>
                      <div className="space-y-2">
                        {Object.entries(job.publish_results).map(([platform, result]) => (
                          <div key={platform} className="flex items-center justify-between p-2 bg-white rounded">
                            <span className="font-medium capitalize">{platform}</span>
                            <div className="flex items-center gap-2">
                              <StatusBadge status={result.status} />
                              {result.video_url && (
                                <a
                                  href={result.video_url}
                                  target="_blank"
                                  className="text-primary-600 text-sm hover:underline"
                                >
                                  View
                                </a>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </Card>
          ))
        )}
      </div>

      {/* Preview modal: view video and approve / approve only */}
      <Modal
        isOpen={!!previewJobId}
        onClose={() => setPreviewJobId(null)}
        title="Review video"
        size="lg"
      >
        {previewJobId && (
          <div className="space-y-4">
            <p className="text-sm text-gray-600">Job #{previewJobId} – watch then approve to publish or approve only.</p>
            <VideoPlayer
              src={`/api/generator/preview/${previewJobId}`}
              className="w-full max-w-md mx-auto rounded-lg overflow-hidden bg-black"
            />
            <div className="flex flex-wrap gap-2 justify-end">
              <Button variant="secondary" onClick={() => setPreviewJobId(null)}>Close</Button>
              <Button variant="secondary" onClick={() => handleApprove(previewJobId, false)} loading={approving === previewJobId}>
                Approve only (don’t publish)
              </Button>
              <Button onClick={() => handleApprove(previewJobId, true)} loading={approving === previewJobId}>
                <Check className="h-4 w-4 mr-1" />
                Approve & Publish
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}
