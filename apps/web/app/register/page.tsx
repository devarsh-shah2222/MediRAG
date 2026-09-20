"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { ApiError, register } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await register(email, password);
      router.push("/chat");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-sm">
      <Card>
        <h1 className="mb-4 text-xl font-semibold text-ink-900">Create an account</h1>
        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <label htmlFor="email" className="text-sm font-medium text-ink-700">
            Email
          </label>
          <Input id="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          <label htmlFor="password" className="text-sm font-medium text-ink-700">
            Password (min. 8 characters)
          </label>
          <Input
            id="password"
            type="password"
            required
            minLength={8}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          {error && <Alert tone="urgent">{error}</Alert>}
          <Button type="submit" loading={loading}>
            Create account
          </Button>
        </form>
        <p className="mt-4 text-sm text-ink-500">
          Already have an account?{" "}
          <Link href="/login" className="focus-ring text-brand-700 underline">
            Log in
          </Link>
        </p>
      </Card>
    </div>
  );
}
