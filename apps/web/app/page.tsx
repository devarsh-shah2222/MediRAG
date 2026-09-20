"use client";

import Link from "next/link";

import { LogoMark } from "@/components/Logo";
import { Alert } from "@/components/ui/Alert";
import { Card } from "@/components/ui/Card";
import { useI18n } from "@/lib/i18n/I18nProvider";

const PRIMARY_ACTIONS = [
  { href: "/chat", key: "home.cta.chat", icon: "💬" },
  { href: "/medicine", key: "home.cta.medicine", icon: "💊" },
  { href: "/prescription", key: "home.cta.prescription", icon: "📄" },
  { href: "/doctors", key: "home.cta.doctors", icon: "🩺" },
];

export default function HomePage() {
  const { t } = useI18n();

  return (
    <div className="flex flex-col gap-8">
      <section className="animate-fade-up flex flex-col items-center gap-4 py-6 text-center sm:py-10">
        <LogoMark className="h-16 w-16 drop-shadow-md" />
        <h1 className="text-3xl font-semibold text-ink-900 sm:text-4xl">{t("home.title")}</h1>
        <p className="mx-auto max-w-xl text-base text-ink-500">{t("home.subtitle")}</p>
      </section>

      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {PRIMARY_ACTIONS.map((action, i) => (
          <Link
            key={action.href}
            href={action.href}
            className="animate-fade-up focus-ring group rounded-card"
            style={{ animationDelay: `${i * 60}ms` }}
          >
            <Card className="flex h-full items-center gap-4 hover:-translate-y-1 hover:shadow-floating">
              <span className="text-3xl transition-transform duration-200 ease-out group-hover:scale-110" aria-hidden="true">
                {action.icon}
              </span>
              <span className="text-lg font-medium text-ink-800">{t(action.key)}</span>
            </Card>
          </Link>
        ))}
      </section>

      <div className="text-center">
        <Link
          href="/how-it-works"
          className="focus-ring rounded-control text-sm font-medium text-brand-700 underline decoration-transparent underline-offset-4 transition-colors hover:decoration-brand-700"
        >
          {t("home.cta.how")}
        </Link>
      </div>

      <Alert tone="info">{t("home.safety_notice")}</Alert>
    </div>
  );
}
