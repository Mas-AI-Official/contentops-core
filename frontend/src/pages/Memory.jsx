import React, { useState, useEffect } from 'react'
import { api } from '../api'
import Card from '../components/Card'

export default function Memory() {
    const [history, setHistory] = useState([])

    useEffect(() => {
        api.get('/memory/history').then(res => setHistory(res.data))
    }, [])

    return (
        <div className="p-6 space-y-6">
            <h1 className="text-2xl font-bold text-gray-900">Memory Index</h1>

            <Card title="What is Memory?">
                <p className="text-gray-700 text-sm mb-2">
                    <strong>Memory</strong> helps avoid posting the same or very similar content twice. When you generate prompt packs (e.g. in Prompt Lab), the system stores an <em>embedding</em> of the script per account and niche. Before publishing, it can check new content against this index: if something is too similar to what you already used, it’s treated as a duplicate.
                </p>
                <p className="text-gray-600 text-sm">
                    The table below lists recent memory entries (niche, fingerprint, date). Duplicate checks use these embeddings so you don’t accidentally repeat the same idea across videos.
                </p>
            </Card>

            <div className="bg-gray-800 rounded-lg overflow-hidden border border-gray-700">
                <table className="w-full text-left">
                    <thead className="bg-gray-900 text-gray-400 text-xs uppercase">
                        <tr>
                            <th className="p-4">ID</th>
                            <th className="p-4">Niche</th>
                            <th className="p-4">Fingerprint</th>
                            <th className="p-4">Created At</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-700">
                        {history.map(item => (
                            <tr key={item.id} className="hover:bg-gray-750">
                                <td className="p-4 text-gray-300">#{item.id}</td>
                                <td className="p-4 text-gray-300">{item.niche_id}</td>
                                <td className="p-4 font-mono text-xs text-gray-500">{item.fingerprint}</td>
                                <td className="p-4 text-gray-400">{new Date(item.created_at).toLocaleString()}</td>
                            </tr>
                        ))}
                        {history.length === 0 && (
                            <tr>
                                <td colSpan="4" className="p-8 text-center text-gray-500">No memory records found</td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    )
}
