import { useEffect, useRef, useState } from 'react'
import { sendAnswer } from '../api'
import ScoreBadge from '../components/ScoreBadge'

export default function Interview({ repo, interview, onFinish }) {
  // Each message is either an interviewer question or the student's answer with its feedback
  const [messages, setMessages] = useState([
    { role: 'interviewer', text: interview.question, topic: interview.topics[0] },
  ])
  const [answer, setAnswer] = useState('')
  const [sending, setSending] = useState(false)
  const [done, setDone] = useState(false)
  const [error, setError] = useState('')
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, sending])

  const currentTopic = [...messages].reverse().find((m) => m.topic)?.topic
  const topicNumber = interview.topics.indexOf(currentTopic) + 1

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!answer.trim()) return
    setError('')
    setSending(true)
    const text = answer.trim()
    try {
      const result = await sendAnswer(interview.interview_id, text)
      setMessages((prev) => {
        const next = [...prev, { role: 'student', text, feedback: result.feedback }]
        if (!result.done) next.push({ role: 'interviewer', text: result.question, topic: result.topic })
        return next
      })
      setAnswer('')
      setDone(result.done)
    } catch (err) {
      setError(err.message)
    } finally {
      setSending(false)
    }
  }

  // Ctrl+Enter (or Cmd+Enter) sends the answer
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) handleSubmit(e)
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between text-sm text-slate-400">
        <span className="truncate">{repo.repo_url.replace('https://github.com/', '')}</span>
        <span>
          Topic {Math.max(topicNumber, 1)} of {interview.topics.length}
        </span>
      </div>

      <div className="flex flex-col gap-4">
        {messages.map((m, i) =>
          m.role === 'interviewer' ? (
            <div key={i} className="rounded-lg border border-slate-800 bg-slate-900 p-4">
              <p className="mb-2 text-xs uppercase tracking-wide text-orange-400">{m.topic}</p>
              <p className="whitespace-pre-wrap">{m.text}</p>
            </div>
          ) : (
            <div key={i} className="ml-8 flex flex-col gap-2">
              <p className="whitespace-pre-wrap rounded-lg bg-slate-800 p-4">{m.text}</p>
              <Feedback feedback={m.feedback} />
            </div>
          ),
        )}
        {sending && <p className="animate-pulse text-slate-400">Grading your answer...</p>}
        <div ref={bottomRef} />
      </div>

      {error && <p className="mt-4 rounded-lg bg-red-950 px-4 py-3 text-red-300">{error}</p>}

      {done ? (
        <button
          onClick={onFinish}
          className="mt-8 w-full rounded-lg bg-orange-500 py-3 font-semibold text-slate-950 hover:bg-orange-400"
        >
          See my scorecard
        </button>
      ) : (
        <form onSubmit={handleSubmit} className="mt-6">
          <textarea
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={sending}
            rows={4}
            placeholder="Type your answer like you would say it in an interview..."
            className="w-full rounded-lg border border-slate-700 bg-slate-900 p-4 outline-none focus:border-orange-400"
          />
          <div className="mt-2 flex items-center justify-between">
            <span className="text-xs text-slate-500">Ctrl + Enter to send</span>
            <button
              disabled={sending || !answer.trim()}
              className="rounded-lg bg-orange-500 px-6 py-2 font-semibold text-slate-950 hover:bg-orange-400 disabled:opacity-50"
            >
              Send answer
            </button>
          </div>
        </form>
      )}
    </div>
  )
}

function Feedback({ feedback }) {
  if (!feedback || feedback.score === null) return null
  return (
    <div className="flex gap-3 rounded-lg border border-slate-800 p-3 text-sm">
      <ScoreBadge score={feedback.score} />
      <div className="flex flex-col gap-1">
        {feedback.got_right && <p className="text-emerald-300">✓ {feedback.got_right}</p>}
        {feedback.missed && <p className="text-amber-300">✗ {feedback.missed}</p>}
      </div>
    </div>
  )
}
