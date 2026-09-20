"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { Logo } from "@/components/Logo";
import { useI18n } from "@/lib/i18n/I18nProvider";

const LINKS = [
  { href: "/chat", key: "nav.chat" },
  { href: "/medicine", key: "nav.medicine" },
  { href: "/prescription", key: "nav.prescription" },
  { href: "/doctors", key: "nav.doctors" },
];

export function NavBar() {
  const { t } = useI18n();
  const pathname = usePathname();

  return (
    <header className="border-b border-ink-100 bg-white">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
        <Link href="/" className="focus-ring group rounded-control">
          <Logo wordmark={t("app.name")} />
        </Link>
        <nav className="hidden items-center gap-1 sm:flex" aria-label="Primary">
          {LINKS.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              aria-current={pathname === link.href ? "page" : undefined}
              className={`focus-ring rounded-control px-3 py-2 text-sm font-medium transition-colors duration-150 ${
                pathname === link.href ? "bg-brand-50 text-brand-700" : "text-ink-700 hover:bg-ink-50 hover:text-brand-700"
              }`}
            >
              {t(link.key)}
            </Link>
          ))}
        </nav>
      </div>
      <nav className="flex items-center gap-1 overflow-x-auto border-t border-ink-100 px-4 py-2 sm:hidden" aria-label="Primary">
        {LINKS.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className="focus-ring shrink-0 rounded-control px-3 py-2 text-sm font-medium text-ink-700 transition-colors duration-150 hover:bg-ink-50 hover:text-brand-700"
          >
            {t(link.key)}
          </Link>
        ))}
      </nav>
    </header>
  );
}
