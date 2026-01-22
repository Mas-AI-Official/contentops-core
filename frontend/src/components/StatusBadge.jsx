const statusColors = {
  // Job statuses
  pending: 'bg-gray-100 text-gray-700',
  queued: 'bg-blue-100 text-blue-700',
  generating_script: 'bg-yellow-100 text-yellow-700',
  generating_audio: 'bg-yellow-100 text-yellow-700',
  generating_subtitles: 'bg-yellow-100 text-yellow-700',
  rendering: 'bg-orange-100 text-orange-700',
  ready_for_review: 'bg-purple-100 text-purple-700',
  approved: 'bg-indigo-100 text-indigo-700',
  publishing: 'bg-cyan-100 text-cyan-700',
  published: 'bg-green-100 text-green-700',
  failed: 'bg-red-100 text-red-700',
  cancelled: 'bg-gray-100 text-gray-500',
  
  // Account statuses
  connected: 'bg-green-100 text-green-700',
  missing_config: 'bg-yellow-100 text-yellow-700',
  expired: 'bg-orange-100 text-orange-700',
  error: 'bg-red-100 text-red-700',
  
  // Publish statuses
  success: 'bg-green-100 text-green-700',
  private: 'bg-yellow-100 text-yellow-700',
  manual_required: 'bg-blue-100 text-blue-700',
}

export default function StatusBadge({ status }) {
  const colorClass = statusColors[status] || 'bg-gray-100 text-gray-700'
  
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${colorClass}`}>
      {status.replace(/_/g, ' ')}
    </span>
  )
}
