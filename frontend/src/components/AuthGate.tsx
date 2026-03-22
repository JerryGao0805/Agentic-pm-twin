"use client";

import { FormEvent, useEffect, useState } from "react";
import { KanbanBoard } from "@/components/KanbanBoard";
import { BoardSelector } from "@/components/BoardSelector";
import { ProfileModal } from "@/components/ProfileModal";

const LOCAL_AUTH_KEY = "pm-local-authenticated";
const DEV_USERNAME = process.env.NODE_ENV !== "production" ? "user" : "";
const DEV_PASSWORD = process.env.NODE_ENV !== "production" ? "password" : "";

type AuthMode = "api" | "local";
type AuthState = "loading" | "authenticated" | "unauthenticated";
type AuthView = "login" | "register";

type SessionResponse = {
  authenticated: boolean;
  username: string | null;
};

const canUseLocalFallback = process.env.NODE_ENV !== "production";

const readLocalAuth = () => {
  if (typeof window === "undefined") {
    return false;
  }
  return window.localStorage.getItem(LOCAL_AUTH_KEY) === "true";
};

export const AuthGate = () => {
  const [authMode, setAuthMode] = useState<AuthMode>("api");
  const [authState, setAuthState] = useState<AuthState>("loading");
  const [authView, setAuthView] = useState<AuthView>("login");
  const [loggedInUsername, setLoggedInUsername] = useState<string>("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [activeBoardId, setActiveBoardId] = useState<number | null>(null);

  useEffect(() => {
    let active = true;

    const initializeAuth = async () => {
      try {
        const response = await fetch("/api/auth/session", { credentials: "include" });

        if (response.status === 404 && canUseLocalFallback) {
          if (!active) return;
          setAuthMode("local");
          setAuthState(readLocalAuth() ? "authenticated" : "unauthenticated");
          if (readLocalAuth()) setLoggedInUsername(DEV_USERNAME);
          return;
        }

        if (!response.ok) {
          if (!active) return;
          setAuthMode("api");
          setAuthState("unauthenticated");
          return;
        }

        const payload = (await response.json()) as SessionResponse;
        if (!active) return;
        setAuthMode("api");
        if (payload.authenticated) {
          setAuthState("authenticated");
          setLoggedInUsername(payload.username ?? "");
        } else {
          setAuthState("unauthenticated");
        }
      } catch {
        if (!active) return;
        if (canUseLocalFallback) {
          setAuthMode("local");
          const isLocal = readLocalAuth();
          setAuthState(isLocal ? "authenticated" : "unauthenticated");
          if (isLocal) setLoggedInUsername(DEV_USERNAME);
        } else {
          setError("Unable to load session.");
          setAuthMode("api");
          setAuthState("unauthenticated");
        }
      }
    };

    initializeAuth();

    return () => {
      active = false;
    };
  }, []);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);

    const trimmedUsername = username.trim();
    if (!trimmedUsername || !password) {
      setError("Enter username and password.");
      return;
    }

    setIsSubmitting(true);
    try {
      if (authMode === "local") {
        if (trimmedUsername === DEV_USERNAME && password === DEV_PASSWORD) {
          window.localStorage.setItem(LOCAL_AUTH_KEY, "true");
          setAuthState("authenticated");
          setLoggedInUsername(DEV_USERNAME);
          setPassword("");
          return;
        }
        setError("Invalid credentials.");
        return;
      }

      const endpoint = authView === "register" ? "/api/auth/register" : "/api/auth/login";
      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ username: trimmedUsername, password }),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        setError(data.detail || (authView === "register" ? "Registration failed." : "Invalid credentials."));
        return;
      }

      setAuthState("authenticated");
      setLoggedInUsername(trimmedUsername);
      setPassword("");
    } catch {
      setError(authView === "register" ? "Registration failed. Try again." : "Login failed. Try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleLogout = async () => {
    setError(null);
    setActiveBoardId(null);
    if (authMode === "local") {
      window.localStorage.removeItem(LOCAL_AUTH_KEY);
      setAuthState("unauthenticated");
      return;
    }

    try {
      await fetch("/api/auth/logout", {
        method: "POST",
        credentials: "include",
      });
    } catch {
      // Clear client state anyway
    }
    setAuthState("unauthenticated");
    setLoggedInUsername("");
  };

  if (authState === "loading") {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[var(--surface)] px-6">
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
          Checking session...
        </p>
      </main>
    );
  }

  if (authState === "unauthenticated") {
    const isRegister = authView === "register";
    return (
      <main className="flex min-h-screen items-center justify-center bg-[var(--surface)] px-6">
        <section className="w-full max-w-md rounded-3xl border border-[var(--stroke)] bg-white p-8 shadow-[var(--shadow)]">
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-[var(--gray-text)]">
            Project Management
          </p>
          <h1 className="mt-3 font-display text-3xl font-semibold text-[var(--navy-dark)]">
            {isRegister ? "Create account" : "Sign in"}
          </h1>
          {canUseLocalFallback && DEV_USERNAME && !isRegister ? (
            <p className="mt-3 text-sm leading-6 text-[var(--gray-text)]">
              Dev mode credentials: <strong>{DEV_USERNAME}</strong> / <strong>{DEV_PASSWORD}</strong>
            </p>
          ) : null}
          {isRegister ? (
            <p className="mt-3 text-sm leading-6 text-[var(--gray-text)]">
              Password must be at least 6 characters.
            </p>
          ) : null}
          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <div>
              <label
                htmlFor="username"
                className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]"
              >
                Username
              </label>
              <input
                id="username"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                className="mt-2 w-full rounded-xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)]"
                autoComplete="username"
              />
            </div>
            <div>
              <label
                htmlFor="password"
                className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]"
              >
                Password
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="mt-2 w-full rounded-xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)]"
                autoComplete={isRegister ? "new-password" : "current-password"}
              />
            </div>
            {error ? (
              <p className="text-sm font-semibold text-[#b42318]" role="alert">
                {error}
              </p>
            ) : null}
            <button
              type="submit"
              className="w-full rounded-full bg-[var(--secondary-purple)] px-4 py-3 text-xs font-semibold uppercase tracking-[0.2em] text-white transition hover:brightness-110 disabled:opacity-60"
              disabled={isSubmitting}
            >
              {isSubmitting
                ? isRegister
                  ? "Creating account..."
                  : "Signing in..."
                : isRegister
                  ? "Create account"
                  : "Sign in"}
            </button>
          </form>
          <p className="mt-6 text-center text-sm text-[var(--gray-text)]">
            {isRegister ? (
              <>
                Already have an account?{" "}
                <button
                  type="button"
                  onClick={() => {
                    setAuthView("login");
                    setError(null);
                  }}
                  className="font-semibold text-[var(--primary-blue)] hover:underline"
                >
                  Sign in
                </button>
              </>
            ) : (
              <>
                No account?{" "}
                <button
                  type="button"
                  onClick={() => {
                    setAuthView("register");
                    setError(null);
                  }}
                  className="font-semibold text-[var(--primary-blue)] hover:underline"
                  data-testid="switch-to-register"
                >
                  Create one
                </button>
              </>
            )}
          </p>
        </section>
      </main>
    );
  }

  const [showProfile, setShowProfile] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const displayUsername = loggedInUsername || DEV_USERNAME;

  return (
    <div className="pb-4">
      <div className="mx-auto max-w-[1500px] px-6 pt-6">
        <div className="flex items-center justify-between rounded-2xl border border-[var(--stroke)] bg-white px-4 py-3 shadow-[var(--shadow)]">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
            Signed in as <span className="text-[var(--navy-dark)]">{displayUsername}</span>
          </p>
          <div className="relative">
            <button
              type="button"
              onClick={() => setShowUserMenu((open) => !open)}
              className="rounded-full border border-[var(--stroke)] px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--navy-dark)] transition hover:border-[var(--primary-blue)] hover:text-[var(--primary-blue)]"
            >
              {displayUsername}
            </button>
            {showUserMenu ? (
              <div className="absolute right-0 top-full z-40 mt-2 min-w-[160px] rounded-xl border border-[var(--stroke)] bg-white py-1 shadow-lg">
                {authMode === "api" ? (
                  <button
                    type="button"
                    onClick={() => {
                      setShowProfile(true);
                      setShowUserMenu(false);
                    }}
                    className="block w-full px-4 py-2 text-left text-xs font-semibold text-[var(--navy-dark)] hover:bg-[var(--surface)]"
                  >
                    Profile
                  </button>
                ) : null}
                <button
                  type="button"
                  onClick={() => {
                    setShowUserMenu(false);
                    handleLogout();
                  }}
                  className="block w-full px-4 py-2 text-left text-xs font-semibold text-[var(--navy-dark)] hover:bg-[var(--surface)]"
                >
                  Log out
                </button>
              </div>
            ) : null}
          </div>
        </div>
      </div>
      {authMode === "api" ? (
        <BoardSelector
          activeBoardId={activeBoardId}
          onSelectBoard={setActiveBoardId}
        />
      ) : null}
      <KanbanBoard boardId={activeBoardId} />
      {showProfile ? (
        <ProfileModal
          username={displayUsername}
          onClose={() => setShowProfile(false)}
          onAccountDeleted={() => {
            setShowProfile(false);
            setAuthState("unauthenticated");
            setLoggedInUsername("");
          }}
        />
      ) : null}
    </div>
  );
};
