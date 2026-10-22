// A strong answer to compare with, hidden until the student asks for it
export default function ModelAnswer({ text }) {
  if (!text) return null
  return (
    <details className="mt-1 text-slate-300">
      <summary className="cursor-pointer text-sky-300 hover:text-sky-200">See a model answer</summary>
      <p className="mt-1 whitespace-pre-wrap border-l-2 border-sky-500/40 pl-3">{text}</p>
    </details>
  )
}
