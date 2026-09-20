import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { EvidencePanel } from "@/components/EvidencePanel";

describe("EvidencePanel", () => {
  it("renders nothing when there is no evidence", () => {
    const { container } = render(<EvidencePanel evidence={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("lists each evidence item behind a collapsed disclosure", () => {
    render(
      <EvidencePanel
        evidence={[
          {
            source_name: "MediRAG Demo Reference Library",
            document_title: "Paracetamol",
            source_type: "demo_reference",
            url: null,
            published_date: null,
            snippet: "Paracetamol is commonly used to relieve mild pain.",
            retrieval_score: 0.6,
          },
        ]}
      />
    );

    const details = screen.getByText(/why am i seeing this answer/i).closest("details");
    expect(details).not.toHaveAttribute("open");
    expect(screen.getByText("Paracetamol")).toBeInTheDocument();
    expect(screen.getByText(/relieve mild pain/i)).toBeInTheDocument();
  });
});
