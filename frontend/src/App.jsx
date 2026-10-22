import { useState } from 'react'
import { getInterview } from './api'
import { turnsToMessages } from './messages'
import History from './screens/History'
import Home from './screens/Home'
import Interview from './screens/Interview'
import Scorecard from './screens/Scorecard'

// Screens: home -> interview -> scorecard, plus history to revisit past interviews
export default function App() {
  const [screen, setScreen] = useState('home')
  // The interview being shown: { interview_id, topics, question, repoUrl, initialMessages? }
  const [interview, setInterview] = useState(null)
  const [error, setError] = useState('')

  const go = (next) => {
    setError('')
    setScreen(next)
  }

  const goHome = () => {
    setInterview(null)
    go('home')
  }

  const continueInterview = async (interviewId) => {
    try {
      const saved = await getInterview(interviewId)
      setInterview({
        interview_id: interviewId,
        topics: saved.topics,
        repoUrl: saved.repo_url,
        initialMessages: turnsToMessages(saved.turns),
      })
      go('interview')
    } catch (err) {
      setError(err.message)
    }
  }

  const viewScorecard = (interviewId) => {
    setInterview({ interview_id: interviewId })
    go('scorecard')
  }

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-800">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-4 py-4">
          <button onClick={goHome} className="text-xl font-bold tracking-tight">
            Repo<span className="text-orange-400">Grill</span>
          </button>
          <nav className="flex gap-4 text-sm">
            <button onClick={goHome} className={screen === 'home' ? 'text-orange-400' : 'text-slate-400 hover:text-slate-200'}>
              New interview
            </button>
            <button
              onClick={() => go('history')}
              className={screen === 'history' ? 'text-orange-400' : 'text-slate-400 hover:text-slate-200'}
            >
              History
            </button>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-4 py-8">
        {error && <p className="mb-4 rounded-lg bg-red-950 px-4 py-3 text-red-300">{error}</p>}
        {screen === 'home' && (
          <Home
            onStart={(repo, started) => {
              setInterview({ ...started, repoUrl: repo.repo_url })
              go('interview')
            }}
          />
        )}
        {screen === 'interview' && (
          <Interview
            key={interview.interview_id}
            repoUrl={interview.repoUrl}
            interview={interview}
            initialMessages={interview.initialMessages}
            onFinish={() => go('scorecard')}
          />
        )}
        {screen === 'scorecard' && <Scorecard interviewId={interview.interview_id} onRestart={goHome} />}
        {screen === 'history' && (
          <History onContinue={continueInterview} onViewScorecard={viewScorecard} onNew={goHome} />
        )}
      </main>
    </div>
  )
}
