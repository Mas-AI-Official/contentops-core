import { useState, useEffect } from 'react'
import { Dna, Sparkles, Copy, ArrowRight } from 'lucide-react'
import Card from '../components/Card'
import Button from '../components/Button'
import api from '../api'

export default function ViralLab() {
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
            console.error('Failed to load viral DNA:', error)
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900">Viral Lab</h1>
                    <p className="text-gray-500">Analyze and replicate viral patterns</p>
                </div>
            </div>

            {loading ? (
                <div className="text-center py-12">Loading...</div>
            ) : dnaItems.length === 0 ? (
                <Card>
                    <div className="text-center py-12 text-gray-500">
                        No viral patterns analyzed yet. Scrape some content first.
                    </div>
                </Card>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {dnaItems.map((item) => (
                        <Card key={item.id} className="relative overflow-hidden">
                            <div className="absolute top-0 right-0 p-4 opacity-10">
                                <Dna className="h-24 w-24" />
                            </div>
                            <div className="relative z-10">
                                <div className="flex justify-between items-start mb-4">
                                    <div>
                                        <h3 className="text-lg font-bold text-gray-900">Viral Pattern #{item.id}</h3>
                                        <p className="text-sm text-gray-500">Score: {item.pacing_score ? Math.round(item.pacing_score * 10) : 'N/A'}/100</p>
                                    </div>
                                    <div className="p-2 bg-primary-50 rounded-lg text-primary-600">
                                        <Sparkles className="h-5 w-5" />
                                    </div>
                                </div>

                                <div className="space-y-2 mb-6">
                                    <div className="flex justify-between text-sm">
                                        <span className="text-gray-500">Hook Type</span>
                                        <span className="font-medium">{item.hook_type || 'Unknown'}</span>
                                    </div>
                                    <div className="flex justify-between text-sm">
                                        <span className="text-gray-500">Pacing Score</span>
                                        <span className="font-medium">{item.pacing_score || 0}/10</span>
                                    </div>
                                    <div className="flex justify-between text-sm">
                                        <span className="text-gray-500">Triggers</span>
                                        <div className="flex gap-1 flex-wrap justify-end">
                                            {item.emotional_triggers && item.emotional_triggers.map(t => (
                                                <span key={t} className="px-2 py-0.5 bg-gray-100 rounded text-xs">{t}</span>
                                            ))}
                                        </div>
                                    </div>
                                </div>

                                <div className="flex gap-2">
                                    <Button className="flex-1" icon={Copy}>Replicate</Button>
                                    <Button variant="secondary" icon={ArrowRight}>View Details</Button>
                                </div>
                            </div>
                        </Card>
                    ))}
                </div>
            )}
        </div>
    )
}
