import { useState, useEffect } from 'react'
import { Youtube, Instagram, Music2, CheckCircle, AlertCircle, XCircle, RefreshCw } from 'lucide-react'
import Card from '../components/Card'
import Button from '../components/Button'
import StatusBadge from '../components/StatusBadge'
import { getAccounts, getPlatformStatus, createAccount, verifyAccount } from '../api'

const PLATFORMS = {
  youtube: { name: 'YouTube', icon: Youtube, color: 'text-red-600', bg: 'bg-red-50' },
  instagram: { name: 'Instagram', icon: Instagram, color: 'text-pink-600', bg: 'bg-pink-50' },
  tiktok: { name: 'TikTok', icon: Music2, color: 'text-gray-800', bg: 'bg-gray-100' },
}

export default function Accounts() {
  const [accounts, setAccounts] = useState([])
  const [platformStatus, setPlatformStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [verifying, setVerifying] = useState(null)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const [accountsRes, statusRes] = await Promise.all([
        getAccounts(),
        getPlatformStatus()
      ])
      setAccounts(accountsRes.data)
      setPlatformStatus(statusRes.data)
    } catch (error) {
      console.error('Failed to load accounts:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleVerify = async (accountId) => {
    setVerifying(accountId)
    try {
      await verifyAccount(accountId)
      loadData()
    } catch (error) {
      console.error('Failed to verify account:', error)
    } finally {
      setVerifying(null)
    }
  }

  if (loading) {
    return <div className="flex items-center justify-center h-64">Loading...</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Platform Accounts</h1>
        <Button variant="secondary" onClick={loadData}>
          <RefreshCw className="h-4 w-4" />
          Refresh
        </Button>
      </div>

      {/* Platform Status Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {platformStatus && Object.entries(platformStatus).map(([platform, status]) => {
          const config = PLATFORMS[platform]
          const Icon = config?.icon || AlertCircle
          
          return (
            <Card key={platform} className="!p-4">
              <div className="flex items-center gap-4">
                <div className={`p-3 rounded-lg ${config?.bg || 'bg-gray-100'}`}>
                  <Icon className={`h-6 w-6 ${config?.color || 'text-gray-600'}`} />
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold text-gray-900">{config?.name || platform}</h3>
                  <p className="text-sm text-gray-500">{status.message}</p>
                </div>
                {status.configured ? (
                  <CheckCircle className="h-6 w-6 text-green-500" />
                ) : (
                  <XCircle className="h-6 w-6 text-gray-300" />
                )}
              </div>
              
              {platform === 'tiktok' && status.configured && !status.verified && (
                <div className="mt-3 p-2 bg-yellow-50 rounded-lg">
                  <p className="text-xs text-yellow-700">
                    <AlertCircle className="h-4 w-4 inline mr-1" />
                    Unverified app - posts will be private until TikTok audit approval
                  </p>
                </div>
              )}
            </Card>
          )
        })}
      </div>

      {/* Setup Instructions */}
      <Card title="Setup Instructions">
        <div className="space-y-6">
          <div>
            <h4 className="font-medium text-gray-900 flex items-center gap-2">
              <Youtube className="h-5 w-5 text-red-600" />
              YouTube Setup
            </h4>
            <ol className="mt-2 text-sm text-gray-600 space-y-1 list-decimal list-inside">
              <li>Go to <a href="https://console.cloud.google.com/" target="_blank" className="text-primary-600 hover:underline">Google Cloud Console</a></li>
              <li>Create a project and enable YouTube Data API v3</li>
              <li>Create OAuth 2.0 credentials (Web application)</li>
              <li>Add credentials to your .env file: YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET</li>
              <li>Complete OAuth flow to get refresh token</li>
            </ol>
          </div>

          <div>
            <h4 className="font-medium text-gray-900 flex items-center gap-2">
              <Instagram className="h-5 w-5 text-pink-600" />
              Instagram Setup
            </h4>
            <ol className="mt-2 text-sm text-gray-600 space-y-1 list-decimal list-inside">
              <li>Go to <a href="https://developers.facebook.com/" target="_blank" className="text-primary-600 hover:underline">Meta for Developers</a></li>
              <li>Create an app with Instagram Graph API access</li>
              <li>Connect your Instagram Business/Creator account</li>
              <li>Generate access token with required permissions</li>
              <li>Add to .env: INSTAGRAM_ACCESS_TOKEN, INSTAGRAM_BUSINESS_ACCOUNT_ID</li>
            </ol>
          </div>

          <div>
            <h4 className="font-medium text-gray-900 flex items-center gap-2">
              <Music2 className="h-5 w-5 text-gray-800" />
              TikTok Setup
            </h4>
            <ol className="mt-2 text-sm text-gray-600 space-y-1 list-decimal list-inside">
              <li>Go to <a href="https://developers.tiktok.com/" target="_blank" className="text-primary-600 hover:underline">TikTok for Developers</a></li>
              <li>Create an app with Content Posting API access</li>
              <li>Complete OAuth flow to get access token</li>
              <li>Add to .env: TIKTOK_CLIENT_KEY, TIKTOK_ACCESS_TOKEN, TIKTOK_OPEN_ID</li>
              <li><strong>Note:</strong> Unverified apps can only post as PRIVATE until you complete audit</li>
            </ol>
            <div className="mt-2 p-3 bg-yellow-50 rounded-lg">
              <p className="text-sm text-yellow-800">
                <strong>Important:</strong> TikTok Content Posting API has strict requirements. 
                Until your app passes TikTok's audit, all posted videos will be set to private/self-only visibility.
                You can still use the "export for manual upload" feature.
              </p>
            </div>
          </div>
        </div>
      </Card>

      {/* Compliance Notes */}
      <Card title="Compliance Notes">
        <div className="prose prose-sm max-w-none">
          <ul className="text-gray-600 space-y-2">
            <li>This tool uses <strong>official APIs only</strong> for publishing content</li>
            <li>No engagement automation (no auto-liking, auto-commenting, or follow/unfollow)</li>
            <li>Content creation and scheduling only - no TOS-violating automation</li>
            <li>You are responsible for ensuring your content complies with each platform's guidelines</li>
            <li>API rate limits and quotas apply based on your developer account tier</li>
          </ul>
        </div>
      </Card>
    </div>
  )
}
