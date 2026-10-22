// A small coloured box showing a score out of 10: red for weak, amber for okay, green for strong
export default function ScoreBadge({ score, large = false }) {
  const color =
    score >= 7 ? 'bg-emerald-500/15 text-emerald-300' : score >= 5 ? 'bg-amber-500/15 text-amber-300' : 'bg-red-500/15 text-red-300'
  const size = large ? 'h-24 w-24 text-3xl' : 'h-10 w-10 text-sm'
  return (
    <div className={`flex shrink-0 items-center justify-center rounded-lg font-bold ${color} ${size}`}>
      {score}
      <span className="text-[0.6em] opacity-60">/10</span>
    </div>
  )
}
