import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Niches
export const getNiches = () => api.get('/niches/')
export const getNiche = (id) => api.get(`/niches/${id}`)
export const createNiche = (data) => api.post('/niches/', data)
export const updateNiche = (id, data) => api.patch(`/niches/${id}`, data)
export const deleteNiche = (id) => api.delete(`/niches/${id}`)
export const generateTopics = (nicheId, count = 5) => api.post(`/niches/${nicheId}/generate-topics?count=${count}`)

// Accounts
export const getAccounts = () => api.get('/accounts/')
export const getPlatformStatus = () => api.get('/accounts/status')
export const createAccount = (data) => api.post('/accounts/', data)
export const verifyAccount = (id) => api.post(`/accounts/${id}/verify`)

// Jobs
export const getJobs = (params) => api.get('/jobs/', { params })
export const getTodaysJobs = () => api.get('/jobs/today')
export const getJob = (id) => api.get(`/jobs/${id}`)
export const createJob = (data, runImmediately = false) => 
  api.post(`/jobs/?run_immediately=${runImmediately}`, data)
export const runJob = (id) => api.post(`/jobs/${id}/run`)
export const retryJob = (id) => api.post(`/jobs/${id}/retry`)
export const cancelJob = (id) => api.post(`/jobs/${id}/cancel`)
export const approveJob = (id, publish = true) => api.post(`/jobs/${id}/approve?publish=${publish}`)
export const getJobLogs = (id) => api.get(`/jobs/${id}/logs`)

// Videos
export const getVideos = (params) => api.get('/videos/', { params })
export const getVideo = (id) => api.get(`/videos/${id}`)
export const getVideoPublishes = (id) => api.get(`/videos/${id}/publishes`)
export const getVideoMetadata = (id) => api.get(`/videos/${id}/metadata`)
export const deleteVideo = (id, deleteFiles = false) => 
  api.delete(`/videos/${id}?delete_files=${deleteFiles}`)

// Generator
export const generateTopic = (nicheId) => api.post(`/generator/topic?niche_id=${nicheId}`)
export const generateScript = (data) => api.post('/generator/script', data)
export const generateVideo = (data) => api.post('/generator/video', data)
export const getGenerationStatus = (jobId) => api.get(`/generator/status/${jobId}`)
export const approveAndPublish = (jobId, platforms) => 
  api.post(`/generator/approve/${jobId}`, { platforms })
export const getNicheAssets = (nicheId) => api.get(`/generator/assets/${nicheId}`)

// Analytics
export const getAnalyticsSummary = (nicheId = null) => 
  api.get('/analytics/summary', { params: { niche_id: nicheId } })
export const getAnalyticsTrends = (days = 30, nicheId = null) => 
  api.get('/analytics/trends', { params: { days, niche_id: nicheId } })
export const getTopVideos = (limit = 10) => api.get(`/analytics/top-videos?limit=${limit}`)
export const getUnderperformers = (limit = 10) => api.get(`/analytics/underperformers?limit=${limit}`)
export const getAnalyticsByNiche = () => api.get('/analytics/by-niche')
export const getAnalyticsByPlatform = () => api.get('/analytics/by-platform')
export const refreshAnalytics = () => api.post('/analytics/refresh')
export const getVideoAnalytics = (videoId) => api.get(`/analytics/video/${videoId}`)

// Settings
export const getSettings = () => api.get('/settings/')
export const getPaths = () => api.get('/settings/paths')
export const checkPaths = () => api.get('/settings/paths/check')
export const checkServices = () => api.get('/settings/services/status')
export const getEnvTemplate = () => api.get('/settings/env-template')

// Models
export const getModels = () => api.get('/models/')
export const getAvailableModels = () => api.get('/models/available')
export const getCurrentModels = () => api.get('/models/current')
export const pullModel = (modelName) => api.post('/models/pull', { model_name: modelName })
export const getPullStatus = (modelName) => api.get(`/models/pull/${modelName}/status`)
export const deleteModel = (modelName) => api.delete(`/models/${encodeURIComponent(modelName)}`)
export const testModel = (modelName) => api.post(`/models/test/${encodeURIComponent(modelName)}`)

// Scripts
export const getScripts = (params) => api.get('/scripts/', { params })
export const getScriptsStats = () => api.get('/scripts/stats')
export const getScriptByPath = (path) => api.get('/scripts/by-path', { params: { path } })
export const downloadScript = (jobId, format) => api.get(`/scripts/download/${jobId}`, { 
  params: { format }, 
  responseType: 'blob' 
})
export const getScriptDates = () => api.get('/scripts/dates')
export const getScriptNiches = () => api.get('/scripts/niches')

// Export
export const getPlatformConfigs = () => api.get('/export/platforms')
export const validateVideoForPlatforms = (videoId) => api.get(`/export/validate/${videoId}`)
export const optimizeForPlatform = (videoId, platform) => api.post(`/export/optimize/${videoId}`, null, {
  params: { platform }
})
export const getExportDownloads = (videoId) => api.get(`/export/downloads/${videoId}`)

export default api
