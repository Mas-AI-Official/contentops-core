import { useState, useEffect } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { FlaskConical, Copy, Check, ArrowRight, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'
import Card from '../components/Card'
import Button from '../components/Button'
import { getNiches, getAccounts, getTrendCandidates, generatePromptPack } from '../api'

export default function PromptLab() {
  const [searchParams] = useSearchParams()
  const nicheIdFromUrl = searchParams.get('niche_id')
  const candidateIdFromUrl = searchParams.get('candidate_id')

  const [niches, setNiches] = useState([])
  const [accounts, setAccounts] = useState([])
  const [candidates, setCandidates] = useState([])
  const [selectedNicheId, setSelectedNicheId] = useState('')
  const [selectedAccountId, setSelectedAccountId] = useState('')
  const [selectedCandidateId, setSelectedCandidateId] = useState('')
  const [promptPack, setPromptPack] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [copiedVariant, setCopiedVariant] = useState(null)

  useEffect(() => {
    loadNiches()
    loadAccounts()
  }, [])

  useEffect(() => {
    if (nicheIdFromUrl && niches.length > 0) {
      setSelectedNicheId(nicheIdFromUrl)
    } else if (niches.length > 0 && !selectedNicheId) {
      setSelectedNicheId(String(niches[0].id))
    }
  }, [nicheIdFromUrl, niches])

  useEffect(() => {
    if (candidateIdFromUrl) setSelectedCandidateId(candidateIdFromUrl)
  }, [candidateIdFromUrl])

  useEffect(() => {
    if (selectedNicheId) loadCandidates()
    else setCandidates([])
  }, [selectedNicheId])

  const loadNiches = async () => {
    try {
      const res = await getNiches()
      setNiches(res.data || [])
    } catch (err) {
      console.error(err)
      setError('Failed to load niches')
    }
  }

  const loadAccounts = async () => {
    try {
      const res = await getAccounts()
      setAccounts(res.data || [])
    } catch (err) {
      console.error(err)
    }
  }

  const loadCandidates = async () => {
    if (!selectedNicheId) return
    try {
      const res = await getTrendCandidates(parseInt(selectedNicheId, 10))
      setCandidates(Array.isArray(res.data) ? res.data : [])
    } catch (err) {
      setCandidates([])
    }
  }

  const handleGenerate = async () => {
    if (!selectedNicheId || !selectedAccountId) return
    setLoading(true)
    setError(null)
    setPromptPack(null)
    try {
      const res = await generatePromptPack({
        niche_id: parseInt(selectedNicheId, 10),
        account_id: parseInt(selectedAccountId, 10),
        candidate_id: selectedCandidateId ? parseInt(selectedCandidateId, 10) : null
      })
      setPromptPack(res.data)
    } catch (err) {
      console.error(err)
      setError(err.response?.data?.detail || 'Generate failed')
    } finally {
      setLoading(false)
    }
  }

  const handleCopy = (variant, field, text) => {
    if (typeof navigator?.clipboard?.writeText === 'function') {
      navigator.clipboard.writeText(text)
      setCopiedVariant(`${variant}-${field}`)
      setTimeout(() => setCopiedVariant(null), 2000)
    }
  }

  const navigate = useNavigate()
  const handleUseInGenerator = (variant) => {
    if (!promptPack?.variants?.[variant]) return
    const script = promptPack.variants[variant].script
    const hook = promptPack.variants[variant].hook
    const text = (hook ? `${hook}\n\n` : '') + (script || '')
    localStorage.setItem('promptlab_script', text)
    navigate('/generator')
  }

  const selectedNiche = niches.find(n => String(n.id) === selectedNicheId)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <h1 className="text-2xl font-bold text-gray-900">Prompt Lab</h1>
      </div>

      <Card title="1. Select Niche & Account">
        <p className="text-sm text-gray-500 mb-4">
          Pick a niche and account, optionally choose a trend candidate from Trend Discovery, then generate A/B/C prompt variants.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Niche</label>
            <select
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white text-gray-900"
              value={selectedNicheId}
              onChange={e => setSelectedNicheId(e.target.value)}
            >
              <option value="">Select Niche</option>
              {niches.map(n => (
                <option key={n.id} value={n.id}>{n.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Account</label>
            <select
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white text-gray-900"
              value={selectedAccountId}
              onChange={e => setSelectedAccountId(e.target.value)}
            >
              <option value="">Select Account</option>
              {accounts.map(a => (
                <option key={a.id} value={a.id}>{a.platform} – {a.username || a.name || a.id}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Trend candidate (optional)</label>
            <select
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm bg-white text-gray-900"
              value={selectedCandidateId}
              onChange={e => setSelectedCandidateId(e.target.value)}
            >
              <option value="">None</option>
              {candidates.slice(0, 30).map(c => (
                <option key={c.id} value={c.id}>
                  {c.platform} – {(c.caption || '').slice(0, 40)}…
                </option>
              ))}
            </select>
          </div>
        </div>
        <Button
          onClick={handleGenerate}
          loading={loading}
          disabled={!selectedNicheId || !selectedAccountId || loading}
        >
          <Sparkles className="h-4 w-4 mr-2" />
          {loading ? 'Generating...' : 'Generate Prompt Pack'}
        </Button>
        {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
      </Card>

      {promptPack && promptPack.variants && (
        <Card title="2. Variants (A / B / C)">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {['A', 'B', 'C'].map(variant => {
              const v = promptPack.variants[variant]
              if (!v) return null
              return (
                <div
                  key={variant}
                  className="rounded-xl border border-gray-200 bg-gray-50/50 p-5 space-y-4"
                >
                  <h3 className="font-semibold text-gray-900 flex items-center gap-2">
                    <span className="w-8 h-8 rounded-full bg-primary-100 text-primary-700 flex items-center justify-center text-sm">
                      {variant}
                    </span>
                    Variant {variant}
                  </h3>
                  <div>
                    <label className="text-xs text-gray-500 uppercase">Hook</label>
                    <p className="text-gray-900 text-sm mt-0.5">{v.hook}</p>
                    <button
                      type="button"
                      onClick={() => handleCopy(variant, 'hook', v.hook)}
                      className="mt-1 text-xs text-primary-600 hover:underline flex items-center gap-1"
                    >
                      {copiedVariant === `${variant}-hook` ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                      Copy
                    </button>
                  </div>
                  <div>
                    <label className="text-xs text-gray-500 uppercase">Script</label>
                    <p className="text-gray-700 text-sm mt-0.5 whitespace-pre-wrap line-clamp-6">{v.script}</p>
                    <button
                      type="button"
                      onClick={() => handleCopy(variant, 'script', v.script)}
                      className="mt-1 text-xs text-primary-600 hover:underline flex items-center gap-1"
                    >
                      {copiedVariant === `${variant}-script` ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
                      Copy
                    </button>
                  </div>
                  {v.reasoning && (
                    <div>
                      <label className="text-xs text-gray-500 uppercase">Reasoning</label>
                      <p className="text-gray-500 text-xs italic mt-0.5">{v.reasoning}</p>
                    </div>
                  )}
                  <Button variant="secondary" size="sm" className="w-full" onClick={() => handleUseInGenerator(variant)}>
                    <ArrowRight className="h-4 w-4 mr-1" />
                    Use in Generator
                  </Button>
                </div>
              )
            })}
          </div>
        </Card>
      )}

      {!promptPack && !loading && (selectedNicheId && selectedAccountId) && (
        <Card>
          <p className="text-gray-500 text-center py-6">
            Click &quot;Generate Prompt Pack&quot; to create three variants. You can optionally pick a trend candidate from Trend Discovery first.
          </p>
        </Card>
      )}
    </div>
  )
}
