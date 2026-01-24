import React, { useState, useEffect } from 'react'
import { api } from '../api'

export default function PromptLab() {
    const [niches, setNiches] = useState([])
    const [accounts, setAccounts] = useState([])
    const [selectedNiche, setSelectedNiche] = useState('')
    const [selectedAccount, setSelectedAccount] = useState('')
    const [promptPack, setPromptPack] = useState(null)
    const [loading, setLoading] = useState(false)

    useEffect(() => {
        api.get('/niches').then(res => setNiches(res.data))
        api.get('/accounts').then(res => setAccounts(res.data))
    }, [])

    const handleGenerate = async () => {
        if (!selectedNiche || !selectedAccount) return
        setLoading(true)
        try {
            const res = await api.post('/promptpack/generate', {
                niche_id: selectedNiche,
                account_id: selectedAccount
            })
            setPromptPack(res.data)
        } catch (err) {
            console.error(err)
        }
        setLoading(false)
    }

    return (
        <div className="p-6">
            <h1 className="text-2xl font-bold mb-6">Prompt Lab</h1>

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

                <select
                    className="bg-gray-800 p-2 rounded text-white border border-gray-700"
                    value={selectedAccount}
                    onChange={e => setSelectedAccount(e.target.value)}
                >
                    <option value="">Select Account</option>
                    {accounts.map(a => (
                        <option key={a.id} value={a.id}>{a.platform} - {a.username}</option>
                    ))}
                </select>

                <button
                    className="bg-purple-600 px-4 py-2 rounded text-white hover:bg-purple-700 disabled:opacity-50"
                    onClick={handleGenerate}
                    disabled={loading || !selectedNiche || !selectedAccount}
                >
                    {loading ? 'Generating...' : 'Generate Prompt Pack'}
                </button>
            </div>

            {promptPack && (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {['A', 'B', 'C'].map(variant => (
                        <div key={variant} className="bg-gray-800 p-6 rounded-lg border border-gray-700">
                            <h3 className="text-xl font-bold mb-4 text-purple-400">Variant {variant}</h3>
                            <div className="space-y-4">
                                <div>
                                    <label className="text-xs text-gray-500 uppercase">Hook</label>
                                    <p className="text-white">{promptPack.variants[variant].hook}</p>
                                </div>
                                <div>
                                    <label className="text-xs text-gray-500 uppercase">Script</label>
                                    <p className="text-gray-300 text-sm whitespace-pre-wrap">{promptPack.variants[variant].script}</p>
                                </div>
                                <div>
                                    <label className="text-xs text-gray-500 uppercase">Reasoning</label>
                                    <p className="text-gray-400 text-xs italic">{promptPack.variants[variant].reasoning}</p>
                                </div>
                                <button className="w-full bg-gray-700 hover:bg-gray-600 py-2 rounded text-sm mt-4">
                                    Use This Variant
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    )
}
