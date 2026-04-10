"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { Send, Plus, MessageSquare, Loader2, ExternalLink } from "lucide-react";
import { chat, type Conversation, type Message, type Source } from "@/lib/api";
import { useDemo } from "@/lib/demo";
import { demoConversations, demoMessages } from "@/lib/demo-data";

function SourceBadge({ source }: { source: Source }) {
  return (
    <a
      href={source.source_url || "#"}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-1 px-2 py-1 rounded-md bg-white/5 border border-white/10 text-xs text-gray-300 hover:bg-white/10 transition-colors"
    >
      <span className="text-[var(--accent)]">{source.source_integration || "doc"}</span>
      <span className="truncate max-w-[120px]">{source.title}</span>
      {source.source_url && <ExternalLink className="w-3 h-3 shrink-0" />}
    </a>
  );
}

function ChatMessage({ message }: { message: Message }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex gap-3 ${isUser ? "justify-end" : ""}`}>
      {!isUser && (
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[var(--accent)] to-[var(--accent-secondary)] flex items-center justify-center text-white text-xs font-bold shrink-0">
          A
        </div>
      )}
      <div className={`max-w-[75%] ${isUser ? "order-first" : ""}`}>
        <div
          className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
            isUser
              ? "bg-[var(--accent)] text-white rounded-br-md"
              : "bg-white/5 border border-white/10 text-gray-200 rounded-bl-md"
          }`}
        >
          <div className="whitespace-pre-wrap">{message.content}</div>
        </div>

        {/* Sources */}
        {message.sources && message.sources.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-2">
            {message.sources.map((s, i) => (
              <SourceBadge key={i} source={s} />
            ))}
          </div>
        )}

        {/* Meta */}
        {!isUser && message.model && (
          <div className="text-xs text-gray-600 mt-1">
            {message.model} · {message.tokens_used} tokens
          </div>
        )}
      </div>
    </div>
  );
}

function ConversationList({
  conversations,
  activeId,
  onSelect,
  onCreate,
}: {
  conversations: Conversation[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onCreate: () => void;
}) {
  return (
    <div className="w-64 border-r border-white/10 flex flex-col h-full">
      <div className="p-3 border-b border-white/10">
        <button
          onClick={onCreate}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg bg-[var(--accent)]/10 text-[var(--accent)] text-sm hover:bg-[var(--accent)]/20 transition-colors"
        >
          <Plus className="w-4 h-4" />
          New chat
        </button>
      </div>
      <div className="flex-1 overflow-auto p-2 space-y-1">
        {conversations.map((c) => (
          <button
            key={c.id}
            onClick={() => onSelect(c.id)}
            className={`w-full text-left flex items-center gap-2 px-3 py-2 rounded-lg text-sm truncate transition-colors ${
              activeId === c.id
                ? "bg-white/10 text-white"
                : "text-gray-400 hover:text-white hover:bg-white/5"
            }`}
          >
            <MessageSquare className="w-4 h-4 shrink-0" />
            <span className="truncate">{c.title || "New chat"}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

export default function AskPage() {
  const { isDemo, markBackendDown } = useDemo();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [loadingConvos, setLoadingConvos] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // Load conversations
  useEffect(() => {
    if (isDemo) {
      setConversations(demoConversations);
      setLoadingConvos(false);
      return;
    }
    chat.listConversations()
      .then(setConversations)
      .catch(() => {
        markBackendDown();
        setConversations(demoConversations);
      })
      .finally(() => setLoadingConvos(false));
  }, [isDemo, markBackendDown]);

  // Load messages when conversation changes
  useEffect(() => {
    if (!activeConversationId) {
      setMessages([]);
      return;
    }
    if (isDemo) {
      setMessages(demoMessages[activeConversationId] || []);
      return;
    }
    chat.getMessages(activeConversationId).then(setMessages).catch(console.error);
  }, [activeConversationId, isDemo]);

  const handleCreateConversation = async () => {
    if (isDemo) {
      const conv: Conversation = {
        id: `conv-${Date.now()}`, title: null, user_id: "demo", is_shared: false, created_at: new Date().toISOString(),
      };
      setConversations((prev) => [conv, ...prev]);
      setActiveConversationId(conv.id);
      return;
    }
    try {
      const conv = await chat.createConversation();
      setConversations((prev) => [conv, ...prev]);
      setActiveConversationId(conv.id);
    } catch (err) {
      console.error("Failed to create conversation:", err);
    }
  };

  // Demo responses keyed by trigger words
  const getDemoResponse = (query: string): { content: string; sources: Source[] } => {
    const q = query.toLowerCase();
    if (q.includes("sprint") || q.includes("planning")) {
      return {
        content: "Based on this week's #engineering discussions, the team has aligned on three priorities for the upcoming sprint:\n\n1. **Payment API Migration** — James is leading the v2 migration. The billing service is done; checkout and subscription services remain. Target: July 10.\n\n2. **JWT Auth Rollout** — Sara's implementation is ahead of schedule. Middleware integration starts tomorrow.\n\n3. **Dashboard Performance** — Lin identified 3 slow queries. She'll add composite indexes and rewrite the aggregation endpoint.\n\n**Open Blockers:**\n- CI pipeline at 18min (needs parallel runners, blocked on DevOps)\n- Need staging payment sandbox credentials from finance",
        sources: [
          { entity_id: "s1", title: "#engineering — Sprint Thread", source_url: "https://slack.com/archives/C01/p123", source_integration: "slack", relevance_score: 0.95 },
          { entity_id: "s2", title: "Q3 Sprint Board", source_url: "https://linear.app/acme/q3", source_integration: "linear", relevance_score: 0.88 },
        ],
      };
    }
    if (q.includes("blocker") || q.includes("blocked")) {
      return {
        content: "There are currently **2 active blockers** across the team:\n\n1. **CI Build Time** (18 min) — Needs parallel test runners. DevOps team is on infra migration until Tuesday. No workaround yet.\n\n2. **Payment Sandbox** — James needs staging credentials for the v2 API migration testing. Requested from finance on Monday, no response yet.\n\n_Recommendation: Escalate the payment sandbox request — the v1 deprecation deadline is July 15._",
        sources: [
          { entity_id: "s3", title: "ACME-2847: Payment API migration", source_url: "https://acme.atlassian.net/browse/ACME-2847", source_integration: "jira", relevance_score: 0.93 },
        ],
      };
    }
    return {
      content: `I searched across your connected tools for "${query}" and here's what I found:\n\n**From Slack (#engineering):**\nRecent discussions mention this topic in the context of the Q3 sprint planning. Sara and James have been coordinating on related work items.\n\n**From Notion:**\nThe Engineering Q3 OKRs document references this area — particularly around platform reliability and developer experience improvements.\n\n**From Jira:**\nThere are 3 open tickets related to this topic, with 1 in progress and 2 in the backlog.\n\n_Want me to dive deeper into any of these?_`,
      sources: [
        { entity_id: "s4", title: "#engineering channel", source_url: "https://slack.com/archives/C01", source_integration: "slack", relevance_score: 0.85 },
        { entity_id: "s5", title: "Q3 OKRs — Engineering", source_url: "https://notion.so/acme/q3-okrs", source_integration: "notion", relevance_score: 0.75 },
      ],
    };
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || sending) return;

    let conversationId = activeConversationId;

    // Auto-create conversation if none selected
    if (!conversationId) {
      if (isDemo) {
        const conv: Conversation = {
          id: `conv-${Date.now()}`, title: null, user_id: "demo", is_shared: false, created_at: new Date().toISOString(),
        };
        setConversations((prev) => [conv, ...prev]);
        conversationId = conv.id;
        setActiveConversationId(conv.id);
      } else {
        try {
          const conv = await chat.createConversation();
          setConversations((prev) => [conv, ...prev]);
          conversationId = conv.id;
          setActiveConversationId(conv.id);
        } catch {
          return;
        }
      }
    }

    const userContent = input.trim();
    setInput("");
    setSending(true);

    // Optimistic user message
    const optimisticUserMsg: Message = {
      id: `temp-${Date.now()}`,
      role: "user",
      content: userContent,
      sources: [],
      tool_calls: [],
      tokens_used: 0,
      model: null,
      created_at: new Date().toISOString(),
    };

    // Placeholder streaming message
    const streamMsgId = `stream-${Date.now()}`;
    const streamMsg: Message = {
      id: streamMsgId,
      role: "assistant",
      content: "",
      sources: [],
      tool_calls: [],
      tokens_used: 0,
      model: null,
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, optimisticUserMsg, streamMsg]);

    // Demo mode: simulate streaming
    if (isDemo) {
      const demoResp = getDemoResponse(userContent);
      const words = demoResp.content.split(" ");
      let built = "";
      for (let i = 0; i < words.length; i++) {
        built += (i === 0 ? "" : " ") + words[i];
        const snapshot = built;
        await new Promise((r) => setTimeout(r, 18));
        setMessages((prev) =>
          prev.map((m) => m.id === streamMsgId ? { ...m, content: snapshot } : m),
        );
      }
      setMessages((prev) =>
        prev.map((m) => m.id === streamMsgId ? { ...m, sources: demoResp.sources, model: "gpt-4o (demo)", tokens_used: words.length * 3 } : m),
      );
      if (!conversations.find((c) => c.id === conversationId)?.title) {
        setConversations((prev) =>
          prev.map((c) => c.id === conversationId ? { ...c, title: userContent.slice(0, 80) } : c),
        );
      }
      setSending(false);
      return;
    }

    try {
      const response = await chat.sendMessageStream(conversationId, userContent);
      if (!response.ok || !response.body) throw new Error("Stream failed");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Parse complete SSE events from buffer
        const parts = buffer.split("\n\n");
        buffer = parts.pop() || ""; // Keep incomplete event in buffer

        for (const part of parts) {
          if (!part.trim()) continue;
          const lines = part.split("\n");
          let eventType = "";
          let eventData = "";

          for (const line of lines) {
            if (line.startsWith("event: ")) eventType = line.slice(7).trim();
            if (line.startsWith("data: ")) eventData = line.slice(6);
          }

          if (!eventData) continue;

          if (eventType === "sources") {
            try {
              const sources = JSON.parse(eventData);
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === streamMsgId ? { ...m, sources } : m,
                ),
              );
            } catch {}
          } else if (eventType === "delta") {
            try {
              const text = JSON.parse(eventData);
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === streamMsgId
                    ? { ...m, content: m.content + text }
                    : m,
                ),
              );
            } catch {}
          } else if (eventType === "done") {
            try {
              const meta = JSON.parse(eventData);
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === streamMsgId
                    ? { ...m, model: meta.model, tokens_used: meta.tokens_total }
                    : m,
                ),
              );
            } catch {}
          }
        }
      }

      // Update conversation title in sidebar
      if (!conversations.find((c) => c.id === conversationId)?.title) {
        setConversations((prev) =>
          prev.map((c) =>
            c.id === conversationId
              ? { ...c, title: userContent.slice(0, 80) }
              : c,
          ),
        );
      }
    } catch (err) {
      console.error("Failed to send message:", err);
      setMessages((prev) => prev.filter((m) => m.id !== optimisticUserMsg.id && m.id !== streamMsgId));
      setInput(userContent);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="flex h-screen">
      {/* Conversation sidebar */}
      <ConversationList
        conversations={conversations}
        activeId={activeConversationId}
        onSelect={setActiveConversationId}
        onCreate={handleCreateConversation}
      />

      {/* Chat area */}
      <div className="flex-1 flex flex-col">
        {/* Messages */}
        <div className="flex-1 overflow-auto p-6 space-y-6">
          {messages.length === 0 && !loadingConvos && (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-[var(--accent)] to-[var(--accent-secondary)] flex items-center justify-center mb-4">
                <MessageSquare className="w-8 h-8 text-white" />
              </div>
              <h2 className="text-xl font-semibold text-white mb-2">Ask</h2>
              <p className="text-gray-400 max-w-md">
                Ask anything about your organization. I can search across
                Slack, GitHub, Jira, Notion, and all your connected tools.
              </p>
            </div>
          )}

          {messages.map((msg) => (
            <ChatMessage key={msg.id} message={msg} />
          ))}

          {sending && (
            <div className="flex gap-3">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[var(--accent)] to-[var(--accent-secondary)] flex items-center justify-center text-white text-xs font-bold">
                A
              </div>
              <div className="bg-white/5 border border-white/10 rounded-2xl rounded-bl-md px-4 py-3">
                <Loader2 className="w-4 h-4 text-gray-400 animate-spin" />
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="p-4 border-t border-white/10">
          <form onSubmit={handleSendMessage} className="flex gap-3">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask anything about your org..."
              className="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-[var(--accent)] text-sm"
              disabled={sending}
            />
            <button
              type="submit"
              disabled={sending || !input.trim()}
              className="bg-[var(--accent)] hover:bg-[var(--accent)]/80 text-white rounded-xl px-4 py-3 transition-colors disabled:opacity-50"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
