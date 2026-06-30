import { useState } from "react";
import { apiFetch } from "../lib/api";

export default function ChatPage() {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);

  const ask = async () => {
    if (!question.trim()) return;
    const q = question;
    setQuestion("");
    setMessages((prev) => [...prev, { role: "user", content: q }]);
    setLoading(true);

    try {
      const data = await apiFetch("/chat", {
        method: "POST",
        body: JSON.stringify({ question: q, top_k: 10 }),
      });
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.answer, meta: data },
      ]);
    } catch {
      setMessages((prev) => [...prev, { role: "assistant", content: "Error fetching answer." }]);
    }
    setLoading(false);
  };

  return (
    <div className="p-6 max-w-4xl mx-auto flex flex-col h-[calc(100vh-4rem)]">
      <h1 className="text-3xl font-bold mb-2">AI Chat</h1>
      <p className="text-gray-400 mb-6">Ask operational, maintenance, and engineering questions</p>

      <div className="flex-1 overflow-y-auto space-y-4 mb-4 bg-gray-900 rounded-xl p-4 border border-gray-800">
        {messages.length === 0 && (
          <div className="text-center text-gray-500 mt-20">
            <p className="text-2xl mb-2">Ask anything...</p>
            <p className="text-sm">Example: "Why did Turbine WTG-12 fail?"</p>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[80%] rounded-xl p-4 text-sm ${
                m.role === "user" ? "bg-blue-600" : "bg-gray-800 border border-gray-700"
              }`}
            >
              <p className="whitespace-pre-wrap">{m.content}</p>
              {m.meta && (
                <div className="mt-3 pt-3 border-t border-gray-700">
                  <div className="flex gap-4 text-xs text-gray-400 flex-wrap">
                    <span className="text-green-400">Confidence: {m.meta.confidence}%</span>
                    {m.meta.sources?.slice(0, 3).map((s, si) => (
                      <span key={si} className="bg-gray-700 px-1.5 py-0.5 rounded">
                        {s.filename} p.{s.page}
                      </span>
                    ))}
                  </div>
                  {m.meta.related && Object.keys(m.meta.related).length > 0 && (
                    <div className="mt-2 text-xs text-gray-500">
                      Related:{" "}
                      {Object.entries(m.meta.related).map(([type, vals]) => (
                        <span key={type} className="mr-2">{type}: {vals.join(", ")}</span>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-800 rounded-xl p-4 text-sm border border-gray-700">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" />
                <span className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: "0.1s" }} />
                <span className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: "0.2s" }} />
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="flex gap-2">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && ask()}
          placeholder="Ask about equipment failures, maintenance, procedures..."
          className="flex-1 bg-gray-900 border border-gray-700 rounded-xl px-4 py-3 text-sm focus:border-blue-500 focus:outline-none"
        />
        <button
          onClick={ask}
          disabled={loading}
          className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 px-6 py-3 rounded-xl text-sm font-medium"
        >
          Send
        </button>
      </div>
    </div>
  );
}
