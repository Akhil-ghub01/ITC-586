import React, { useState } from 'react';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000';

function Chatbot() {
  const [messages, setMessages] = useState([]); // { role: "user" | "assistant", content: string }
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSend = async () => {
    const trimmed = input.trim();
    if (!trimmed || loading) return;

    const newUserMessage = { role: 'user', content: trimmed };

    // For UI: show user message immediately
    setMessages((prev) => [...prev, newUserMessage]);
    setInput('');
    setError('');
    setLoading(true);

    try {
      // For backend: history is previous messages only (no duplication of the latest query)
      const payload = {
        query: trimmed,
        history: messages, // messages BEFORE newUserMessage
      };

      const res = await fetch(`${API_BASE_URL}/chatbot/query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        throw new Error(`Server error: ${res.status}`);
      }

      const data = await res.json();

      const botMessage = {
        role: 'assistant',
        content: data.reply ?? '',
      };

      setMessages((prev) => [...prev, botMessage]);
    } catch (err) {
      console.error(err);
      setError('Something went wrong talking to the chatbot. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="chat-container">
      <div className="chat-window">
        {messages.length === 0 && (
          <div className="chat-empty-state">
            <p>Start the conversation by asking a question about your order, shipping, returns, or account.</p>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`chat-message ${msg.role === 'user' ? 'chat-message-user' : 'chat-message-bot'}`}
          >
            <div className="chat-message-meta">
              <span className="chat-message-role">
                {msg.role === 'user' ? 'You' : 'Assistant'}
              </span>
            </div>
            <div className="chat-message-bubble">
              {msg.content}
            </div>
          </div>
        ))}

        {loading && (
          <div className="chat-message chat-message-bot">
            <div className="chat-message-meta">
              <span className="chat-message-role">Assistant</span>
            </div>
            <div className="chat-message-bubble chat-message-bubble-loading">
              Thinking...
            </div>
          </div>
        )}
      </div>

      {error && <div className="chat-error">{error}</div>}

      <div className="chat-input-bar">
        <textarea
          className="chat-input"
          rows={2}
          placeholder="Type your question here and press Enter to send…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button
          className="chat-send-button"
          onClick={handleSend}
          disabled={loading || !input.trim()}
        >
          {loading ? 'Sending…' : 'Send'}
        </button>
      </div>
    </div>
  );
}

export default Chatbot;
