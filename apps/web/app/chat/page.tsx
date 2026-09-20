"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { ChatMessage, DisplayMessage, ThinkingBubble } from "@/components/ChatMessage";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { Textarea } from "@/components/ui/Input";
import { prepareVisit, sendChatMessage } from "@/lib/api";
import { useI18n } from "@/lib/i18n/I18nProvider";
import { getClientSessionId } from "@/lib/session";

let idCounter = 0;
const nextId = () => `local-${Date.now()}-${idCounter++}`;

const THINKING_STAGE_LABEL: Record<"thinking" | "tricky", string> = {
  thinking: "Thinking...",
  tricky: "This one is tricky, let me search more on it...",
};

export default function ChatPage() {
  const { t } = useI18n();
  const router = useRouter();
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [thinkingStage, setThinkingStage] = useState<"thinking" | "tricky">("thinking");
  const [error, setError] = useState<string | null>(null);
  const conversationIdRef = useRef<string | null>(null);
  const inFlightRef = useRef(false);
  const abortRef = useRef<AbortController | null>(null);
  const thinkingTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = scrollContainerRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, loading, thinkingStage]);

  async function submitMessage(text: string) {
    const trimmed = text.trim();
    if (!trimmed || inFlightRef.current) return;
    inFlightRef.current = true;
    setError(null);
    setInput("");
    setMessages((prev) => [...prev, { id: nextId(), role: "user", content: trimmed }]);
    setLoading(true);
    setThinkingStage("thinking");

    const controller = new AbortController();
    abortRef.current = controller;
    thinkingTimerRef.current = setTimeout(() => setThinkingStage("tricky"), 7000);

    try {
      const response = await sendChatMessage(
        {
          message: trimmed,
          conversation_id: conversationIdRef.current,
          client_session_id: getClientSessionId(),
          language: "en",
        },
        { signal: controller.signal }
      );
      conversationIdRef.current = response.conversation_id;
      setMessages((prev) => [...prev, { id: response.message_id, role: "assistant", content: response.answer, response }]);
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") {
        setInput(trimmed);
        setMessages((prev) => [...prev, { id: nextId(), role: "assistant", content: "I was searching and it got cancelled." }]);
      } else {
        setError("Sorry, this question is new to me. Please try again.");
      }
    } finally {
      if (thinkingTimerRef.current) clearTimeout(thinkingTimerRef.current);
      setLoading(false);
      inFlightRef.current = false;
      abortRef.current = null;
    }
  }

  function stopGenerating() {
    abortRef.current?.abort();
  }

  async function handleAction(actionId: string, target?: string | null) {
    if (target) {
      router.push(target);
      return;
    }
    if (actionId === "prepare_visit" && conversationIdRef.current) {
      try {
        const summary = await prepareVisit(conversationIdRef.current);
        setMessages((prev) => [
          ...prev,
          {
            id: nextId(),
            role: "assistant",
            content: `Here are some questions you could bring to your visit:\n${summary.suggested_questions
              .map((q) => `- ${q}`)
              .join("\n")}\n\n${summary.note}`,
          },
        ]);
      } catch {
        setError("Couldn't prepare a visit summary right now. Please try again.");
      }
    }
  }

  return (
    <div className="flex h-[calc(100vh-10rem)] flex-col gap-4">
      <h1 className="text-2xl font-semibold text-ink-900">{t("chat.title")}</h1>

      <div ref={scrollContainerRef} className="flex-1 space-y-4 overflow-y-auto rounded-card border border-ink-100 bg-ink-50 p-4">
        {messages.length === 0 && !loading && (
          <EmptyState title={t("chat.empty_title")} description={t("chat.empty_description")} />
        )}
        {messages.map((message) => (
          <ChatMessage key={message.id} message={message} onAction={handleAction} />
        ))}
        {loading && <ThinkingBubble label={THINKING_STAGE_LABEL[thinkingStage]} />}
      </div>

      {error && <Alert tone="urgent"><span className="animate-fade-up block">{error}</span></Alert>}

      <form
        className="flex flex-wrap gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          submitMessage(input);
        }}
      >
        <label htmlFor="chat-input" className="sr-only">
          {t("chat.placeholder")}
        </label>
        <Textarea
          id="chat-input"
          rows={1}
          value={input}
          placeholder={t("chat.placeholder")}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submitMessage(input);
            }
          }}
          className="min-w-[220px] flex-1"
        />
        <div className="ml-auto flex shrink-0 gap-2">
          <Button type="submit" loading={loading} disabled={!loading && !input.trim()}>
            {t("chat.send")}
          </Button>
          {loading && (
            <Button type="button" variant="secondary" className="aspect-square px-0" aria-label="Stop" onClick={stopGenerating}>
              <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" aria-hidden="true">
                <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" />
                <rect x="8" y="8" width="8" height="8" rx="1.5" fill="currentColor" />
              </svg>
            </Button>
          )}
        </div>
      </form>
    </div>
  );
}
