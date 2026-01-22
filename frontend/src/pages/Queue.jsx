import { useState, useEffect } from 'react'
import { RefreshCw, Play, RotateCcw, XCircle, Eye, ChevronDown, ChevronUp } from 'lucide-react'
import Card from '../components/Card'
import Button from '../components/Button'
import StatusBadge from '../components/StatusBadge'
import Modal from '../components/Modal'
import { getJobs, runJob, retryJob, cancelJob, getJobLogs } from '../api'

export default function Queue() {
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all')
  const [expandedJob, setExpandedJob] = useState(null)
  const [jobLogs, setJobLogs] = useState({})
  const [showLogsModal, setShowLogsModal] = useState(false)
  const [selectedJobLogs, setSelectedJobLogs] = useState([])

  useEffect(() => {
    loadJobs()
  }, [])

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

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Job Queue</h1>
        <Button variant="secondary" onClick={loadJobs}>
          <RefreshCw className="h-4 w-4" />
          Refresh
        </Button>
      </div>

      {/* Filters */}
      <div className="flex gap-2 flex-wrap">
        {['all', 'pending', 'queued', 'rendering', 'ready_for_review', 'published', 'failed'].map(status => (
          <button
            key={status}
            onClick={() => setFilter(status)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              filter === status
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
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <span className="text-sm font-medium text-gray-500">#{job.id}</span>
                      <StatusBadge status={job.status} />
                      {job.progress_percent > 0 && job.progress_percent < 100 && (
                        <span className="text-sm text-gray-500">{job.progress_percent}%</span>
                      )}
                    </div>
                    <h3 className="font-medium text-gray-900">{job.topic}</h3>
                    <p className="text-sm text-gray-500 mt-1">
                      Created: {new Date(job.created_at).toLocaleString()}
                    </p>
                  </div>
                  
                  <div className="flex items-center gap-2">
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
                      <Button size="sm" onClick={() => window.location.href = `/library?video=${job.id}`}>
                        <Eye className="h-4 w-4" />
                        Preview
                      </Button>
                    )}
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
                          <div key={i} className={`text-xs font-mono ${
                            log.level === 'ERROR' ? 'text-red-400' :
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
    </div>
  )
}
