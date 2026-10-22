// All calls to the Python backend live here, so screens never deal with fetch details.

async function request(path, options = {}) {
  const response = await fetch(`/api${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(data.detail || `Request failed (${response.status})`)
  }
  return data
}

export const analyzeRepo = (repoUrl) =>
  request('/analyze', { method: 'POST', body: JSON.stringify({ repo_url: repoUrl }) })

export const startInterview = (repoId) =>
  request(`/repos/${repoId}/interviews`, { method: 'POST' })

export const sendAnswer = (interviewId, answer) =>
  request(`/interviews/${interviewId}/answer`, { method: 'POST', body: JSON.stringify({ answer }) })

export const getScorecard = (interviewId) => request(`/interviews/${interviewId}/scorecard`)

export const listInterviews = () => request('/interviews')

export const getInterview = (interviewId) => request(`/interviews/${interviewId}`)
