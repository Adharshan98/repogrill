// Turn saved interview turns into chat messages, so an unfinished interview can be continued
export function turnsToMessages(turns) {
  return turns.flatMap((t) => {
    const question = { role: 'interviewer', text: t.question, topic: t.topic }
    if (!t.answer) return [question]
    const feedback = { score: t.score, got_right: t.got_right, missed: t.missed }
    return [question, { role: 'student', text: t.answer, feedback }]
  })
}
