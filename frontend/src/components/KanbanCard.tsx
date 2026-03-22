import { memo, useState } from "react";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import clsx from "clsx";
import type { Card, Label } from "@/lib/kanban";
import { priorityLabel, priorityColor, labelColor } from "@/lib/kanban";
import { CardComments } from "@/components/CardComments";

type KanbanCardProps = {
  card: Card;
  labels?: Label[];
  boardId?: number;
  onDelete: (cardId: string) => void;
  onUpdate: (updates: Partial<Card>) => void;
};

export const KanbanCard = memo(function KanbanCard({ card, labels = [], boardId, onDelete, onUpdate }: KanbanCardProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: card.id });
  const [isExpanded, setIsExpanded] = useState(false);

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <article
      ref={setNodeRef}
      style={style}
      className={clsx(
        "rounded-2xl border border-transparent bg-white px-4 py-4 shadow-[0_12px_24px_rgba(3,33,71,0.08)]",
        "transition-all duration-150",
        isDragging && "opacity-60 shadow-[0_18px_32px_rgba(3,33,71,0.16)]"
      )}
      {...attributes}
      {...listeners}
      data-testid={`card-${card.id}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <h4 className="font-display text-base font-semibold text-[var(--navy-dark)]">
            {card.title}
          </h4>
          <p className="mt-2 text-sm leading-6 text-[var(--gray-text)]">
            {card.details}
          </p>
          {(card.label_ids ?? []).length > 0 && labels.length > 0 ? (
            <div className="mt-2 flex flex-wrap gap-1">
              {(card.label_ids ?? []).map((lid) => {
                const label = labels.find((l) => l.id === lid);
                if (!label) return null;
                return (
                  <span
                    key={lid}
                    className={clsx(
                      "rounded-full border px-2 py-0.5 text-[10px] font-semibold",
                      labelColor(label.color)
                    )}
                  >
                    {label.name}
                  </span>
                );
              })}
            </div>
          ) : null}
          <div className="mt-2 flex flex-wrap items-center gap-2">
            {card.priority ? (
              <span
                className={clsx(
                  "rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider",
                  priorityColor(card.priority)
                )}
              >
                {priorityLabel(card.priority)}
              </span>
            ) : null}
            {card.due_date ? (
              <span className="text-[10px] font-semibold text-[var(--gray-text)]">
                Due: {card.due_date}
              </span>
            ) : null}
            {card.assignee ? (
              <span className="text-[10px] font-semibold text-[var(--primary-blue)]">
                @{card.assignee}
              </span>
            ) : null}
          </div>
        </div>
        <div className="flex flex-col gap-1">
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              setIsExpanded(!isExpanded);
            }}
            className="rounded-full border border-transparent px-2 py-1 text-xs font-semibold text-[var(--gray-text)] transition hover:border-[var(--stroke)] hover:text-[var(--navy-dark)]"
            aria-label={`Edit card ${card.title}`}
          >
            Edit
          </button>
          <button
            type="button"
            onClick={() => onDelete(card.id)}
            className="rounded-full border border-transparent px-2 py-1 text-xs font-semibold text-[var(--gray-text)] transition hover:border-[var(--stroke)] hover:text-[var(--navy-dark)]"
            aria-label={`Delete ${card.title}`}
          >
            Remove
          </button>
        </div>
      </div>
      {isExpanded ? (
        <div
          className="mt-3 space-y-2 border-t border-[var(--stroke)] pt-3"
          onClick={(e) => e.stopPropagation()}
          onPointerDown={(e) => e.stopPropagation()}
        >
          <div>
            <label className="text-[10px] font-semibold uppercase tracking-wider text-[var(--gray-text)]">
              Priority
            </label>
            <select
              value={card.priority || ""}
              onChange={(e) =>
                onUpdate({
                  priority: (e.target.value || null) as Card["priority"],
                })
              }
              className="mt-1 w-full rounded-lg border border-[var(--stroke)] bg-white px-2 py-1 text-xs text-[var(--navy-dark)] outline-none"
            >
              <option value="">None</option>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>
          </div>
          <div>
            <label className="text-[10px] font-semibold uppercase tracking-wider text-[var(--gray-text)]">
              Due Date
            </label>
            <input
              type="date"
              value={card.due_date || ""}
              onChange={(e) =>
                onUpdate({ due_date: e.target.value || null })
              }
              className="mt-1 w-full rounded-lg border border-[var(--stroke)] bg-white px-2 py-1 text-xs text-[var(--navy-dark)] outline-none"
            />
          </div>
          <div>
            <label className="text-[10px] font-semibold uppercase tracking-wider text-[var(--gray-text)]">
              Assignee
            </label>
            <input
              type="text"
              value={card.assignee || ""}
              onChange={(e) =>
                onUpdate({ assignee: e.target.value || null })
              }
              placeholder="username"
              className="mt-1 w-full rounded-lg border border-[var(--stroke)] bg-white px-2 py-1 text-xs text-[var(--navy-dark)] outline-none"
            />
          </div>
          {labels.length > 0 ? (
            <div>
              <label className="text-[10px] font-semibold uppercase tracking-wider text-[var(--gray-text)]">
                Labels
              </label>
              <div className="mt-1 flex flex-wrap gap-1">
                {labels.map((label) => {
                  const isSelected = (card.label_ids ?? []).includes(label.id);
                  return (
                    <button
                      key={label.id}
                      type="button"
                      onClick={() => {
                        const current = card.label_ids ?? [];
                        const next = isSelected
                          ? current.filter((id) => id !== label.id)
                          : [...current, label.id];
                        onUpdate({ label_ids: next });
                      }}
                      className={clsx(
                        "rounded-full border px-2 py-0.5 text-[10px] font-semibold transition",
                        isSelected
                          ? labelColor(label.color)
                          : "border-[var(--stroke)] text-[var(--gray-text)] opacity-50 hover:opacity-100"
                      )}
                    >
                      {label.name}
                    </button>
                  );
                })}
              </div>
            </div>
          ) : null}
          {boardId ? (
            <CardComments boardId={boardId} cardId={card.id} />
          ) : null}
        </div>
      ) : null}
    </article>
  );
});
