import { useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Plus, MessageSquare, Search, PanelLeftClose, PanelLeftOpen,
  Sparkles, ArrowUp, ChevronDown, Zap, MoreHorizontal, Bot,
  Clock3, Coins, AlertCircle, LoaderCircle, Command, X,
  BarChart3, PanelTop, Copy, Check, Trash2, ArrowLeft,
  Activity, Database, Gauge, MessagesSquare, RefreshCw,
} from "lucide-react";

const API_URL = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");
const STORAGE_KEY = "lyftr-ai-conversations-v1";

function createSessionId() {
  return crypto.randomUUID();
}

function readSavedConversations() {
  try {
    const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function formatDate(value) {
  if (!value) return "";
  const date = new Date(value);
  const now = new Date();
  const sameDay = date.toDateString() === now.toDateString();
  return sameDay
    ? date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    : date.toLocaleDateString([], { month: "short", day: "numeric" });
}

function getTitle(messages) {
  const firstUserMessage = messages.find((item) => item.role === "user");
  if (!firstUserMessage) return "New conversation";
  return firstUserMessage.content.length > 42
    ? `${firstUserMessage.content.slice(0, 42).trim()}…`
    : firstUserMessage.content;
}

function AnimatedMarkdown({ content }) {
  const [visibleText, setVisibleText] = useState("");
  useEffect(() => {
    const words = content.match(/\S+\s*/g) || [];
    let index = 0;
    setVisibleText("");
    const interval = window.setInterval(() => {
      index += 1;
      setVisibleText(words.slice(0, index).join(""));
      if (index >= words.length) window.clearInterval(interval);
    }, 12);
    return () => window.clearInterval(interval);
  }, [content]);

  return (
    <div className="markdown-content">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{visibleText}</ReactMarkdown>
      {visibleText.length < content.length && <span className="typing-cursor" />}
    </div>
  );
}

function App() {
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState([]);
  const [sessionId, setSessionId] = useState(createSessionId);
  const [loading, setLoading] = useState(false);
  const [conversations, setConversations] = useState(readSavedConversations);
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [activeView, setActiveView] = useState("chat");
  const [historyLoading, setHistoryLoading] = useState(false);
  const [copiedId, setCopiedId] = useState(null);
  const textareaRef = useRef(null);
  const bottomRef = useRef(null);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations));
  }, [conversations]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, loading]);

  useEffect(() => {
    const onKeyDown = (event) => {
      const isMac = navigator.platform.toUpperCase().includes("MAC");
      const modifier = isMac ? event.metaKey : event.ctrlKey;
      if (modifier && event.key.toLowerCase() === "k") {
        event.preventDefault();
        handleNewChat();
      }
      if (event.key === "Escape") {
        setSearchOpen(false);
        setSearchQuery("");
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  });

  const filteredConversations = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    const sorted = [...conversations].sort(
      (a, b) => new Date(b.updatedAt) - new Date(a.updatedAt)
    );
    return query
      ? sorted.filter((item) => item.title.toLowerCase().includes(query))
      : sorted;
  }, [conversations, searchQuery]);

  const analytics = useMemo(() => {
    const allMessages = conversations.flatMap((conversation) => conversation.messages || []);
    const assistantMessages = allMessages.filter((item) => item.role === "assistant" && item.metadata);
    const totalInput = assistantMessages.reduce((sum, item) => sum + (item.metadata.input_tokens || 0), 0);
    const totalOutput = assistantMessages.reduce((sum, item) => sum + (item.metadata.output_tokens || 0), 0);
    const totalLatency = assistantMessages.reduce((sum, item) => sum + (item.metadata.latency_ms || 0), 0);
    const cacheHits = assistantMessages.filter((item) => item.metadata.cache_hit || item.metadata.resolution_source === "LLM_CACHE").length;
    return {
      chats: conversations.length,
      messages: allMessages.filter((item) => item.role === "user").length,
      responses: assistantMessages.length,
      inputTokens: totalInput,
      outputTokens: totalOutput,
      totalTokens: totalInput + totalOutput,
      avgLatency: assistantMessages.length ? Math.round(totalLatency / assistantMessages.length) : 0,
      cacheHits,
      liveCalls: assistantMessages.filter((item) => item.metadata.resolution_source === "LIVE_INFERENCE").length,
      cacheRate: assistantMessages.length ? Math.round((cacheHits / assistantMessages.length) * 100) : 0,
    };
  }, [conversations]);

  function persistConversation(nextMessages, nextSessionId = sessionId) {
    if (!nextMessages.some((item) => item.role === "user")) return;
    const updatedAt = new Date().toISOString();
    const conversation = {
      id: nextSessionId,
      title: getTitle(nextMessages),
      updatedAt,
      messages: nextMessages,
    };
    setConversations((previous) => [
      conversation,
      ...previous.filter((item) => item.id !== nextSessionId),
    ]);
  }

  function handleNewChat() {
    if (loading) return;
    setMessages([]);
    setMessage("");
    setSessionId(createSessionId());
    setActiveView("chat");
    setSearchOpen(false);
    setSearchQuery("");
    textareaRef.current?.focus();
  }

  async function openConversation(conversation) {
    if (loading || historyLoading) return;
    setHistoryLoading(true);
    setActiveView("chat");
    try {
      const response = await fetch(`${API_URL}/sessions/${conversation.id}/messages`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Unable to load this conversation.");
      const loadedMessages = (data.messages || []).map((item, index) => ({
        id: `${conversation.id}-${index}`,
        role: item.role,
        content: item.content,
        metadata: item.metadata || undefined,
      }));
      setSessionId(conversation.id);
      setMessages(loadedMessages);
      setSearchOpen(false);
      setSearchQuery("");
    } catch (error) {
      setMessages((previous) => [
        ...previous,
        { id: crypto.randomUUID(), role: "assistant", content: error.message, isError: true },
      ]);
    } finally {
      setHistoryLoading(false);
    }
  }

  async function handleSend(event) {
    event.preventDefault();
    const userMessage = message.trim();
    if (!userMessage || loading) return;

    const userItem = { id: crypto.randomUUID(), role: "user", content: userMessage };
    const nextMessages = [...messages, userItem];
    setMessages(nextMessages);
    setMessage("");
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, message: userMessage }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Unable to generate a response.");
      const assistantItem = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: data.reply,
        metadata: data.metadata,
      };
      const completedMessages = [...nextMessages, assistantItem];
      setMessages(completedMessages);
      persistConversation(completedMessages);
    } catch (error) {
      const errorItem = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: error.message || "Something went wrong. Please try again.",
        isError: true,
      };
      const failedMessages = [...nextMessages, errorItem];
      setMessages(failedMessages);
      persistConversation(failedMessages);
    } finally {
      setLoading(false);
      textareaRef.current?.focus();
    }
  }

  async function copyMessage(item) {
    try {
      await navigator.clipboard.writeText(item.content);
      setCopiedId(item.id);
      window.setTimeout(() => setCopiedId(null), 1400);
    } catch {
      setCopiedId(null);
    }
  }

  function deleteConversation(event, id) {
    event.stopPropagation();
    setConversations((previous) => previous.filter((item) => item.id !== id));
    if (sessionId === id) handleNewChat();
  }

  const showChat = activeView === "chat";

  return (
    <div className={`app-shell ${sidebarCollapsed ? "sidebar-is-collapsed" : ""}`}>
      <aside className="sidebar">
        <div className="sidebar-top">
          <button className="brand" onClick={() => setActiveView("chat")} aria-label="Lyftr AI home">
            <span className="brand-icon"><Sparkles size={19} /></span>
            <span className="brand-word">lyftr<span>.ai</span></span>
          </button>
          <button className="icon-button collapse-button" onClick={() => setSidebarCollapsed((value) => !value)} title={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}>
            {sidebarCollapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}
          </button>
        </div>

        <button className="new-chat-button" onClick={handleNewChat} disabled={loading} title="New chat">
          <Plus size={17} /><span>New chat</span><kbd>Ctrl K</kbd>
        </button>

        <button className={`sidebar-link ${searchOpen ? "selected" : ""}`} onClick={() => setSearchOpen((value) => !value)}>
          <Search size={17} /><span>Search chats</span>
        </button>

        {searchOpen && (
          <div className="sidebar-search">
            <Search size={15} />
            <input autoFocus value={searchQuery} onChange={(event) => setSearchQuery(event.target.value)} placeholder="Search conversations..." />
            <button onClick={() => { setSearchOpen(false); setSearchQuery(""); }} aria-label="Close search"><X size={14} /></button>
          </div>
        )}

        <div className="sidebar-section">
          <p className="section-label">WORKSPACE</p>
          <button className={`sidebar-link ${showChat ? "active" : ""}`} onClick={() => setActiveView("chat")}>
            <MessageSquare size={17} /><span>Chats</span>
          </button>
          <button className={`sidebar-link ${activeView === "analytics" ? "active" : ""}`} onClick={() => setActiveView("analytics")}>
            <BarChart3 size={17} /><span>Usage & analytics</span>
          </button>
        </div>

        <div className="sidebar-section recent-section">
          <div className="section-heading">
            <p className="section-label">RECENT CHATS</p>
            {!sidebarCollapsed && <span className="recent-count">{filteredConversations.length}</span>}
          </div>
          <div className="conversation-list">
            {filteredConversations.length ? filteredConversations.slice(0, 30).map((conversation) => (
              <button className={`conversation-link ${sessionId === conversation.id && showChat ? "conversation-active" : ""}`} key={conversation.id} onClick={() => openConversation(conversation)} title={conversation.title}>
                <MessageSquare size={15} />
                <span>{conversation.title}</span>
                <small>{formatDate(conversation.updatedAt)}</small>
                <span className="conversation-delete" onClick={(event) => deleteConversation(event, conversation.id)} role="button" aria-label="Delete conversation"><Trash2 size={13} /></span>
              </button>
            )) : <p className="empty-history">{searchQuery ? "No matching chats" : "Your conversations will appear here."}</p>}
          </div>
        </div>

        <div className="sidebar-bottom">
          <div className="sidebar-status"><span className="status-dot" /> <span>AI services ready</span></div>
          <div className="profile">
            <div className="avatar">L</div>
            <div className="profile-info"><span className="profile-name">My Workspace</span><span className="profile-plan">Lyftr AI · Personal</span></div>
            <MoreHorizontal size={18} className="profile-more" />
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div className="breadcrumb">
            <span>Workspace</span><span className="breadcrumb-divider">/</span>
            <span className="breadcrumb-current">{activeView === "analytics" ? "Usage & analytics" : messages.length ? "Chat" : "New chat"}</span>
          </div>
          <div className="topbar-right">
            <div className="model-selector"><span className="model-dot" /> Gemini <span className="model-caption">· active model</span><ChevronDown size={14} /></div>
            <button className="icon-button topbar-command" title="Keyboard shortcuts"><Command size={17} /></button>
          </div>
        </header>

        {activeView === "analytics" ? (
          <section className="analytics-page">
            <div className="page-heading">
              <div><span className="eyebrow">WORKSPACE OVERVIEW</span><h1>Usage & analytics</h1><p>Understand how your Lyftr AI workspace is being used.</p></div>
              <button className="secondary-button" onClick={() => setConversations(readSavedConversations())}><RefreshCw size={15} /> Refresh data</button>
            </div>
            <div className="stats-grid">
              <StatCard icon={<MessagesSquare size={18} />} label="Conversations" value={analytics.chats} detail={`${analytics.messages} user messages`} />
              <StatCard icon={<Coins size={18} />} label="Total tokens" value={analytics.totalTokens.toLocaleString()} detail={`${analytics.inputTokens.toLocaleString()} in · ${analytics.outputTokens.toLocaleString()} out`} />
              <StatCard icon={<Gauge size={18} />} label="Avg. latency" value={`${analytics.avgLatency.toLocaleString()} ms`} detail="Across saved AI responses" />
              <StatCard icon={<Database size={18} />} label="Cache hit rate" value={`${analytics.cacheRate}%`} detail={`${analytics.cacheHits} cached responses`} />
            </div>
            <div className="analytics-grid">
              <div className="panel analytics-panel">
                <div className="panel-heading"><div><h2>Response resolution</h2><p>How saved responses were served</p></div><Activity size={18} /></div>
                <div className="resolution-row"><span className="resolution-dot live" /><span>Live inference</span><strong>{analytics.liveCalls}</strong></div>
                <div className="resolution-row"><span className="resolution-dot cache" /><span>LLM cache</span><strong>{analytics.cacheHits}</strong></div>
                <div className="bar-track"><span className="bar-live" style={{ width: `${analytics.responses ? (analytics.liveCalls / analytics.responses) * 100 : 0}%` }} /><span className="bar-cache" style={{ width: `${analytics.responses ? (analytics.cacheHits / analytics.responses) * 100 : 0}%` }} /></div>
                <p className="panel-footnote">{analytics.responses} responses included in this browser's saved history.</p>
              </div>
              <div className="panel analytics-panel">
                <div className="panel-heading"><div><h2>Token usage</h2><p>Prompt and completion tokens</p></div><Coins size={18} /></div>
                <div className="token-total">{analytics.totalTokens.toLocaleString()} <span>tokens</span></div>
                <div className="token-breakdown"><div><span className="token-key input-key" />Input tokens<strong>{analytics.inputTokens.toLocaleString()}</strong></div><div><span className="token-key output-key" />Output tokens<strong>{analytics.outputTokens.toLocaleString()}</strong></div></div>
              </div>
            </div>
            <div className="panel recent-activity">
              <div className="panel-heading"><div><h2>Recent conversations</h2><p>Your locally saved conversation history</p></div><button className="text-button" onClick={() => setActiveView("chat")}>Open chats <ArrowLeft size={14} /></button></div>
              {conversations.length ? conversations.slice(0, 5).map((item) => <button className="activity-item" key={item.id} onClick={() => openConversation(item)}><span className="activity-icon"><MessageSquare size={16} /></span><span className="activity-title">{item.title}</span><span className="activity-date">{formatDate(item.updatedAt)}</span><ChevronDown size={15} className="activity-chevron" /></button>) : <div className="empty-analytics">No saved conversations yet. Start a chat to see your usage here.</div>}
            </div>
            <p className="analytics-disclaimer">Analytics are calculated from conversations saved in this browser. They are not account-wide server analytics.</p>
          </section>
        ) : (
          <>
            <section className="chat-area" key={sessionId}>
              {historyLoading ? <div className="loading-screen"><LoaderCircle className="loading-spinner" /> Loading conversation...</div> : messages.length === 0 ? (
                <div className="welcome-screen">
                  <div className="welcome-icon"><Sparkles size={25} /></div>
                  <p className="welcome-eyebrow">YOUR AI WORKSPACE</p>
                  <h1>Ideas start with<br /><span>a conversation.</span></h1>
                  <p className="welcome-description">Ask a question, explore an idea, or work through a problem. Lyftr AI is ready when you are.</p>
                  <div className="suggestion-grid">
                    <Suggestion icon={<Sparkles size={17} />} tone="purple" title="Learn something" description="Break down a complex topic" onClick={() => setMessage("Explain a complex topic in simple terms")} />
                    <Suggestion icon={<Command size={17} />} tone="blue" title="Build with code" description="Debug, design, and improve" onClick={() => setMessage("Help me write clean, maintainable code")} />
                    <Suggestion icon={<Zap size={17} />} tone="orange" title="Explore an idea" description="Brainstorm your next project" onClick={() => setMessage("Help me brainstorm a project idea")} />
                    <Suggestion icon={<Clock3 size={17} />} tone="green" title="Plan your work" description="Turn goals into clear next steps" onClick={() => setMessage("Help me plan my day")} />
                  </div>
                </div>
              ) : (
                <div className="messages-container">
                  {messages.map((item) => (
                    <div className={`message-row ${item.role === "user" ? "user-message" : "assistant-message"} message-enter`} key={item.id} data-testid={item.role === "assistant" && !item.isError ? "assistant-message" : undefined}>
                      {item.role === "assistant" && <div className="message-avatar"><Bot size={18} /></div>}
                      <div className="message-body">
                        {item.role === "assistant" && !item.isError ? <AnimatedMarkdown content={item.content} /> : <p>{item.content}</p>}
                        {item.metadata && (
                          <div className="message-metadata">
                            <span className={`source-pill ${item.metadata.resolution_source === "LLM_CACHE" ? "metadata-cache" : "metadata-live"}`} data-testid="meta-source"><span className="source-dot" />{item.metadata.resolution_source}</span>
                            <span data-testid="meta-model">{item.metadata.model}</span>
                            <span data-testid="meta-latency"><Clock3 size={12} />{item.metadata.latency_ms} ms</span>
                            <span><Coins size={12} />In: <strong data-testid="meta-input-tokens">{item.metadata.input_tokens}</strong></span>
                            <span>Out: <strong data-testid="meta-output-tokens">{item.metadata.output_tokens}</strong></span>
                            {item.metadata.key_id && <span>{item.metadata.key_id}</span>}
                            <span>{item.metadata.fallback_attempts || 0} fallbacks</span>
                          </div>
                        )}
                        {item.isError && <div className="message-error"><AlertCircle size={14} /> Request failed</div>}
                        {item.role === "assistant" && !item.isError && <div className="message-actions"><button onClick={() => copyMessage(item)} title="Copy response">{copiedId === item.id ? <Check size={14} /> : <Copy size={14} />}{copiedId === item.id ? "Copied" : "Copy"}</button></div>}
                      </div>
                    </div>
                  ))}
                  {loading && <div className="message-row assistant-message"><div className="message-avatar"><Bot size={18} /></div><div className="message-body loading-indicator"><LoaderCircle size={17} className="loading-spinner" /><span>Lyftr AI is thinking...</span></div></div>}
                  <div ref={bottomRef} />
                </div>
              )}
            </section>
            <div className="composer-wrapper">
              <form className="message-composer" onSubmit={handleSend}>
                <textarea ref={textareaRef} data-testid="chat-input" value={message} onChange={(event) => setMessage(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); handleSend(event); } }} placeholder="Message Lyftr AI..." rows={2} disabled={loading} />
                <div className="composer-footer">
                  <div className="composer-tools"><span className="composer-hint"><span className="hint-dot" /> Responses include model and usage metadata</span></div>
                  <div className="composer-actions"><span className="enter-hint">Enter to send · Shift + Enter for new line</span><button type="submit" data-testid="send-button" className="send-button" disabled={!message.trim() || loading} aria-label="Send message"><ArrowUp size={18} /></button></div>
                </div>
              </form>
              <p className="disclaimer">Lyftr AI can make mistakes. Verify important information.</p>
            </div>
          </>
        )}
      </main>
    </div>
  );
}

function StatCard({ icon, label, value, detail }) {
  return <div className="stat-card"><div className="stat-card-top"><span className="stat-icon">{icon}</span><span className="stat-label">{label}</span></div><strong className="stat-value">{value}</strong><span className="stat-detail">{detail}</span></div>;
}

function Suggestion({ icon, tone, title, description, onClick }) {
  return <button className="suggestion-card" onClick={onClick}><span className={`suggestion-icon ${tone}`}>{icon}</span><span><strong>{title}</strong><small>{description}</small></span><ArrowUp size={14} className="suggestion-arrow" /></button>;
}

export default App;
