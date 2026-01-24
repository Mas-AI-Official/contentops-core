import React, { useState, useEffect } from 'react'
import { api } from '../api'

export default function Trends() {
    const [niches, setNiches] = useState([])
    const [selectedNiche, setSelectedNiche] = useState('')
    const [candidates, setCandidates] = useState([])
    const [loading, setLoading] = useState(false)

    useEffect(() => {
        api.get('/niches').then(res => setNiches(res.data))
    }, [])

    const handleScan = async () => {
        if (!selectedNiche) return
        setLoading(true)
        try {
            const res = await api.post('/trends/scan', {
                niche_id: selectedNiche,
                platforms: ['instagram', 'tiktok', 'youtube'],
                limit: 10
            })
            setCandidates(res.data)
        } catch (err) {
            console.error(err)
        }
        setLoading(false)
    }

    return (
        <div className="p-6">
            <h1 className="text-2xl font-bold mb-6">Trend Discovery</h1>

            <div className="flex gap-4 mb-8">
                <select
                    className="bg-gray-800 p-2 rounded text-white border border-gray-700"
                    value={selectedNiche}
                    onChange={e => setSelectedNiche(e.target.value)}
                >
                    <option value="">Select Niche</option>
                    {niches.map(n => (
                        <option key={n.id} value={n.id}>{n.name}</option>
                    ))}
                </select>

                <button
                    className="bg-blue-600 px-4 py-2 rounded text-white hover:bg-blue-700 disabled:opacity-50"
                    onClick={handleScan}
                    disabled={loading || !selectedNiche}
                >
                    {loading ? 'Scanning...' : 'Scan Trends'}
                </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {candidates.map(c => (
                    <div key={c.id} className="bg-gray-800 p-4 rounded-lg border border-gray-700">
                        <div className="flex justify-between items-start mb-2">
                            <span className="bg-gray-700 text-xs px-2 py-1 rounded uppercase text-gray-300">{c.platform}</span>
                            <span className="text-xs text-gray-400">{new Date(c.discovered_at).toLocaleDateString()}</span>
                        </div>
                        <p className="font-medium mb-2 line-clamp-2 text-white">{c.caption}</p>
                        <div className="flex gap-2 text-sm text-gray-400 mb-4">
                            <span>{c.metrics?.views || 0} views</span>
                            <span>{c.metrics?.likes || 0} likes</span>
                        </div>
                        <a
                            href={c.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-400 text-sm hover:underline"
                        >
                            View Source
                        </a>
                    </div>
                ))}
            </div>
        </div>
    )
}
