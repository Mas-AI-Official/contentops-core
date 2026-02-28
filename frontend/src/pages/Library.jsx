import { useState, useEffect } from 'react'
import { Play, Download, Trash2, ExternalLink, Clock, Eye, CheckCircle, AlertCircle, Youtube, Instagram, Music2 } from 'lucide-react'
import Card from '../components/Card'
import Button from '../components/Button'
import VideoPlayer from '../components/VideoPlayer'
import Modal from '../components/Modal'
import { getVideos, getVideo, getVideoPublishes, getVideoMetadata, deleteVideo, getNiches, validateVideoForPlatforms, getPlatformConfigs } from '../api'

export default function Library() {
  const [videos, setVideos] = useState([])
  const [niches, setNiches] = useState([])
  const [selectedVideo, setSelectedVideo] = useState(null)
  const [videoDetails, setVideoDetails] = useState(null)
  const [publishes, setPublishes] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState({ niche: 'all' })
  const [selectedIds, setSelectedIds] = useState(new Set())
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const [videosRes, nichesRes] = await Promise.all([
        getVideos({ limit: 50 }),
        getNiches()
      ])
      setVideos(videosRes.data)
      setNiches(nichesRes.data)
    } catch (error) {
      console.error('Failed to load data:', error)
    } finally {
      setLoading(false)
    }
  }

  const [platformValidation, setPlatformValidation] = useState(null)

  const handleViewVideo = async (video) => {
    setSelectedVideo(video)
    setPlatformValidation(null)
    try {
      const [detailsRes, publishesRes, validationRes] = await Promise.all([
        getVideoMetadata(video.id),
        getVideoPublishes(video.id),
        validateVideoForPlatforms(video.id)
      ])
      setVideoDetails(detailsRes.data)
      setPublishes(publishesRes.data)
      setPlatformValidation(validationRes.data)
    } catch (error) {
      console.error('Failed to load video details:', error)
    }
  }

  const handleDelete = async (videoId) => {
    if (!confirm('Are you sure you want to delete this video? This will also delete the files.')) return
    try {
      await deleteVideo(videoId, true)
      setVideos(prev => prev.filter(v => v.id !== videoId))
      setSelectedVideo(null)
      setSelectedIds(prev => { const s = new Set(prev); s.delete(videoId); return s })
    } catch (error) {
      console.error('Failed to delete video:', error)
    }
  }

  const toggleSelect = (videoId, e) => {
    if (e) e.stopPropagation()
    setSelectedIds(prev => {
      const next = new Set(prev)
      if (next.has(videoId)) next.delete(videoId)
      else next.add(videoId)
      return next
    })
  }

  const toggleSelectAll = () => {
    if (selectedIds.size === filteredVideos.length) setSelectedIds(new Set())
    else setSelectedIds(new Set(filteredVideos.map(v => v.id)))
  }

  const handleDeleteSelected = async () => {
    if (selectedIds.size === 0) return
    if (!confirm(`Delete ${selectedIds.size} selected video(s)? This will also delete the files.`)) return
    setDeleting(true)
    try {
      await Promise.all([...selectedIds].map(id => deleteVideo(id, true)))
      setVideos(prev => prev.filter(v => !selectedIds.has(v.id)))
      setSelectedVideo(null)
      setSelectedIds(new Set())
    } catch (error) {
      console.error('Failed to delete videos:', error)
    } finally {
      setDeleting(false)
    }
  }

  const formatDuration = (seconds) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const filteredVideos = filter.niche === 'all' 
    ? videos 
    : videos.filter(v => v.niche_id === parseInt(filter.niche))

  const getNicheName = (nicheId) => {
    const niche = niches.find(n => n.id === nicheId)
    return niche?.name || 'Unknown'
  }

  if (loading) {
    return <div className="flex items-center justify-center h-64">Loading...</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <h1 className="text-2xl font-bold text-gray-900">Video Library</h1>
        <div className="flex items-center gap-3 flex-wrap">
          {filteredVideos.length > 0 && (
            <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
              <input
                type="checkbox"
                checked={selectedIds.size === filteredVideos.length && filteredVideos.length > 0}
                onChange={toggleSelectAll}
                className="rounded border-gray-300"
              />
              Select all
            </label>
          )}
          {selectedIds.size > 0 && (
            <Button variant="danger" size="sm" onClick={handleDeleteSelected} disabled={deleting}>
              <Trash2 className="h-4 w-4 mr-1" />
              Delete selected ({selectedIds.size})
            </Button>
          )}
          <select
            value={filter.niche}
            onChange={(e) => setFilter(prev => ({ ...prev, niche: e.target.value }))}
            className="px-3 py-2 border rounded-lg text-sm"
          >
            <option value="all">All Niches</option>
            {niches.map(niche => (
              <option key={niche.id} value={niche.id}>{niche.name}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Video Grid */}
      {filteredVideos.length === 0 ? (
        <Card>
          <div className="text-center py-12">
            <p className="text-gray-500">No videos yet. Generate your first video!</p>
          </div>
        </Card>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
          {filteredVideos.map(video => (
            <div
              key={video.id}
              className={`group relative bg-white rounded-xl overflow-hidden shadow-sm border hover:shadow-md transition-shadow cursor-pointer ${selectedIds.has(video.id) ? 'ring-2 ring-indigo-500' : ''}`}
              onClick={() => handleViewVideo(video)}
            >
              {/* Bulk select checkbox */}
              <div
                className="absolute top-2 left-2 z-10"
                onClick={(e) => toggleSelect(video.id, e)}
              >
                <input
                  type="checkbox"
                  checked={selectedIds.has(video.id)}
                  onChange={() => {}}
                  onClick={(e) => e.stopPropagation()}
                  className="rounded border-gray-300 h-5 w-5 bg-white/90 shadow"
                />
              </div>
              {/* Thumbnail */}
              <div className="aspect-[9/16] bg-gray-100 relative">
                {video.thumbnail_path ? (
                  <img
                    src={`/api/videos/${video.id}/thumbnail`}
                    alt={video.title}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    <Play className="h-12 w-12 text-gray-300" />
                  </div>
                )}
                
                {/* Overlay on hover */}
                <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                  <Play className="h-12 w-12 text-white" />
                </div>
                
                {/* Duration badge */}
                <div className="absolute bottom-2 right-2 px-2 py-0.5 bg-black/70 text-white text-xs rounded">
                  {formatDuration(video.duration_seconds)}
                </div>
              </div>
              
              {/* Info */}
              <div className="p-3">
                <h3 className="font-medium text-gray-900 text-sm line-clamp-2">{video.title}</h3>
                {(video.description || video.caption) && (
                  <p className="text-xs text-gray-600 mt-1 line-clamp-2">{video.description || video.caption}</p>
                )}
                <p className="text-xs text-gray-500 mt-1">{getNicheName(video.niche_id)}</p>
                <p className="text-xs text-gray-400 mt-0.5">
                  {new Date(video.created_at).toLocaleDateString()}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Video Detail Modal */}
      <Modal
        isOpen={!!selectedVideo}
        onClose={() => { setSelectedVideo(null); setVideoDetails(null); setPublishes([]); }}
        title="Video Details"
        size="xl"
      >
        {selectedVideo && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Video Player */}
            <div>
              <VideoPlayer
                src={`/api/videos/${selectedVideo.id}/stream`}
                poster={selectedVideo.thumbnail_path ? `/api/videos/${selectedVideo.id}/thumbnail` : undefined}
                className="w-full"
              />
            </div>
            
            {/* Details */}
            <div className="space-y-4">
              <div>
                <h3 className="font-semibold text-gray-900 text-lg">{selectedVideo.title}</h3>
                <p className="text-sm text-gray-500 mt-1">{selectedVideo.topic}</p>
              </div>
              
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <span className="text-gray-500">Niche</span>
                  <p className="text-gray-900">{getNicheName(selectedVideo.niche_id)}</p>
                </div>
                <div>
                  <span className="text-gray-500">Duration</span>
                  <p className="text-gray-900">{formatDuration(selectedVideo.duration_seconds)}</p>
                </div>
                <div>
                  <span className="text-gray-500">Size</span>
                  <p className="text-gray-900">{(selectedVideo.file_size_bytes / 1024 / 1024).toFixed(2)} MB</p>
                </div>
                <div>
                  <span className="text-gray-500">Created</span>
                  <p className="text-gray-900">{new Date(selectedVideo.created_at).toLocaleDateString()}</p>
                </div>
              </div>
              
              {/* Hashtags */}
              {selectedVideo.hashtags && selectedVideo.hashtags.length > 0 && (
                <div>
                  <span className="text-sm text-gray-500">Hashtags</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {selectedVideo.hashtags.map((tag, i) => (
                      <span key={i} className="px-2 py-0.5 bg-gray-100 text-gray-700 rounded text-xs">
                        #{tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              
              {/* Publish Status */}
              {publishes.length > 0 && (
                <div>
                  <span className="text-sm text-gray-500">Published To</span>
                  <div className="space-y-2 mt-2">
                    {publishes.map((pub, i) => (
                      <div key={i} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                        <span className="font-medium capitalize">{pub.platform}</span>
                        <div className="flex items-center gap-2">
                          <span className={`text-xs px-2 py-0.5 rounded ${
                            pub.status === 'published' ? 'bg-green-100 text-green-700' :
                            pub.status === 'private' ? 'bg-yellow-100 text-yellow-700' :
                            'bg-gray-100 text-gray-700'
                          }`}>
                            {pub.status}
                          </span>
                          {pub.url && (
                            <a href={pub.url} target="_blank" className="text-primary-600 hover:text-primary-700">
                              <ExternalLink className="h-4 w-4" />
                            </a>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {/* Platform Compatibility */}
              {platformValidation && (
                <div className="border-t pt-4">
                  <h4 className="text-sm font-medium text-gray-700 mb-3">Platform Compatibility</h4>
                  <div className="grid grid-cols-3 gap-2">
                    {Object.entries(platformValidation.validations || {}).map(([platform, validation]) => (
                      <div 
                        key={platform} 
                        className={`p-3 rounded-lg text-center ${
                          validation.valid ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'
                        }`}
                      >
                        <div className="flex items-center justify-center gap-1 mb-1">
                          {platform === 'youtube_shorts' && <Youtube className="h-4 w-4" />}
                          {platform === 'instagram_reels' && <Instagram className="h-4 w-4" />}
                          {platform === 'tiktok' && <Music2 className="h-4 w-4" />}
                          {validation.valid ? (
                            <CheckCircle className="h-4 w-4 text-green-600" />
                          ) : (
                            <AlertCircle className="h-4 w-4 text-red-600" />
                          )}
                        </div>
                        <p className="text-xs font-medium capitalize">{platform.replace('_', ' ')}</p>
                        {validation.issues?.length > 0 && (
                          <p className="text-xs text-red-600 mt-1">{validation.issues[0]}</p>
                        )}
                        {validation.warnings?.length > 0 && validation.valid && (
                          <p className="text-xs text-yellow-600 mt-1">{validation.warnings[0]}</p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {/* Actions */}
              <div className="flex gap-2 pt-4 border-t">
                {videoDetails?.file_path && (
                  <Button
                    variant="secondary"
                    onClick={() => window.open(`/outputs/${selectedVideo.id}_final.mp4`, '_blank')}
                  >
                    <Download className="h-4 w-4" />
                    Download
                  </Button>
                )}
                <Button
                  variant="danger"
                  onClick={() => handleDelete(selectedVideo.id)}
                >
                  <Trash2 className="h-4 w-4" />
                  Delete
                </Button>
              </div>
            </div>
          </div>
        )}
      </Modal>
    </div>
  )
}
