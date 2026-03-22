"use client";

import { FormEvent, useState } from "react";

type ProfileModalProps = {
  username: string;
  onClose: () => void;
  onAccountDeleted: () => void;
};

export const ProfileModal = ({
  username,
  onClose,
  onAccountDeleted,
}: ProfileModalProps) => {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const handleChangePassword = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setMessage(null);

    if (newPassword !== confirmPassword) {
      setError("New passwords do not match.");
      return;
    }

    setIsSubmitting(true);
    try {
      const resp = await fetch("/api/auth/password", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      });

      if (!resp.ok) {
        const data = await resp.json().catch(() => null);
        setError(data?.detail ?? "Failed to change password.");
        return;
      }

      setMessage("Password updated successfully.");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch {
      setError("Failed to change password.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteAccount = async () => {
    try {
      const resp = await fetch("/api/auth/account", {
        method: "DELETE",
        credentials: "include",
      });
      if (resp.ok || resp.status === 204) {
        onAccountDeleted();
      }
    } catch {
      setError("Failed to delete account.");
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-md rounded-3xl border border-[var(--stroke)] bg-white p-8 shadow-xl">
        <div className="flex items-center justify-between">
          <h2 className="font-display text-xl font-semibold text-[var(--navy-dark)]">
            Profile
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full px-3 py-1 text-sm text-[var(--gray-text)] hover:text-[var(--navy-dark)]"
          >
            Close
          </button>
        </div>

        <p className="mt-4 text-sm text-[var(--gray-text)]">
          Signed in as{" "}
          <span className="font-semibold text-[var(--navy-dark)]">
            {username}
          </span>
        </p>

        <form onSubmit={handleChangePassword} className="mt-6 space-y-3">
          <h3 className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
            Change Password
          </h3>
          <input
            type="password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            placeholder="Current password"
            required
            className="w-full rounded-xl border border-[var(--stroke)] bg-[var(--surface)] px-4 py-2.5 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
          />
          <input
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            placeholder="New password (min 6 chars)"
            required
            minLength={6}
            className="w-full rounded-xl border border-[var(--stroke)] bg-[var(--surface)] px-4 py-2.5 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
          />
          <input
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder="Confirm new password"
            required
            minLength={6}
            className="w-full rounded-xl border border-[var(--stroke)] bg-[var(--surface)] px-4 py-2.5 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
          />
          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full rounded-xl bg-[var(--primary-blue)] px-4 py-2.5 text-sm font-semibold text-white transition hover:brightness-110 disabled:opacity-50"
          >
            {isSubmitting ? "Updating..." : "Update Password"}
          </button>
        </form>

        {message ? (
          <p className="mt-3 text-xs font-semibold text-green-600">{message}</p>
        ) : null}
        {error ? (
          <p className="mt-3 text-xs font-semibold text-[#b42318]">{error}</p>
        ) : null}

        <div className="mt-8 border-t border-[var(--stroke)] pt-6">
          <h3 className="text-xs font-semibold uppercase tracking-[0.2em] text-[#b42318]">
            Danger Zone
          </h3>
          {showDeleteConfirm ? (
            <div className="mt-3 space-y-2">
              <p className="text-xs text-[var(--gray-text)]">
                This will permanently delete your account and all your boards.
              </p>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={handleDeleteAccount}
                  className="rounded-xl bg-[#b42318] px-4 py-2 text-xs font-semibold text-white hover:brightness-110"
                >
                  Confirm Delete
                </button>
                <button
                  type="button"
                  onClick={() => setShowDeleteConfirm(false)}
                  className="rounded-xl border border-[var(--stroke)] px-4 py-2 text-xs font-semibold text-[var(--gray-text)]"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setShowDeleteConfirm(true)}
              className="mt-3 rounded-xl border border-[#b42318] px-4 py-2 text-xs font-semibold text-[#b42318] transition hover:bg-[#b42318] hover:text-white"
            >
              Delete Account
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
