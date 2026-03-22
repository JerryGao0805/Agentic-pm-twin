"use client";

import { useEffect, useState } from "react";

type ActivityEntry = {
  id: number;
  action: string;
  details: Record<string, string> | null;
  created_at: string;
  username: string;
};

type BoardActivityFeedProps = {
  boardId: number;
};

const actionLabel = (entry: ActivityEntry): string => {
  const d = entry.details;
  switch (entry.action) {
    case "card_created":
      return `created card "${d?.title ?? "untitled"}"`;
    case "card_deleted":
      return `deleted card "${d?.title ?? "untitled"}"`;
    case "card_moved":
      return `moved "${d?.title ?? "card"}" from ${d?.from_column ?? "?"} to ${d?.to_column ?? "?"}`;
    case "column_added":
      return `added column "${d?.title ?? "untitled"}"`;
    case "column_deleted":
      return `deleted column "${d?.title ?? "untitled"}"`;
    case "board_renamed":
      return `renamed board to "${d?.name ?? ""}"`;
    case "board_deleted":
      return `deleted the board`;
    default:
      return entry.action;
  }
};

const actionIcon = (action: string): string => {
  switch (action) {
    case "card_created":
      return "+";
    case "card_deleted":
      return "−";
    case "card_moved":
      return "→";
    case "column_added":
      return "▸";
    case "column_deleted":
      return "◂";
    case "board_renamed":
      return "✎";
    default:
      return "•";
  }
};

export const BoardActivityFeed = ({ boardId }: BoardActivityFeedProps) => {
  const [entries, setEntries] = useState<ActivityEntry[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    if (!isOpen) return;

    let active = true;
    const fetchActivity = async () => {
      try {
        const resp = await fetch(`/api/boards/${boardId}/activity?limit=30`, {
          credentials: "include",
        });
        if (resp.ok && active) {
          setEntries(await resp.json());
        }
      } catch {
        // ignore
      }
    };
    void fetchActivity();

    return () => {
      active = false;
    };
  }, [isOpen, boardId, refreshKey]);

  return (
    <div className="rounded-2xl border border-[var(--stroke)] bg-white/80 shadow-[var(--shadow)] backdrop-blur">
      <button
        type="button"
        onClick={() => setIsOpen((o) => !o)}
        className="flex w-full items-center justify-between px-5 py-4 text-left"
      >
        <span className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
          Activity Log
        </span>
        <span className="text-xs text-[var(--gray-text)]">
          {isOpen ? "▲" : "▼"}
        </span>
      </button>
      {isOpen && (
        <div className="border-t border-[var(--stroke)] px-5 py-4">
          {entries.length === 0 ? (
            <p className="text-xs text-[var(--gray-text)]">No activity yet.</p>
          ) : (
            <div className="space-y-3">
              {entries.map((entry) => (
                <div key={entry.id} className="flex items-start gap-3">
                  <span className="mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-[var(--surface)] text-[10px] font-bold text-[var(--primary-blue)]">
                    {actionIcon(entry.action)}
                  </span>
                  <div className="min-w-0">
                    <p className="text-xs text-[var(--navy-dark)]">
                      <span className="font-semibold text-[var(--primary-blue)]">
                        @{entry.username}
                      </span>{" "}
                      {actionLabel(entry)}
                    </p>
                    <p className="mt-0.5 text-[10px] text-[var(--gray-text)]">
                      {new Date(entry.created_at).toLocaleString()}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
          <button
            type="button"
            onClick={() => setRefreshKey((k) => k + 1)}
            className="mt-3 text-[10px] font-semibold uppercase tracking-wider text-[var(--primary-blue)] hover:underline"
          >
            Refresh
          </button>
        </div>
      )}
    </div>
  );
};
