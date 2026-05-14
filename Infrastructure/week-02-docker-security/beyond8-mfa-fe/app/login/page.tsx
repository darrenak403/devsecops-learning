"use client";

import { useState } from "react";
import { useAuth } from "@/hooks/useAuth";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const { login, isLoading } = useAuth();

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!email.trim()) return;
    await login(email.trim());
  };

  return (
    <main className="mx-auto flex min-h-screen max-w-5xl items-center justify-center px-4 py-10">
      <section className="grid w-full overflow-hidden rounded-3xl border bg-white shadow-xl md:grid-cols-2">
        <div className="bg-[#faf3e1] p-8 md:p-10">
          <h1 className="text-3xl font-extrabold">He thong Admin Cap Phat OTP</h1>
          <p className="mt-3 text-sm text-[#6d6d6d]">
            Moi OTP duoc cap phat cho quan tri vien thong qua backend FastAPI.
          </p>
        </div>

        <div className="p-8 md:p-10">
          <h2 className="text-2xl font-bold">Dang nhap</h2>
          <p className="mt-2 text-sm text-muted-foreground">Vui long nhap email admin de tiep tuc.</p>

          <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
            <label className="block text-sm font-medium" htmlFor="email">
              Email
            </label>
            <input
              id="email"
              type="email"
              className="w-full rounded-xl border border-input px-4 py-3 outline-none ring-0 focus:border-[#fa8112]"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="admin@example.com"
            />
            <button
              type="submit"
              disabled={isLoading}
              className="w-full rounded-xl bg-[#fa8112] px-4 py-3 font-semibold text-white disabled:opacity-60"
            >
              {isLoading ? "Dang xu ly..." : "Dang nhap"}
            </button>
          </form>
        </div>
      </section>
    </main>
  );
}
