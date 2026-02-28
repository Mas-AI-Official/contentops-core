import { useState, useEffect } from 'react'
import { Search, Plus, RefreshCw, Link, Database, Activity, Dna, Sparkles, Copy, ArrowRight, Rss, Youtube, TrendingUp, Zap, MousePointer2 } from 'lucide-react'
import Card from '../components/Card'
import Button from '../components/Button'
import StatusBadge from '../components/StatusBadge'
import api, { getNiches, scrapeNiche, getNicheTopics, markTopicUsed } from '../api'
import { useNavigate } from 'react-router-dom'

export default function ScraperDashboard() {
    const [activeTab, setActiveTab] = useState('topics')
    const [niches, setNiches] = useState([])
    const [selectedNiche, setSelectedNiche] = useState(null)
    const [loading, setLoading] = useState({ niches: true, topics: false, scraping: false })

    useEffect(() => {
        loadNiches()
    }, [])

    const loadNiches = async () => {
        try {
            const res = await getNiches()
            setNiches(res.data)
            if (res.data.length > 0) {
                setSelectedNiche(res.data[0])
            }
        } catch (error) {
            console.error('Failed to load niches:', error)
        } finally {
            setLoading(prev => ({ ...prev, niches: false }))
        }
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <h1 className="text-2xl font-bold text-gray-900">Research & Scraping</h1>
                <div className="flex gap-2">
                    <Button
                        variant={activeTab === 'topics' ? 'primary' : 'secondary'}
                        onClick={() => setActiveTab('topics')}
                    >
                        <TrendingUp className="h-4 w-4 mr-2" />
                        Niche Topics
                    </Button>
                    <Button
                        variant={activeTab === 'ingest' ? 'primary' : 'secondary'}
                        onClick={() => setActiveTab('ingest')}
                    >
                        <Plus className="h-4 w-4 mr-2" />
                        Manual Ingest
                    </Button>
                    <Button
                        variant={activeTab === 'viral' ? 'primary' : 'secondary'}
                        onClick={() => setActiveTab('viral')}
                    >
                        <Dna className="h-4 w-4 mr-2" />
                        Viral DNA
                    </Button>
                </div>
            </div>

            {activeTab === 'topics' && (
                <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
                    {/* Niche Sidebar */}
                    <div className="lg:col-span-1 space-y-4">
                        <Card title="1. Select Niche">
                            <div className="space-y-2">
                                {niches.map(niche => (
                                    <button
                                        key={niche.id}
                                        onClick={() => setSelectedNiche(niche)}
                                        className={`w-full p-3 rounded-lg text-left transition-all ${selectedNiche?.id === niche.id
                                            ? 'bg-primary-50 border-primary-500 border-2 shadow-sm'
                                            : 'bg-white border-gray-200 border hover:border-primary-300'
                                            }`}
                                    >
                                        <p className="font-bold text-gray-900 text-sm">{niche.name}</p>
                                        <p className="text-[10px] text-gray-500 uppercase tracking-tighter">{niche.slug}</p>
                                    </button>
                                ))}
                            </div>
                        </Card>
                    </div>

                    {/* Topics List */}
                    <div className="lg:col-span-3 space-y-6">
                        <TopicsTab niche={selectedNiche} />
                    </div>
                </div>
            )}

            {activeTab === 'ingest' && <IngestTab />}
            {activeTab === 'viral' && <ViralAnalysisTab />}
        </div>
    )
}

function TopicsTab({ niche }) {
    const [topics, setTopics] = useState([])
    const [loading, setLoading] = useState(false)
    const [scraping, setScraping] = useState(false)
    const navigate = useNavigate()

    useEffect(() => {
        if (niche) {
            loadTopics()
        }
    }, [niche])

    const loadTopics = async () => {
        setLoading(true)
        try {
            const res = await getNicheTopics(niche.slug || niche.id, true)
            setTopics(res.data.topics || [])
        } catch (error) {
            console.error('Failed to load topics:', error)
        } finally {
            setLoading(false)
        }
    }

    const handleScrapeNow = async () => {
        if (!niche) return
        setScraping(true)
        try {
            await scrapeNiche(niche.slug || niche.id)
            await loadTopics()
        } catch (error) {
            alert('Scrape failed: ' + (error.response?.data?.detail || error.message))
        } finally {
            setScraping(false)
        }
    }

    const handleUseTopic = async (topic) => {
        const slug = niche.slug || niche.id
        const topicId = topic.id ?? topic.title
        try {
            await markTopicUsed(slug, topicId)
        } catch (error) {
            console.warn('Could not mark topic as used:', error)
        }
        localStorage.setItem('picked_topic', JSON.stringify({
            title: topic.title,
            niche_id: niche.id
        }))
        navigate('/generator')
    }

    if (!niche) return <div className="p-8 text-center text-gray-500">Select a niche to see trends.</div>

    return (
        <Card>
            <div className="flex items-center justify-between mb-6">
                <div>
                    <h2 className="text-xl font-bold text-gray-900">Trending in {niche.name}</h2>
                    <p className="text-sm text-gray-500">Live topics from across RSS, YouTube & Web</p>
                </div>
                <Button onClick={handleScrapeNow} loading={scraping} variant="secondary">
                    <RefreshCw className={`h-4 w-4 mr-2 ${scraping ? 'animate-spin' : ''}`} />
                    Refresh Feed
                </Button>
            </div>

            {loading ? (
                <div className="flex flex-col items-center justify-center py-20">
                    <RefreshCw className="h-10 w-10 text-primary-500 animate-spin mb-4" />
                    <p className="text-gray-500">Scanning for viral opportunities...</p>
                </div>
            ) : topics.length === 0 ? (
                <div className="text-center py-20 bg-gray-50 rounded-xl border-2 border-dashed border-gray-200">
                    <Database className="h-12 w-12 text-gray-300 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-gray-900">No topics found yet</h3>
                    <p className="text-gray-500 mb-6">Hit refresh or add more sources in settings.</p>
                    <Button onClick={handleScrapeNow} loading={scraping}>
                        Trigger First Scrape
                    </Button>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {topics.map((topic, i) => (
                        <div key={i} className="group p-5 bg-white border border-gray-100 rounded-xl shadow-sm hover:border-primary-500 hover:shadow-md transition-all relative overflow-hidden">
                            <div className="absolute top-0 right-0 p-2 opacity-5 group-hover:opacity-10 transition-opacity">
                                <Zap className="h-16 w-16 text-primary-900" />
                            </div>

                            <div className="flex items-start justify-between gap-4 mb-3">
                                <span className="p-1 px-2 bg-primary-100 text-primary-700 text-[10px] font-bold rounded uppercase">
                                    {topic.source || 'Trending'}
                                </span>
                                <span className="text-[10px] text-gray-400">
                                    {new Date(topic.published).toLocaleDateString()}
                                </span>
                            </div>

                            <h3 className="font-bold text-gray-900 mb-4 line-clamp-2 min-h-[3rem]">
                                {topic.title}
                            </h3>

                            <div className="flex gap-2">
                                <Button
                                    size="sm"
                                    variant="primary"
                                    className="flex-1 rounded-lg"
                                    onClick={() => handleUseTopic(topic)}
                                >
                                    <MousePointer2 className="h-3 w-3 mr-2" />
                                    Create Video
                                </Button>
                                <a
                                    href={topic.url}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="p-2 bg-gray-50 text-gray-500 hover:text-primary-600 rounded-lg border border-gray-100"
                                >
                                    <ArrowRight className="h-4 w-4" />
                                </a>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </Card>
    )
}

function IngestTab() {
    const [url, setUrl] = useState('')
    const [loading, setLoading] = useState(false)
    const [result, setResult] = useState(null)
    const [error, setError] = useState(null)

    const handleIngest = async (e) => {
        e.preventDefault()
        if (!url) return

        setLoading(true)
        setError(null)
        setResult(null)

        try {
            const res = await api.post('/scraper/ingest', null, {
                params: { url, platform: 'web' }
            })
            setResult(res.data)
            setUrl('')
        } catch (err) {
            setError(err.response?.data?.detail || 'Failed to ingest URL')
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card title="Manual Content Ingest">
                <form onSubmit={handleIngest} className="space-y-4">
                    <p className="text-sm text-gray-500">Paste a URL from TikTok, YouTube, or a Web Article to ingest it into the Viral DNA lab.</p>
                    <div>
                        <div className="flex gap-2">
                            <div className="relative flex-1">
                                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                    <Link className="h-5 w-5 text-gray-400" />
                                </div>
                                <input
                                    type="url"
                                    value={url}
                                    onChange={(e) => setUrl(e.target.value)}
                                    className="block w-full pl-10 pr-3 py-2.5 border border-gray-300 rounded-xl focus:ring-primary-500 focus:border-primary-500"
                                    placeholder="https://tiktok.com/@user/video/..."
                                />
                            </div>
                            <Button type="submit" disabled={loading}>
                                {loading ? <RefreshCw className="h-4 w-4 animate-spin" /> : 'Ingest'}
                            </Button>
                        </div>
                    </div>

                    {error && (
                        <div className="p-3 bg-red-50 text-red-700 rounded-lg text-sm">
                            {error}
                        </div>
                    )}

                    {result && (
                        <div className="p-4 bg-green-50 border border-green-200 rounded-xl">
                            <div className="flex items-center gap-2 text-green-800 font-medium mb-1">
                                <Activity className="h-4 w-4" />
                                Ingested Successfully
                            </div>
                            <p className="text-sm text-green-700">
                                ID: {result.id} • Status: {result.status}
                            </p>
                            <Button size="sm" variant="secondary" className="mt-2 w-full">View in Viral Lab</Button>
                        </div>
                    )}
                </form>
            </Card>

            <Card title="Global Sources">
                <div className="space-y-4">
                    <div className="flex items-center justify-between p-3 bg-gray-50 rounded-xl border border-gray-100">
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-red-100 rounded-lg">
                                <Youtube className="h-5 w-5 text-red-600" />
                            </div>
                            <div>
                                <p className="font-bold text-gray-900 text-sm">YouTube Trending</p>
                                <p className="text-[10px] text-gray-500 uppercase">Worldwide Data</p>
                            </div>
                        </div>
                        <StatusBadge status="active" />
                    </div>
                    <div className="flex items-center justify-between p-3 bg-gray-50 rounded-xl border border-gray-100">
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-orange-100 rounded-lg">
                                <Rss className="h-5 w-5 text-orange-500" />
                            </div>
                            <div>
                                <p className="font-bold text-gray-900 text-sm">Global RSS Feed</p>
                                <p className="text-[10px] text-gray-500 uppercase">Multilingual Support</p>
                            </div>
                        </div>
                        <StatusBadge status="active" />
                    </div>
                </div>
            </Card>
        </div>
    )
}

function ViralAnalysisTab() {
    const [dnaItems, setDnaItems] = useState([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        loadDna()
    }, [])

    const loadDna = async () => {
        try {
            const res = await api.get('/scraper/viral-dna')
            setDnaItems(res.data)
        } catch (error) {
            console.error(error)
        } finally {
            setLoading(false)
        }
    }

    if (loading) return <div>Loading...</div>

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {dnaItems.map((dna) => (
                <Card key={dna.id} className="relative overflow-hidden group">
                    <div className="absolute top-0 right-0 p-2 opacity-5">
                        <Dna className="h-24 w-24" />
                    </div>

                    <div className="relative z-10">
                        <div className="flex items-center gap-2 mb-4">
                            <div className="p-2 bg-amber-50 rounded-lg">
                                <Sparkles className="h-5 w-5 text-amber-500" />
                            </div>
                            <h3 className="font-bold text-gray-900">Viral Pattern #{dna.id}</h3>
                        </div>

                        <div className="space-y-4">
                            <div>
                                <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">Hook Strategy</p>
                                <p className="text-gray-900 font-bold">{dna.hook_type}</p>
                            </div>

                            <div>
                                <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-1">Virality Potential</p>
                                <div className="flex items-center gap-2">
                                    <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                                        <div
                                            className="h-full bg-primary-500"
                                            style={{ width: `${dna.pacing_score * 10}%` }}
                                        />
                                    </div>
                                    <span className="text-xs font-bold text-gray-700">{dna.pacing_score}/10</span>
                                </div>
                            </div>

                            <div>
                                <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-1">Drivers</p>
                                <div className="flex flex-wrap gap-1 mt-1">
                                    {dna.emotional_triggers.map((trigger, i) => (
                                        <span key={i} className="px-2 py-0.5 bg-purple-50 text-purple-700 rounded text-[10px] font-medium">
                                            {trigger}
                                        </span>
                                    ))}
                                </div>
                            </div>

                            <Button variant="secondary" size="sm" className="w-full mt-2 rounded-lg">
                                <Copy className="h-3 w-3 mr-2" />
                                Apply to Generator
                            </Button>
                        </div>
                    </div>
                </Card>
            ))}
            {dnaItems.length === 0 && (
                <div className="col-span-full py-20 text-center bg-white rounded-xl border border-gray-100 italic text-gray-400">
                    No viral patterns analyzed yet. Ingest content to begin.
                </div>
            )}
        </div>
    )
}
