import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ChatMessage } from "@/components/ChatMessage";

describe("ChatMessage", () => {
  it("renders a user message aligned as a simple bubble", () => {
    render(<ChatMessage message={{ id: "1", role: "user", content: "What is paracetamol?" }} onAction={() => {}} />);
    expect(screen.getByText("What is paracetamol?")).toBeInTheDocument();
  });

  it("renders an emergency-mode assistant message via the EmergencyBanner", () => {
    render(
      <ChatMessage
        message={{
          id: "2",
          role: "assistant",
          content: "Symptoms may need urgent evaluation.",
          response: {
            conversation_id: "c1",
            message_id: "2",
            answer: "Symptoms may need urgent evaluation.",
            mode: "emergency_navigation",
            evidence: [],
            actions: [{ id: "call_emergency", label: "Call Emergency Service", type: "emergency_call" }],
            disclaimer: "",
            language: "en",
            emergency_contacts: { emergency_number: "911", poison_control: null },
          },
        }}
        onAction={() => {}}
      />
    );
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });

  it("invokes onAction when a suggested action button is clicked", () => {
    const onAction = vi.fn();
    render(
      <ChatMessage
        message={{
          id: "3",
          role: "assistant",
          content: "Paracetamol relieves pain.",
          response: {
            conversation_id: "c1",
            message_id: "3",
            answer: "Paracetamol relieves pain.",
            mode: "information",
            evidence: [],
            actions: [{ id: "prepare_visit", label: "Prepare for my visit", type: "suggested_prompt" }],
            disclaimer: "Not medical advice.",
            language: "en",
          },
        }}
        onAction={onAction}
      />
    );

    fireEvent.click(screen.getByRole("button", { name: /prepare for my visit/i }));
    expect(onAction).toHaveBeenCalledWith("prepare_visit", undefined);
  });

  it("never renders the explain-simpler action, to avoid an unnecessary extra LLM call", () => {
    render(
      <ChatMessage
        message={{
          id: "4",
          role: "assistant",
          content: "Paracetamol relieves pain.",
          response: {
            conversation_id: "c1",
            message_id: "4",
            answer: "Paracetamol relieves pain.",
            mode: "information",
            evidence: [],
            actions: [{ id: "explain_simpler", label: "Explain more simply", type: "suggested_prompt" }],
            disclaimer: "Not medical advice.",
            language: "en",
          },
        }}
        onAction={() => {}}
      />
    );

    expect(screen.queryByRole("button", { name: /explain more simply/i })).not.toBeInTheDocument();
  });
});
