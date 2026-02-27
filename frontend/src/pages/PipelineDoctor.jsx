import { useState, useEffect } from 'react'
import { Activity, CheckCircle, XCircle, RefreshCw, AlertTriangle, ShieldAlert, Wrench } from 'lucide-react'
import Card from '../components/Card'
import Button from '../components/Button'
import StatusBadge from '../components/StatusBadge'
import api from '../api'

export default function PipelineDoctor() {
    const [health, setHealth] = useState(null)
    const [loading, setLoading] = useState(true)
    const [fixing, setFixing] = useState(false)
    const [error, setError] = useState(null)

    const fetchHealth = async () => {
        setLoading(true)
        setError(null)
        try {
            const response = await api.get('/diagnostics/pipeline')
            setHealth(response.data)
        } catch (err) {
            setError('Failed to fetch pipeline health. Backend might be down.')
            console.error(err)
        } finally {
            setLoading(false)
        }
    }

    const runFixes = async () => {
        setFixing(true)
        try {
            await api.post('/diagnostics/fix')
            await fetchHealth()
        } catch (err) {
            console.error(err)
        } finally {
            setFixing(false)
        }
    }

    useEffect(() => {
        fetchHealth()
    }, [])

    if (loading && !health) {
        return (
            <div className="flex items-center justify-center h-96">
                <RefreshCw className="h-8 w-8 animate-spin text-primary-500" />
            </div>
        )
    }

    if (error) {
        return (
            <div className="p-8">
                <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-center gap-3 text-red-700">
                    <XCircle className="h-6 w-6" />
                    <p>{error}</p>
                    <Button onClick={fetchHealth} variant="outline" size="sm" className="ml-auto">
                        Retry
                    </Button>
                </div>
            </div>
        )
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900">Pipeline Doctor</h1>
                    <p className="text-gray-500">System health and diagnostics</p>
                </div>
                <div className="flex gap-2">
                    <Button onClick={runFixes} variant="secondary" icon={Wrench} loading={fixing}>
                        Auto-Fix Issues
                    </Button>
                    <Button onClick={fetchHealth} icon={RefreshCw} loading={loading}>
                        Run Diagnostics
                    </Button>
                </div>
            </div>

            {/* Overall Health Score */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <Card className="p-6 flex items-center gap-4">
                    <div className={`p-3 rounded-full ${health.health_score === 100 ? 'bg-green-100 text-green-600' : health.health_score > 50 ? 'bg-yellow-100 text-yellow-600' : 'bg-red-100 text-red-600'}`}>
                        <Activity className="h-8 w-8" />
                    </div>
                    <div>
                        <p className="text-sm text-gray-500 font-medium">Health Score</p>
                        <p className="text-3xl font-bold">{health.health_score}%</p>
                    </div>
                </Card>

                <Card className="p-6 flex items-center gap-4">
                    <div className={`p-3 rounded-full ${health.blocking_count === 0 ? 'bg-green-100 text-green-600' : 'bg-red-100 text-red-600'}`}>
                        <XCircle className="h-8 w-8" />
                    </div>
                    <div>
                        <p className="text-sm text-gray-500 font-medium">Blocking Issues</p>
                        <p className="text-3xl font-bold">{health.blocking_count}</p>
                    </div>
                </Card>

                <Card className="p-6 flex items-center gap-4">
                    <div className={`p-3 rounded-full ${health.warning_count === 0 ? 'bg-green-100 text-green-600' : 'bg-yellow-100 text-yellow-600'}`}>
                        <AlertTriangle className="h-8 w-8" />
                    </div>
                    <div>
                        <p className="text-sm text-gray-500 font-medium">Warnings</p>
                        <p className="text-3xl font-bold">{health.warning_count}</p>
                    </div>
                </Card>
            </div>

            {/* Detailed Checks */}
            <Card title="Diagnostic Checks">
                <div className="divide-y divide-gray-100">
                    {health.checks.map((check) => (
                        <div key={check.name} className="p-4 flex items-start justify-between hover:bg-gray-50 transition-colors">
                            <div className="flex gap-3">
                                {check.status === 'ok' ? (
                                    <CheckCircle className="h-5 w-5 text-green-500 mt-0.5" />
                                ) : check.severity === 'blocking' ? (
                                    <XCircle className="h-5 w-5 text-red-500 mt-0.5" />
                                ) : (
                                    <AlertTriangle className="h-5 w-5 text-yellow-500 mt-0.5" />
                                )}
                                <div>
                                    <div className="flex items-center gap-2">
                                        <p className="font-medium text-gray-900 capitalize">{check.name.replace('_', ' ')}</p>
                                        {check.severity === 'blocking' && check.status !== 'ok' && (
                                            <span className="px-2 py-0.5 rounded-full bg-red-100 text-red-700 text-xs font-medium">
                                                Blocking
                                            </span>
                                        )}
                                    </div>
                                    <p className="text-sm text-gray-500">{check.message}</p>

                                    {check.status !== 'ok' && check.fix_steps && (
                                        <div className="mt-2 p-3 bg-gray-50 rounded border border-gray-200 text-sm">
                                            <p className="font-medium text-gray-700 mb-1">How to fix:</p>
                                            <pre className="whitespace-pre-wrap text-gray-600 font-sans">{check.fix_steps}</pre>

                                            {check.links && check.links.length > 0 && (
                                                <div className="mt-2 flex gap-2">
                                                    {check.links.map((link, i) => (
                                                        <a
                                                            key={i}
                                                            href={link}
                                                            target="_blank"
                                                            rel="noopener noreferrer"
                                                            className="text-primary-600 hover:underline"
                                                        >
                                                            Download / Guide
                                                        </a>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    )}

                                    {check.last_checked && (
                                        <p className="text-xs text-gray-400 mt-1">
                                            Checked: {new Date(check.last_checked).toLocaleTimeString()}
                                        </p>
                                    )}
                                </div>
                            </div>
                            <StatusBadge status={check.status === 'ok' ? 'completed' : check.status === 'warning' ? 'pending' : 'failed'} />
                        </div>
                    ))}
                </div>
            </Card>
        </div>
    )
}
