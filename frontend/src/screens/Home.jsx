import { useState } from 'react'
import { analyzeRepo, startInterview } from '../api'

export default function Home({ onStart }) {
  const [url, setUrl] = useState('')
  const [status, setStatus] = useState('') // what we're doing right now, shown while loading
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    try {
      setStatus('Reading your code...')
      const repo = await analyzeRepo(url.trim())
      setStatus(`Found ${repo.chunk_count} pieces of code in ${repo.file_count} files. Preparing your first question...`)
      const interview = await startInterview(repo.repo_id)
      onStart(repo, interview)
    } catch (err) {
      setError(err.message)
      setStatus('')
    }
  }

  const loading = Boolean(status)

  return (
    <div className="pt-10">
      <h1 className="text-4xl font-bold leading-tight">
        Can you explain <span className="text-orange-400">your own code?</span>
      </h1>
      <p className="mt-4 text-lg text-slate-400">
        Paste your GitHub repo. RepoGrill reads it and interviews you on it, the way a real interviewer would in
        a project deep-dive round.
      </p>

      <form onSubmit={handleSubmit} className="mt-8 flex flex-col gap-3 sm:flex-row">
        <input
          type="url"
          required
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://github.com/you/your-project"
          disabled={loading}
          className="flex-1 rounded-lg border border-slate-700 bg-slate-900 px-4 py-3 outline-none focus:border-orange-400"
        />
        <button
          disabled={loading}
          className="rounded-lg bg-orange-500 px-6 py-3 font-semibold text-slate-950 hover:bg-orange-400 disabled:opacity-50"
        >
          {loading ? 'Working...' : 'Start interview'}
        </button>
      </form>

      {status && <p className="mt-4 animate-pulse text-slate-300">{status}</p>}
      {error && <p className="mt-4 rounded-lg bg-red-950 px-4 py-3 text-red-300">{error}</p>}

      <div className="mt-12 grid gap-4 sm:grid-cols-3">
        {[
          ['1. Reads your repo', 'Splits your code into functions and classes and understands what each one does.'],
          ['2. Grills you', 'Asks about your real code, and digs deeper when an answer is vague.'],
          ['3. Scores you', 'Grades every answer and tells you exactly what to revise.'],
        ].map(([title, text]) => (
          <div key={title} className="rounded-lg border border-slate-800 p-4">
            <h3 className="font-semibold">{title}</h3>
            <p className="mt-1 text-sm text-slate-400">{text}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
