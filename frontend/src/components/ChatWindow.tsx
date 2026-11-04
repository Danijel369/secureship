import { useEffect, useRef, useState } from 'react'
import { useChatChatPost } from '../api/generated/index'

type Message = { role: 'user' | 'assistant' | 'error'; content: string }

// Session id persists across page loads; visible history does not (no history endpoint yet).
export default function ChatWindow() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const sessionId = useRef<string | null>(
    localStorage.getItem('secureship_session_id'),
  )
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const { mutate, isPending } = useChatChatPost()

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, isPending])

  const handleSend = () => {
    const text = input.trim()
    if (!text || isPending) return

    setMessages((prev) => [...prev, { role: 'user', content: text }])
    setInput('')

    mutate(
      { data: { session_id: sessionId.current, message: text } },
      {
        onSuccess: (reply) => {
          sessionId.current = reply.session_id
          localStorage.setItem('secureship_session_id', reply.session_id)
          setMessages((prev) => [
            ...prev,
            { role: 'assistant', content: reply.reply },
          ])
        },
        onError: () => {
          setMessages((prev) => [
            ...prev,
            {
              role: 'error',
              content: 'Something went wrong. Please try again.',
            },
          ])
          setInput(text)
        },
      },
    )
  }

  const handleNewConversation = () => {
    localStorage.removeItem('secureship_session_id')
    sessionId.current = null
    setMessages([])
  }

  return (
    <div className="chat-window">
      <header className="chat-header">
        <span className="chat-title">MockExpress Support</span>
        <button type="button" className="new-chat-btn" onClick={handleNewConversation} disabled={isPending}>
          New conversation
        </button>
      </header>
      <div className="messages">
        {messages.map((msg, i) => (
          <div key={i} className={`bubble ${msg.role}`}>
            {msg.content}
          </div>
        ))}
        {isPending && <div className="bubble assistant pending">…</div>}
        <div ref={messagesEndRef} />
      </div>
      <div className="input-row">
        <input
          type="text"
          className="chat-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              handleSend()
            }
          }}
          maxLength={2000}
          placeholder="Type a message…"
          disabled={isPending}
          aria-label="Message"
        />
        <button
          type="button"
          className="send-btn"
          onClick={handleSend}
          disabled={isPending || !input.trim()}
        >
          Send
        </button>
      </div>
    </div>
  )
}
