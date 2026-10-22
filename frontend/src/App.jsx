import { useState } from 'react'
import Home from './screens/Home'
import Interview from './screens/Interview'
import Scorecard from './screens/Scorecard'

// The app moves through three screens: home -> interview -> scorecard
export default function App() {
  const [screen, setScreen] = useState('home')
  const [repo, setRepo] = useState(null)
  const [interview, setInterview] = useState(null)

  const restart = () => {
    setRepo(null)
    setInterview(null)
    setScreen('home')
  }

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-800">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-4 py-4">
          <button onClick={restart} className="text-xl font-bold tracking-tight">
            Repo<span className="text-orange-400">Grill</span>
          </button>
          <span className="text-sm text-slate-400">Get interviewed on your own code</span>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-4 py-8">
        {screen === 'home' && (
          <Home
            onStart={(repoInfo, interviewInfo) => {
              setRepo(repoInfo)
              setInterview(interviewInfo)
              setScreen('interview')
            }}
          />
        )}
        {screen === 'interview' && (
          <Interview repo={repo} interview={interview} onFinish={() => setScreen('scorecard')} />
        )}
        {screen === 'scorecard' && <Scorecard interviewId={interview.interview_id} onRestart={restart} />}
      </main>
    </div>
  )
}
