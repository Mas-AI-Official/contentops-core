import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Loader2, CheckCircle2, AlertCircle, Clock } from 'lucide-react'
import { getJobs } from '../api'

export default function ActiveJobsBar() {
    const [activeJobs, setActiveJobs] = useState([])
    const [stats, setStats] = useState({ running: 0, pending: 0, review: 0 })

    useEffect(() => {
        const poll = async () => {
            try {
                // Fetch recent jobs to check status
                const res = await getJobs({ limit: 20 })
                const jobs = res.data || []

                const running = jobs.filter(j => ['queued', 'generating_script', 'generating_audio', 'generating_subtitles', 'rendering', 'publishing'].includes(j.status))
                const pending = jobs.filter(j => j.status === 'pending')
                const review = jobs.filter(j => j.status === 'ready_for_review')

                setActiveJobs(running)
                setStats({
                    running: running.length,
                    pending: pending.length,
                    review: review.length
                })
            } catch (e) {
                console.error("Failed to poll jobs:", e)
            }
        }

        poll()
        const interval = setInterval(poll, 3000) // Poll every 3 seconds for "real-time" feel
        return () => clearInterval(interval)
    }, [])

    if (stats.running === 0 && stats.pending === 0 && stats.review === 0) {
        return null
    }

    return (
        <div className="bg-white border-b border-gray-200 px-6 py-2 flex items-center justify-between text-sm">
            <div className="flex items-center gap-6">
                {stats.running > 0 && (
                    <div className="flex items-center gap-2 text-blue-600 font-medium animate-pulse">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        <span>{stats.running} Job{stats.running > 1 ? 's' : ''} Running</span>
                    </div>
                )}

                {stats.pending > 0 && (
                    <div className="flex items-center gap-2 text-gray-500">
                        <Clock className="h-4 w-4" />
                        <span>{stats.pending} Pending</span>
                    </div>
                )}

                {stats.review > 0 && (
                    <Link to="/queue" className="flex items-center gap-2 text-amber-600 hover:text-amber-700 font-medium">
                        <AlertCircle className="h-4 w-4" />
                        <span>{stats.review} Ready for Review</span>
                    </Link>
                )}
            </div>

            <div className="flex items-center gap-2">
                {activeJobs.length > 0 && (
                    <span className="text-xs text-gray-400">
                        Processing: {activeJobs[0].topic.substring(0, 30)}...
                    </span>
                )}
                <Link to="/queue" className="text-xs text-primary-600 hover:text-primary-700 font-medium ml-2">
                    View Queue →
                </Link>
            </div>
        </div>
    )
}
