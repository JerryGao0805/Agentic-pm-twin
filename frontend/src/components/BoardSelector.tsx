"use client";

import { useCallback, useEffect, useState } from "react";
import type { BoardSummary } from "@/lib/kanban";
import { TemplateSelector } from "@/components/TemplateSelector";

type BoardSelectorProps = {
  activeBoardId: number | null;
  onSelectBoard: (boardId: number | null) => void;
};

export const BoardSelector = ({
  activeBoardId,
  onSelectBoard,
}: BoardSelectorProps) => {
  const [boards, setBoards] = useState<BoardSummary[]>([]);
  const [isCreating, setIsCreating] = useState(false);
  const [newBoardName, setNewBoardName] = useState("");
  const [newBoardTemplate, setNewBoardTemplate] = useState("");
  const [error, setError] = useState<string | null>(null);

  const loadBoards = useCallback(async () => {
    try {
      const response = await fetch("/api/boards", { credentials: "include" });
      if (!response.ok) return;
      const data = (await response.json()) as BoardSummary[];
      setBoards(data);
      return data;
    } catch {
      return null;
    }
  }, []);

  useEffect(() => {
    void loadBoards().then((data) => {
      if (data && data.length > 0 && activeBoardId === null) {
        onSelectBoard(data[0].id);
      }
    });
    // Only run on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleCreateBoard = async () => {
    const name = newBoardName.trim();
    if (!name) return;

    setError(null);
    try {
      const response = await fetch("/api/boards", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ name, ...(newBoardTemplate ? { template: newBoardTemplate } : {}) }),
      });

      if (!response.ok) {
        setError("Failed to create board.");
        return;
      }

      const newBoard = (await response.json()) as { id: number; name: string };
      setNewBoardName("");
      setNewBoardTemplate("");
      setIsCreating(false);
      await loadBoards();
      onSelectBoard(newBoard.id);
    } catch {
      setError("Failed to create board.");
    }
  };

  const handleDeleteBoard = async (boardId: number) => {
    try {
      const response = await fetch(`/api/boards/${boardId}`, {
        method: "DELETE",
        credentials: "include",
      });
      if (response.ok || response.status === 204) {
        const remaining = boards.filter((b) => b.id !== boardId);
        setBoards(remaining);
        if (activeBoardId === boardId) {
          onSelectBoard(remaining.length > 0 ? remaining[0].id : null);
        }
      }
    } catch {
      // Silently fail
    }
  };

  return (
    <div className="mx-auto max-w-[1500px] px-6 pt-4">
      <div className="flex flex-wrap items-center gap-3">
        <span className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
          Boards
        </span>
        {boards.map((board) => (
          <div key={board.id} className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => onSelectBoard(board.id)}
              className={`rounded-full border px-4 py-2 text-xs font-semibold uppercase tracking-[0.15em] transition ${
                activeBoardId === board.id
                  ? "border-[var(--primary-blue)] bg-[var(--primary-blue)] text-white"
                  : "border-[var(--stroke)] text-[var(--navy-dark)] hover:border-[var(--primary-blue)]"
              }`}
              data-testid={`board-tab-${board.id}`}
            >
              {board.name}
            </button>
            {boards.length > 1 ? (
              <button
                type="button"
                onClick={() => handleDeleteBoard(board.id)}
                className="rounded-full px-1 text-xs text-[var(--gray-text)] hover:text-[#b42318]"
                aria-label={`Delete board ${board.name}`}
              >
                x
              </button>
            ) : null}
          </div>
        ))}
        {isCreating ? (
          <div className="flex items-center gap-2">
            <TemplateSelector value={newBoardTemplate} onChange={setNewBoardTemplate} />
            <input
              value={newBoardName}
              onChange={(e) => setNewBoardName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleCreateBoard();
                if (e.key === "Escape") {
                  setIsCreating(false);
                  setNewBoardName("");
                  setNewBoardTemplate("");
                }
              }}
              placeholder="Board name"
              className="rounded-xl border border-[var(--stroke)] bg-white px-3 py-1.5 text-sm text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
              autoFocus
            />
            <button
              type="button"
              onClick={handleCreateBoard}
              className="rounded-full bg-[var(--secondary-purple)] px-3 py-1.5 text-xs font-semibold text-white hover:brightness-110"
            >
              Create
            </button>
            <button
              type="button"
              onClick={() => {
                setIsCreating(false);
                setNewBoardName("");
                setNewBoardTemplate("");
              }}
              className="text-xs text-[var(--gray-text)] hover:text-[var(--navy-dark)]"
            >
              Cancel
            </button>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => setIsCreating(true)}
            className="rounded-full border border-dashed border-[var(--stroke)] px-4 py-2 text-xs font-semibold text-[var(--primary-blue)] hover:border-[var(--primary-blue)]"
            data-testid="create-board-button"
          >
            + New Board
          </button>
        )}
      </div>
      {error ? (
        <p className="mt-2 text-xs font-semibold text-[#b42318]">{error}</p>
      ) : null}
    </div>
  );
};
