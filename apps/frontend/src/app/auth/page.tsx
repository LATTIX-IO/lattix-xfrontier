import type { Metadata } from "next";

import { LattixAuthCard } from "@/components/auth/lattix-auth-card";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Sign in | Lattix xFrontier",
  description: "Secure access to the Lattix xFrontier console.",
};

type AuthPageProps = {
  searchParams?: Promise<Record<string, string | string[] | undefined>>;
};

function readSearchParam(value: string | string[] | undefined): string | null {
  if (Array.isArray(value)) return value[0] ?? null;
  return value ?? null;
}

export default async function AuthPage({ searchParams }: AuthPageProps) {
  const params = searchParams ? await searchParams : {};
  const authError = readSearchParam(params.auth_error);

  return (
    <section className="relative flex min-h-screen items-center justify-center overflow-hidden px-4 py-10">
      <LattixAuthCard initialErrorCode={authError} />
    </section>
  );
}
