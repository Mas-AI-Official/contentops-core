import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Overview from './pages/Overview'
import Platforms from './pages/Platforms'
import Niches from './pages/Niches'
import Accounts from './pages/Accounts'
import Generator from './pages/Generator'
import Queue from './pages/Queue'
import Library from './pages/Library'
import Analytics from './pages/Analytics'
import Settings from './pages/Settings'
import Models from './pages/Models'
import Scripts from './pages/Scripts'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Overview />} />
        <Route path="/platforms" element={<Platforms />} />
        <Route path="/niches" element={<Niches />} />
        <Route path="/accounts" element={<Accounts />} />
        <Route path="/generator" element={<Generator />} />
        <Route path="/queue" element={<Queue />} />
        <Route path="/library" element={<Library />} />
        <Route path="/scripts" element={<Scripts />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/models" element={<Models />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </Layout>
  )
}

export default App
