import { useEffect, useState } from 'react'
import { getScorecard } from '../api'
import ScoreBadge from '../components/ScoreBadge'

export default function Scorecard({ interviewId, onRestart }) {
  const [card, setCard] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    getScorecard(interviewId).then(setCard).catch((err) => setError(err.message))
  }, [interviewId])

  if (error) return <p className="rounded-lg bg-red-950 px-4 py-3 text-red-300">{error}</p>
  if (!card) return <p className="animate-pulse text-slate-400">Building your scorecard...</p>

  return (
    <div className="flex flex-col gap-8">
      <div className="flex items-center gap-6">
        <ScoreBadge score={card.overall_score} large />
        <div>
          <h1 className="text-2xl font-bold">Your scorecard</h1>
          <p className="text-slate-400">Average score across all your answers</p>
        </div>
      </div>

      {card.study_plan && (
        <section className="rounded-lg border border-orange-500/30 bg-orange-500/5 p-5">
          <h2 className="mb-2 font-semibold text-orange-300">What to revise before your interview</h2>
          <p className="whitespace-pre-wrap text-slate-200">{card.study_plan}</p>
        </section>
      )}

      <section>
        <h2 className="mb-3 font-semibold">By topic (weakest first)</h2>
        <div className="flex flex-col gap-3">
          {card.topics.map((t) => (
            <details key={t.topic} className="rounded-lg border border-slate-800 p-4">
              <summary className="flex cursor-pointer items-center gap-4">
                <ScoreBadge score={t.score} />
                <span className="flex-1">{t.topic}</span>
                <div className="hidden h-2 w-32 rounded bg-slate-800 sm:block">
                  <div className="h-2 rounded bg-orange-400" style={{ width: `${t.score * 10}%` }} />
                </div>
              </summary>
              <div className="mt-4 flex flex-col gap-3 border-t border-slate-800 pt-4 text-sm">
                {t.feedback.map((f, i) => (
                  <div key={i}>
                    <p className="text-slate-300">
                      <span className="font-semibold">Q:</span> {f.question}
                    </p>
                    <p className="mt-1 text-slate-400">Score {f.score}/10</p>
                    {f.got_right && <p className="text-emerald-300">✓ {f.got_right}</p>}
                    {f.missed && <p className="text-amber-300">✗ {f.missed}</p>}
                  </div>
                ))}
              </div>
            </details>
          ))}
        </div>
      </section>

      <button
        onClick={onRestart}
        className="rounded-lg border border-slate-700 py-3 font-semibold hover:border-orange-400"
      >
        Interview me on another repo
      </button>
    </div>
  )
}
