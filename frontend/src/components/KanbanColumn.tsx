import { useState } from "react";
import clsx from "clsx";
import { useDroppable } from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";
import type { Card, Column, Label } from "@/lib/kanban";
import { KanbanCard } from "@/components/KanbanCard";
import { NewCardForm } from "@/components/NewCardForm";

type KanbanColumnProps = {
  column: Column;
  cards: Card[];
  labels?: Label[];
  boardId?: number;
  onRename: (columnId: string, title: string) => void;
  onAddCard: (columnId: string, title: string, details: string) => void;
  onDeleteCard: (columnId: string, cardId: string) => void;
  onUpdateCard: (cardId: string, updates: Partial<Card>) => void;
  onDeleteColumn?: (columnId: string) => void;
};

export const KanbanColumn = ({
  column,
  cards,
  labels = [],
  boardId,
  onRename,
  onAddCard,
  onDeleteCard,
  onUpdateCard,
  onDeleteColumn,
}: KanbanColumnProps) => {
  const { setNodeRef, isOver } = useDroppable({ id: column.id });
  const [localTitle, setLocalTitle] = useState(column.title);
  const [prevColumnTitle, setPrevColumnTitle] = useState(column.title);

  if (column.title !== prevColumnTitle) {
    setPrevColumnTitle(column.title);
    setLocalTitle(column.title);
  }

  return (
    <section
      ref={setNodeRef}
      className={clsx(
        "flex min-w-[220px] flex-shrink-0 min-h-[520px] flex-col rounded-3xl border border-[var(--stroke)] bg-[var(--surface-strong)] p-4 shadow-[var(--shadow)] transition lg:min-w-0 lg:flex-shrink",
        isOver && "ring-2 ring-[var(--accent-yellow)]"
      )}
      data-testid={`column-${column.id}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="w-full">
          <div className="flex items-center gap-3">
            <div className="h-2 w-10 rounded-full bg-[var(--accent-yellow)]" />
            <span className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
              {cards.length} cards
            </span>
          </div>
          <input
            value={localTitle}
            onChange={(event) => setLocalTitle(event.target.value)}
            onBlur={() => {
              if (localTitle !== column.title) {
                onRename(column.id, localTitle);
              }
            }}
            className="mt-3 w-full bg-transparent font-display text-lg font-semibold text-[var(--navy-dark)] outline-none"
            aria-label={`Column title: ${localTitle}`}
          />
        </div>
        {onDeleteColumn ? (
          <button
            type="button"
            onClick={() => onDeleteColumn(column.id)}
            className="mt-1 rounded-full border border-transparent px-2 py-1 text-xs font-semibold text-[var(--gray-text)] transition hover:border-[var(--stroke)] hover:text-[#b42318]"
            aria-label={`Delete column ${localTitle}`}
          >
            Delete
          </button>
        ) : null}
      </div>
      <div className="mt-4 flex flex-1 flex-col gap-3">
        <SortableContext items={column.cardIds} strategy={verticalListSortingStrategy}>
          {cards.map((card) => (
            <KanbanCard
              key={card.id}
              card={card}
              labels={labels}
              boardId={boardId}
              onDelete={(cardId) => onDeleteCard(column.id, cardId)}
              onUpdate={(updates) => onUpdateCard(card.id, updates)}
            />
          ))}
        </SortableContext>
        {cards.length === 0 && (
          <div className="flex flex-1 items-center justify-center rounded-2xl border border-dashed border-[var(--stroke)] px-3 py-6 text-center text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
            Drop a card here
          </div>
        )}
      </div>
      <NewCardForm
        onAdd={(title, details) => onAddCard(column.id, title, details)}
      />
    </section>
  );
};
