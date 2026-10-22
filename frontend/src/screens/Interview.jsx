import { useCallback, useEffect, useRef, useState } from 'react'
import { sendAnswer } from '../api'
import ScoreBadge from '../components/ScoreBadge'
import { canListen, canSpeak, speak, stopSpeaking, useListener } from '../speech'

function loadVoicePreference() {
  try {
    return localStorage.getItem('readAloud') === 'on'
  } catch {
    return false
  }
}

export default function Interview({ repoUrl, interview, initialMessages, onFinish }) {
  // Each message is either an interviewer question or the student's answer with its feedback
  const [messages, setMessages] = useState(
    initialMessages || [{ role: 'interviewer', text: interview.question, topic: interview.topics[0] }],
  )
  const [answer, setAnswer] = useState('')
  const [sending, setSending] = useState(false)
  const [done, setDone] = useState(false)
  const [error, setError] = useState('')
  const [readAloud, setReadAloud] = useState(loadVoicePreference)
  const bottomRef = useRef(null)

  // Spoken sentences are added to the end of whatever is already typed
  const addSpokenText = useCallback((text) => {
    setAnswer((prev) => (prev.trim() ? `${prev.trim()} ${text}` : text))
  }, [])
  const mic = useListener(addSpokenText)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, sending])

  // Read each new question aloud when the student has turned that on
  const latest = messages[messages.length - 1]
  useEffect(() => {
    if (readAloud && latest.role === 'interviewer') speak(latest.text)
  }, [latest, readAloud])

  useEffect(() => stopSpeaking, []) // stop talking when leaving the screen

  const toggleReadAloud = () => {
    const next = !readAloud
    setReadAloud(next)
    if (!next) stopSpeaking()
    try {
      localStorage.setItem('readAloud', next ? 'on' : 'off')
    } catch {
      // storage can be blocked (private mode); the toggle still works for this visit
    }
  }

  const currentTopic = [...messages].reverse().find((m) => m.topic)?.topic
  const topicNumber = interview.topics.indexOf(currentTopic) + 1

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!answer.trim()) return
    mic.stop()
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
        <span className="truncate">{repoUrl.replace('https://github.com/', '')}</span>
        <div className="flex items-center gap-4">
          {canSpeak && (
            <button onClick={toggleReadAloud} className={readAloud ? 'text-orange-400' : 'hover:text-slate-200'}>
              {readAloud ? '🔊 Reading aloud' : '🔈 Read aloud'}
            </button>
          )}
          <span className="shrink-0">
            Topic {Math.max(topicNumber, 1)} of {interview.topics.length}
          </span>
        </div>
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
            placeholder={
              canListen
                ? 'Type your answer, or press Speak and answer out loud like a real interview...'
                : 'Type your answer like you would say it in an interview...'
            }
            className="w-full rounded-lg border border-slate-700 bg-slate-900 p-4 outline-none focus:border-orange-400"
          />
          <div className="mt-2 flex items-center justify-between gap-3">
            <span className="hidden text-xs text-slate-500 sm:inline">Ctrl + Enter to send</span>
            <div className="ml-auto flex gap-2">
              {canListen && (
                <button
                  type="button"
                  disabled={sending}
                  onClick={mic.listening ? mic.stop : mic.start}
                  className={`rounded-lg border px-4 py-2 font-semibold disabled:opacity-50 ${
                    mic.listening
                      ? 'animate-pulse border-red-500 text-red-400'
                      : 'border-slate-700 hover:border-orange-400'
                  }`}
                >
                  {mic.listening ? '● Stop' : '🎤 Speak'}
                </button>
              )}
              <button
                disabled={sending || !answer.trim()}
                className="rounded-lg bg-orange-500 px-6 py-2 font-semibold text-slate-950 hover:bg-orange-400 disabled:opacity-50"
              >
                Send answer
              </button>
            </div>
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
