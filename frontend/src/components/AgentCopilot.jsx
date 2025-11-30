import React, { useState } from 'react';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000';

const defaultConversation = [
  {
    role: 'user',
    content: 'Hi, I ordered headphones last week and they still have not arrived.',
  },
  {
    role: 'assistant',
    content: 'I am sorry to hear that. Can you please share your order number?',
  },
  {
    role: 'user',
    content: 'The order number is #12345, and the tracking has not updated for 5 days.',
  },
];

function AgentCopilot() {
  const [conversation, setConversation] = useState(defaultConversation);
  const [latestCustomerMessage, setLatestCustomerMessage] = useState(
    'My order was supposed to arrive yesterday with express shipping but the tracking has not updated. Can you help?',
  );
  const [topicHint, setTopicHint] = useState('orders');
  const [suggestedReply, setSuggestedReply] = useState('');
  const [summary, setSummary] = useState('');
  const [keyPoints, setKeyPoints] = useState([]);
  const [loadingSuggest, setLoadingSuggest] = useState(false);
  const [loadingSummary, setLoadingSummary] = useState(false);
  const [error, setError] = useState('');

  const handleSuggestReply = async () => {
    if (!latestCustomerMessage.trim()) return;

    setLoadingSuggest(true);
    setError('');
    setSuggestedReply('');

    try {
      const payload = {
        customer_message: latestCustomerMessage.trim(),
        conversation_history: conversation,
        topic_hint: topicHint || null,
      };

      const res = await fetch(`${API_BASE_URL}/copilot/suggest-reply`, {
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
      setSuggestedReply(data.suggested_reply ?? '');
    } catch (err) {
      console.error(err);
      setError('Failed to generate a suggested reply. Please try again.');
    } finally {
      setLoadingSuggest(false);
    }
  };

  const handleSummarize = async () => {
    setLoadingSummary(true);
    setError('');
    setSummary('');
    setKeyPoints([]);

    try {
      const payload = {
        conversation,
      };

      const res = await fetch(`${API_BASE_URL}/copilot/summarize-case`, {
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
      setSummary(data.summary ?? '');
      setKeyPoints(data.key_points ?? []);
    } catch (err) {
      console.error(err);
      setError('Failed to summarize the case. Please try again.');
    } finally {
      setLoadingSummary(false);
    }
  };

  const handleAddAgentReplyToConversation = () => {
    if (!suggestedReply.trim()) return;

    const newMessage = {
      role: 'assistant',
      content: suggestedReply.trim(),
    };

    setConversation((prev) => [...prev, newMessage]);
  };

  const handleAddCustomerFollowup = () => {
    if (!latestCustomerMessage.trim()) return;

    const newMessage = {
      role: 'user',
      content: latestCustomerMessage.trim(),
    };

    setConversation((prev) => [...prev, newMessage]);
    setLatestCustomerMessage('');
  };

  return (
    <div className="copilot-root">
      <div className="copilot-grid">
        {/* Left: Conversation context */}
        <section className="copilot-panel">
          <h2 className="copilot-title">Conversation Context</h2>
          <p className="copilot-description">
            This is the current conversation between the customer and the agent. You can add follow-up
            messages to simulate a live case.
          </p>

          <div className="copilot-conversation">
            {conversation.length === 0 && (
              <div className="copilot-empty">No messages yet. Add a customer message below.</div>
            )}

            {conversation.map((msg, idx) => (
              <div
                key={idx}
                className={`copilot-msg ${
                  msg.role === 'user' ? 'copilot-msg-customer' : 'copilot-msg-agent'
                }`}
              >
                <div className="copilot-msg-meta">
                  <span className="copilot-msg-role">
                    {msg.role === 'user' ? 'Customer' : 'Agent'}
                  </span>
                </div>
                <div className="copilot-msg-bubble">{msg.content}</div>
              </div>
            ))}
          </div>

          <div className="copilot-input-group">
            <label className="copilot-label">Add customer follow-up</label>
            <textarea
              className="copilot-textarea"
              rows={3}
              placeholder="Type a new customer message to add to the conversation…"
              value={latestCustomerMessage}
              onChange={(e) => setLatestCustomerMessage(e.target.value)}
            />
            <div className="copilot-row">
              <div className="copilot-select-group">
                <label className="copilot-label-sm">Topic hint (optional)</label>
                <select
                  className="copilot-select"
                  value={topicHint}
                  onChange={(e) => setTopicHint(e.target.value)}
                >
                  <option value="orders">Orders & Shipping</option>
                  <option value="returns">Returns & Refunds</option>
                  <option value="account">Account & Security</option>
                  <option value="">None</option>
                </select>
              </div>

              <button
                className="copilot-button-outline"
                type="button"
                onClick={handleAddCustomerFollowup}
                disabled={!latestCustomerMessage.trim()}
              >
                Add to conversation
              </button>
            </div>
          </div>
        </section>

        {/* Right: Copilot tools */}
        <section className="copilot-panel">
          <h2 className="copilot-title">Agent Copilot Tools</h2>
          <p className="copilot-description">
            Generate suggested replies and quick summaries to help the human agent respond faster and more
            consistently.
          </p>

          {error && <div className="copilot-error">{error}</div>}

          {/* Suggest reply */}
          <div className="copilot-box">
            <div className="copilot-box-header">
              <h3>Suggested Reply</h3>
              <button
                className="copilot-button-primary"
                type="button"
                onClick={handleSuggestReply}
                disabled={loadingSuggest || !latestCustomerMessage.trim()}
              >
                {loadingSuggest ? 'Generating…' : 'Suggest Reply'}
              </button>
            </div>

            <p className="copilot-help-text">
              Uses the knowledge base and conversation context to draft a reply the agent can edit.
            </p>

            <textarea
              className="copilot-textarea copilot-textarea-output"
              rows={6}
              placeholder="Suggested reply will appear here…"
              value={suggestedReply}
              onChange={(e) => setSuggestedReply(e.target.value)}
            />

            <div className="copilot-row-end">
              <button
                className="copilot-button-outline"
                type="button"
                onClick={handleAddAgentReplyToConversation}
                disabled={!suggestedReply.trim()}
              >
                Add as agent message
              </button>
            </div>
          </div>

          {/* Summarize case */}
          <div className="copilot-box">
            <div className="copilot-box-header">
              <h3>Summarize Case</h3>
              <button
                className="copilot-button-secondary"
                type="button"
                onClick={handleSummarize}
                disabled={loadingSummary || conversation.length === 0}
              >
                {loadingSummary ? 'Summarizing…' : 'Summarize'}
              </button>
            </div>

            <p className="copilot-help-text">
              Generates a short summary and key points so the next agent can quickly understand the case.
            </p>

            <div className="copilot-summary">
              {summary && <p className="copilot-summary-text">{summary}</p>}

              {keyPoints && keyPoints.length > 0 && (
                <ul className="copilot-summary-list">
                  {keyPoints.map((kp, idx) => (
                    <li key={idx}>{kp}</li>
                  ))}
                </ul>
              )}

              {!summary && !loadingSummary && (
                <p className="copilot-summary-placeholder">
                  No summary yet. Click &quot;Summarize&quot; to generate one.
                </p>
              )}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

export default AgentCopilot;
