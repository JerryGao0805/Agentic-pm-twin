"use client";

import { useMemo, useState, useEffect, useCallback } from "react";
import {
  DndContext,
  DragOverlay,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  closestCorners,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { KanbanColumn } from "@/components/KanbanColumn";
import { KanbanCardPreview } from "@/components/KanbanCardPreview";
import { AISidebarChat } from "@/components/AISidebarChat";
import { BoardActivityFeed } from "@/components/BoardActivityFeed";
import { createId, initialData, moveCard, type BoardData } from "@/lib/kanban";

const LOCAL_BOARD_KEY = "pm-local-board";
const canUseLocalFallback = process.env.NODE_ENV !== "production";

type BoardMode = "api" | "local";
type BoardStatus = "loading" | "ready" | "error";

type KanbanBoardProps = {
  boardId?: number | null;
};

const cloneInitialBoard = (): BoardData =>
  JSON.parse(JSON.stringify(initialData)) as BoardData;

const readLocalBoard = (): BoardData => {
  if (typeof window === "undefined") {
    return cloneInitialBoard();
  }

  const raw = window.localStorage.getItem(LOCAL_BOARD_KEY);
  if (!raw) {
    return cloneInitialBoard();
  }

  try {
    const parsed = JSON.parse(raw) as BoardData;
    if (
      !parsed ||
      !Array.isArray(parsed.columns) ||
      typeof parsed.cards !== "object" ||
      parsed.cards === null
    ) {
      return cloneInitialBoard();
    }
    return parsed;
  } catch {
    return cloneInitialBoard();
  }
};

const writeLocalBoard = (board: BoardData) => {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(LOCAL_BOARD_KEY, JSON.stringify(board));
};

export const KanbanBoard = ({ boardId }: KanbanBoardProps) => {
  const [boardMode, setBoardMode] = useState<BoardMode>("api");
  const [boardStatus, setBoardStatus] = useState<BoardStatus>("loading");
  const [board, setBoard] = useState<BoardData | null>(null);
  const [activeCardId, setActiveCardId] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  useEffect(() => {
    let active = true;

    const loadBoard = async () => {
      setLoadError(null);
      setBoardStatus("loading");

      try {
        const url = boardId ? `/api/boards/${boardId}` : "/api/board";
        const response = await fetch(url, { credentials: "include" });

        if (response.status === 404 && canUseLocalFallback) {
          if (!active) return;
          setBoardMode("local");
          setBoard(readLocalBoard());
          setBoardStatus("ready");
          return;
        }

        if (!response.ok) {
          throw new Error("Unable to load board.");
        }

        const payload = (await response.json()) as BoardData;
        if (!active) return;
        if (
          !payload ||
          !Array.isArray(payload.columns) ||
          typeof payload.cards !== "object" ||
          payload.cards === null
        ) {
          throw new Error("Invalid board data from API.");
        }
        setBoardMode("api");
        setBoard(payload);
        setBoardStatus("ready");
      } catch {
        if (!active) return;
        if (canUseLocalFallback) {
          setBoardMode("local");
          setBoard(readLocalBoard());
          setBoardStatus("ready");
        } else {
          setLoadError("Unable to load board.");
          setBoardStatus("error");
        }
      }
    };

    void loadBoard();

    return () => {
      active = false;
    };
  }, [boardId]);

  const persistBoard = useCallback(
    async (nextBoard: BoardData) => {
      setSaveError(null);

      if (boardMode === "local") {
        writeLocalBoard(nextBoard);
        return;
      }

      setIsSaving(true);
      try {
        const effectiveBoardId = boardId || nextBoard.id;
        const url = effectiveBoardId
          ? `/api/boards/${effectiveBoardId}`
          : "/api/board";
        const response = await fetch(url, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify(nextBoard),
        });

        if (!response.ok) {
          throw new Error("Unable to save board.");
        }
      } catch {
        setSaveError("Unable to save changes. Refresh and try again.");
      } finally {
        setIsSaving(false);
      }
    },
    [boardMode, boardId]
  );

  const applyBoardUpdate = useCallback(
    (updater: (previousBoard: BoardData) => BoardData) => {
      setBoard((previousBoard) => {
        if (!previousBoard) {
          return previousBoard;
        }

        const nextBoard = updater(previousBoard);
        queueMicrotask(() => void persistBoard(nextBoard));
        return nextBoard;
      });
    },
    [persistBoard]
  );

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 6 },
    }),
    useSensor(KeyboardSensor)
  );

  const cardsById = useMemo(() => board?.cards ?? {}, [board]);

  const handleDragStart = (event: DragStartEvent) => {
    setActiveCardId(String(event.active.id));
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveCardId(null);

    if (!over || active.id === over.id) {
      return;
    }

    applyBoardUpdate((previousBoard) => ({
      ...previousBoard,
      columns: moveCard(
        previousBoard.columns,
        String(active.id),
        String(over.id)
      ),
    }));
  };

  const handleRenameColumn = (columnId: string, title: string) => {
    applyBoardUpdate((previousBoard) => ({
      ...previousBoard,
      columns: previousBoard.columns.map((column) =>
        column.id === columnId ? { ...column, title } : column
      ),
    }));
  };

  const handleAddCard = (columnId: string, title: string, details: string) => {
    const id = createId("card");
    applyBoardUpdate((previousBoard) => ({
      ...previousBoard,
      cards: {
        ...previousBoard.cards,
        [id]: { id, title, details: details || "No details yet." },
      },
      columns: previousBoard.columns.map((column) =>
        column.id === columnId
          ? { ...column, cardIds: [...column.cardIds, id] }
          : column
      ),
    }));
  };

  const handleDeleteCard = (columnId: string, cardId: string) => {
    applyBoardUpdate((previousBoard) => ({
      ...previousBoard,
      cards: Object.fromEntries(
        Object.entries(previousBoard.cards).filter(([id]) => id !== cardId)
      ),
      columns: previousBoard.columns.map((column) =>
        column.id === columnId
          ? {
              ...column,
              cardIds: column.cardIds.filter((id) => id !== cardId),
            }
          : column
      ),
    }));
  };

  const handleUpdateCard = (cardId: string, updates: Partial<{ title: string; details: string; priority: "low" | "medium" | "high" | null; due_date: string | null; assignee: string | null; label_ids: string[] }>) => {
    applyBoardUpdate((previousBoard) => ({
      ...previousBoard,
      cards: {
        ...previousBoard.cards,
        [cardId]: { ...previousBoard.cards[cardId], ...updates },
      },
    }));
  };

  const handleAddColumn = () => {
    const id = createId("col");
    applyBoardUpdate((previousBoard) => ({
      ...previousBoard,
      columns: [...previousBoard.columns, { id, title: "New Column", cardIds: [] }],
    }));
  };

  const handleDeleteColumn = (columnId: string) => {
    applyBoardUpdate((previousBoard) => {
      const column = previousBoard.columns.find((c) => c.id === columnId);
      if (!column) return previousBoard;
      const cardIdsToRemove = new Set(column.cardIds);
      return {
        ...previousBoard,
        columns: previousBoard.columns.filter((c) => c.id !== columnId),
        cards: Object.fromEntries(
          Object.entries(previousBoard.cards).filter(
            ([id]) => !cardIdsToRemove.has(id)
          )
        ),
      };
    });
  };

  const handleAIBoardUpdate = useCallback(
    (nextBoard: BoardData, options: { persist: boolean }) => {
      setBoard(nextBoard);
      setActiveCardId((previousActiveCardId) =>
        previousActiveCardId && !nextBoard.cards[previousActiveCardId]
          ? null
          : previousActiveCardId
      );
      if (options.persist) {
        void persistBoard(nextBoard);
      }
    },
    [persistBoard]
  );

  if (boardStatus === "loading" || !board) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[var(--surface)] px-6">
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
          Loading board...
        </p>
      </main>
    );
  }

  if (boardStatus === "error") {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[var(--surface)] px-6">
        <p className="text-sm font-semibold text-[#b42318]" role="alert">
          {loadError ?? "Unable to load board."}
        </p>
      </main>
    );
  }

  const activeCard = activeCardId ? cardsById[activeCardId] : null;

  return (
    <div className="relative overflow-hidden">
      <div className="pointer-events-none absolute left-0 top-0 h-[420px] w-[420px] -translate-x-1/3 -translate-y-1/3 rounded-full bg-[radial-gradient(circle,_rgba(32,157,215,0.25)_0%,_rgba(32,157,215,0.05)_55%,_transparent_70%)]" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-[520px] w-[520px] translate-x-1/4 translate-y-1/4 rounded-full bg-[radial-gradient(circle,_rgba(117,57,145,0.18)_0%,_rgba(117,57,145,0.05)_55%,_transparent_75%)]" />

      <main className="relative mx-auto flex min-h-screen max-w-[1500px] flex-col gap-10 px-6 pb-16 pt-12">
        <header className="flex flex-col gap-6 rounded-[32px] border border-[var(--stroke)] bg-white/80 p-8 shadow-[var(--shadow)] backdrop-blur">
          <div className="flex flex-wrap items-start justify-between gap-6">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.35em] text-[var(--gray-text)]">
                Kanban Board
              </p>
              <h1 className="mt-3 font-display text-4xl font-semibold text-[var(--navy-dark)]">
                {board.name || "Kanban Studio"}
              </h1>
              <p className="mt-3 max-w-xl text-sm leading-6 text-[var(--gray-text)]">
                Drag cards between columns, add new columns, set priorities and due dates,
                and use the AI copilot to manage your board.
              </p>
            </div>
            <div className="rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] px-5 py-4">
              <p className="text-xs font-semibold uppercase tracking-[0.25em] text-[var(--gray-text)]">
                Sync
              </p>
              <p className="mt-2 text-lg font-semibold text-[var(--primary-blue)]">
                {boardMode === "local"
                  ? "Local fallback mode"
                  : isSaving
                    ? "Saving..."
                    : "All changes saved"}
              </p>
              {saveError ? (
                <p className="mt-2 text-xs font-semibold text-[#b42318]" role="alert">
                  {saveError}
                </p>
              ) : null}
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-4">
            {board.columns.map((column) => (
              <div
                key={column.id}
                className="flex items-center gap-2 rounded-full border border-[var(--stroke)] px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--navy-dark)]"
              >
                <span className="h-2 w-2 rounded-full bg-[var(--accent-yellow)]" />
                {column.title}
              </div>
            ))}
          </div>
        </header>

        <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
          <DndContext
            sensors={sensors}
            collisionDetection={closestCorners}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
          >
            <section className="overflow-x-auto">
              <div className="flex gap-6">
                {board.columns.map((column) => (
                  <KanbanColumn
                    key={column.id}
                    column={column}
                    cards={column.cardIds.map((cardId) => board.cards[cardId]).filter(Boolean)}
                    labels={board.labels}
                    boardId={board.id}
                    onRename={handleRenameColumn}
                    onAddCard={handleAddCard}
                    onDeleteCard={handleDeleteCard}
                    onUpdateCard={handleUpdateCard}
                    onDeleteColumn={
                      board.columns.length > 1
                        ? handleDeleteColumn
                        : undefined
                    }
                  />
                ))}
                <div className="flex min-w-[220px] flex-shrink-0 items-start">
                  <button
                    type="button"
                    onClick={handleAddColumn}
                    className="w-full rounded-3xl border border-dashed border-[var(--stroke)] bg-[var(--surface-strong)] px-4 py-8 text-center text-xs font-semibold uppercase tracking-[0.2em] text-[var(--primary-blue)] transition hover:border-[var(--primary-blue)]"
                    data-testid="add-column-button"
                  >
                    + Add Column
                  </button>
                </div>
              </div>
            </section>
            <DragOverlay>
              {activeCard ? (
                <div className="w-[260px]">
                  <KanbanCardPreview card={activeCard} />
                </div>
              ) : null}
            </DragOverlay>
          </DndContext>

          <div className="xl:block">
            <button
              type="button"
              onClick={() => setIsSidebarOpen((open) => !open)}
              className="mb-4 rounded-full border border-[var(--stroke)] px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--navy-dark)] transition hover:border-[var(--primary-blue)] hover:text-[var(--primary-blue)] xl:hidden"
            >
              {isSidebarOpen ? "Hide AI Copilot" : "Show AI Copilot"}
            </button>
            <div className={`${isSidebarOpen ? "block" : "hidden"} xl:block`}>
              <AISidebarChat board={board} onBoardUpdate={handleAIBoardUpdate} boardId={boardId ?? undefined} />
              {board.id ? (
                <div className="mt-4">
                  <BoardActivityFeed boardId={board.id} />
                </div>
              ) : null}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};
