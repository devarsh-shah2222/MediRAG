"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";

import en from "./en.json";
import gu from "./gu.json";
import hi from "./hi.json";

export const SUPPORTED_LANGUAGES = [
  { code: "en", label: "English" },
  { code: "hi", label: "हिन्दी" },
  { code: "gu", label: "ગુજરાતી" },
] as const;

export type LanguageCode = (typeof SUPPORTED_LANGUAGES)[number]["code"];

const DICTIONARIES: Record<LanguageCode, Record<string, string>> = { en, hi, gu };
const STORAGE_KEY = "medirag_language";

interface I18nContextValue {
  language: LanguageCode;
  setLanguage: (lang: LanguageCode) => void;
  t: (key: string) => string;
}

const I18nContext = createContext<I18nContextValue | null>(null);

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [language, setLanguageState] = useState<LanguageCode>("en");

  useEffect(() => {
    try {
      const stored = window.localStorage.getItem(STORAGE_KEY) as LanguageCode | null;
      if (stored && DICTIONARIES[stored]) setLanguageState(stored);
    } catch {
      // localStorage unavailable (private browsing) -- fall back to default language
    }
  }, []);

  const setLanguage = (lang: LanguageCode) => {
    setLanguageState(lang);
    try {
      window.localStorage.setItem(STORAGE_KEY, lang);
    } catch {
      // ignore persistence failure, language still applies for this session
    }
  };

  const value = useMemo<I18nContextValue>(
    () => ({
      language,
      setLanguage,
      t: (key: string) => DICTIONARIES[language][key] ?? DICTIONARIES.en[key] ?? key,
    }),
    [language]
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nContextValue {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useI18n must be used within I18nProvider");
  return ctx;
}
