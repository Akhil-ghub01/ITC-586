import React, { useState } from 'react';
import Chatbot from './components/Chatbot.jsx';
import AgentCopilot from './components/AgentCopilot.jsx';

function App() {
  const [view, setView] = useState('chatbot'); // 'chatbot' | 'copilot'

  return (
    <div className="app-root">
      <header className="app-header">
        <div className="app-header-inner">
          <h1 className="app-title">AI Customer Service Studio</h1>
          <p className="app-subtitle">
            Customer chatbot + agent copilot for e-commerce support.
          </p>

          <div className="app-tabs">
            <button
              className={`app-tab-button ${view === 'chatbot' ? 'app-tab-active' : ''}`}
              onClick={() => setView('chatbot')}
              type="button"
            >
              Customer Chatbot
            </button>
            <button
              className={`app-tab-button ${view === 'copilot' ? 'app-tab-active' : ''}`}
              onClick={() => setView('copilot')}
              type="button"
            >
              Agent Copilot
            </button>
          </div>
        </div>
      </header>

      <main className="app-main">
        {view === 'chatbot' ? <Chatbot /> : <AgentCopilot />}
      </main>
    </div>
  );
}

export default App;
