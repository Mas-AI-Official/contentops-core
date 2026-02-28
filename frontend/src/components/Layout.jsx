import { Link, useLocation } from 'react-router-dom'
import ActiveJobsBar from './ActiveJobsBar'
import {
  LayoutDashboard,
  Monitor,
  Tags,
  Users,
  Wand2,
  ListTodo,
  Film,
  FileText,
  BarChart3,
  Settings,
  Factory,
  Box,
  TrendingUp,
  FlaskConical,
  Brain,
  Search
} from 'lucide-react'

const navigation = [
  { name: 'Overview', href: '/', icon: LayoutDashboard },
  { name: 'Platforms', href: '/platforms', icon: Monitor },
  { name: 'Niches', href: '/niches', icon: Tags },
  { name: 'Accounts', href: '/accounts', icon: Users },
  { name: 'Trends', href: '/trends', icon: TrendingUp },
  { name: 'Prompt Lab', href: '/promptlab', icon: FlaskConical },
  { name: 'Research & Scrape', href: '/scrape', icon: Search },
  { name: 'Memory', href: '/memory', icon: Brain },
  { name: 'Generator', href: '/generator', icon: Wand2 },
  { name: 'Queue', href: '/queue', icon: ListTodo },
  { name: 'Library', href: '/library', icon: Film },
  { name: 'Scripts', href: '/scripts', icon: FileText },
  { name: 'Analytics', href: '/analytics', icon: BarChart3 },
  { name: 'Models', href: '/models', icon: Box },
  { name: 'Settings', href: '/settings', icon: Settings },
]



export default function Layout({ children }) {
  const location = useLocation()

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Sidebar */}
      <div className="fixed inset-y-0 left-0 w-64 bg-gray-900">
        <div className="flex h-16 items-center gap-2 px-6 border-b border-gray-800">
          <Factory className="h-8 w-8 text-primary-500" />
          <span className="text-xl font-bold text-white">Content Factory</span>
        </div>
        <nav className="mt-6 px-3">
          {navigation.map((item) => {
            const isActive = location.pathname === item.href
            return (
              <Link
                key={item.name}
                to={item.href}
                className={`flex items-center gap-3 px-3 py-2 rounded-lg mb-1 transition-colors ${isActive
                  ? 'bg-primary-600 text-white'
                  : 'text-gray-400 hover:bg-gray-800 hover:text-white'
                  }`}
              >
                <item.icon className="h-5 w-5" />
                {item.name}
              </Link>
            )
          })}
        </nav>
      </div>

      {/* Main content */}
      <div className="pl-64">
        <ActiveJobsBar />
        <main className="p-8">
          {children}
        </main>
      </div>
    </div>
  )
}
