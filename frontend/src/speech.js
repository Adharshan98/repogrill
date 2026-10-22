// Voice features built into the browser: speech-to-text (Chrome, Edge) and text-to-speech (most browsers).
import { useEffect, useRef, useState } from 'react'

const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition
const LANGUAGE = 'en-IN' // English (India) handles Indian accents better than en-US

export const canListen = Boolean(Recognition)
export const canSpeak = 'speechSynthesis' in window

// Read text aloud. Code formatting like `analyze` sounds odd when spoken, so strip backticks first.
export function speak(text) {
  if (!canSpeak) return
  window.speechSynthesis.cancel()
  const utterance = new SpeechSynthesisUtterance(text.replace(/`/g, ''))
  utterance.lang = LANGUAGE
  window.speechSynthesis.speak(utterance)
}

export function stopSpeaking() {
  if (canSpeak) window.speechSynthesis.cancel()
}

// Listen to the microphone. Calls onText with each finished sentence the user says.
export function useListener(onText) {
  const [listening, setListening] = useState(false)
  const recognitionRef = useRef(null)
  const onTextRef = useRef(onText)

  useEffect(() => {
    onTextRef.current = onText
  }, [onText])

  useEffect(() => () => recognitionRef.current?.abort(), [])

  const start = () => {
    if (!canListen || listening) return
    stopSpeaking() // don't let the microphone hear the interviewer
    const recognition = new Recognition()
    recognition.lang = LANGUAGE
    recognition.continuous = true
    recognition.interimResults = false
    recognition.onresult = (event) => {
      for (let i = event.resultIndex; i < event.results.length; i++) {
        if (event.results[i].isFinal) onTextRef.current(event.results[i][0].transcript.trim())
      }
    }
    recognition.onend = () => setListening(false)
    recognition.onerror = () => setListening(false)
    recognitionRef.current = recognition
    recognition.start()
    setListening(true)
  }

  const stop = () => recognitionRef.current?.stop()

  return { listening, start, stop }
}
