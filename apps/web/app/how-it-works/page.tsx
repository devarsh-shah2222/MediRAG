import { Card } from "@/components/ui/Card";

const STEPS = [
  {
    title: "You ask, in plain language",
    body: "Ask MediAssist about a health topic or a medicine by name. (Uploading a prescription or medicine photo is coming soon -- it needs a real OCR provider we haven't wired up yet.)",
  },
  {
    title: "We retrieve trusted references first",
    body: "MediRAG looks up relevant passages from a curated reference library before answering, instead of guessing.",
  },
  {
    title: "Every answer shows its evidence",
    body: "Each answer links back to the specific reference passages it came from, so you can see why it says what it says.",
  },
  {
    title: "We flag when something may need urgent care",
    body: "A separate safety check runs on every message. If it looks like your situation may need prompt attention, we prioritize getting you to care over a long explanation.",
  },
];

export default function HowItWorksPage() {
  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-2xl font-semibold text-ink-900">How MediRAG works</h1>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {STEPS.map((step, i) => (
          <Card key={step.title}>
            <p className="mb-2 text-sm font-medium text-brand-700">Step {i + 1}</p>
            <h2 className="mb-1 text-lg font-semibold text-ink-900">{step.title}</h2>
            <p className="text-sm text-ink-500">{step.body}</p>
          </Card>
        ))}
      </div>
      <Card className="bg-brand-50">
        <p className="text-sm text-ink-700">
          MediRAG is not a doctor. It provides general health information and helps you get to the right care faster
          -- it never diagnoses, prescribes, or changes an existing prescription.
        </p>
      </Card>
    </div>
  );
}
