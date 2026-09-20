import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { EmergencyBanner } from "@/components/EmergencyBanner";

describe("EmergencyBanner", () => {
  it("renders the urgent heading and answer text", () => {
    render(
      <EmergencyBanner
        answer="Your description includes symptoms that may need urgent professional evaluation."
        actions={[{ id: "call_emergency", label: "Call Emergency Service", type: "emergency_call" }]}
        contacts={{ emergency_number: "911", poison_control: "1-800-222-1222" }}
      />
    );

    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText(/urgent medical attention may be needed/i)).toBeInTheDocument();
    expect(screen.getByText(/911/)).toBeInTheDocument();
  });

  it("disables the call action and shows a note when no emergency number is configured", () => {
    render(
      <EmergencyBanner
        answer="Symptoms may need urgent evaluation."
        actions={[{ id: "call_emergency", label: "Call Emergency Service", type: "emergency_call" }]}
        contacts={{ emergency_number: null, poison_control: null, note: "Not configured for your region yet." }}
      />
    );

    expect(screen.getByRole("button", { name: /call emergency service/i })).toHaveAttribute("aria-disabled", "true");
    expect(screen.getByText(/not configured for your region yet/i)).toBeInTheDocument();
  });

  it("renders a navigate action as a link to its target", () => {
    render(
      <EmergencyBanner
        answer="Symptoms may need urgent evaluation."
        actions={[{ id: "find_hospital", label: "Find Nearby Hospital", type: "navigate", target: "/doctors?emergency=true" }]}
      />
    );

    const link = screen.getByRole("link", { name: /find nearby hospital/i });
    expect(link).toHaveAttribute("href", "/doctors?emergency=true");
  });
});
