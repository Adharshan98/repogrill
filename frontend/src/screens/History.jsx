import { useEffect, useState } from 'react'
import { listInterviews } from '../api'
import ScoreBadge from '../components/ScoreBadge'

export default function History({ onContinue, onViewScorecard, onNew }) {
  const [items, setItems] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    listInterviews().then(setItems).catch((err) => setError(err.message))
  }, [])

  if (error) return <p className="rounded-lg bg-red-950 px-4 py-3 text-red-300">{error}</p>
  if (!items) return <p className="animate-pulse text-slate-400">Loading your interviews...</p>

  if (items.length === 0) {
    return (
      <div className="pt-10 text-center">
        <p className="text-slate-400">No interviews yet.</p>
        <button onClick={onNew} className="mt-4 rounded-lg bg-orange-500 px-6 py-3 font-semibold text-slate-950">
          Start your first one
        </button>
      </div>
    )
  }

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold">Past interviews</h1>
      <div className="flex flex-col gap-3">
        {items.map((item) => (
          <div key={item.interview_id} className="flex items-center gap-4 rounded-lg border border-slate-800 p-4">
            {item.average_score === null ? (
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-slate-800 text-slate-500">
                –
              </div>
            ) : (
              <ScoreBadge score={item.average_score} />
            )}
            <div className="min-w-0 flex-1">
              <p className="truncate font-medium">{item.repo_url.replace('https://github.com/', '')}</p>
              <p className="text-sm text-slate-400">
                {new Date(item.created_at).toLocaleString()} · {item.questions_answered} answered
              </p>
            </div>
            {item.done ? (
              <button
                onClick={() => onViewScorecard(item.interview_id)}
                className="rounded-lg border border-slate-700 px-4 py-2 text-sm hover:border-orange-400"
              >
                Scorecard
              </button>
            ) : (
              <button
                onClick={() => onContinue(item.interview_id)}
                className="rounded-lg bg-orange-500 px-4 py-2 text-sm font-semibold text-slate-950 hover:bg-orange-400"
              >
                Continue
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
