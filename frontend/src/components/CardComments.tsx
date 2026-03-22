"use client";

import { useCallback, useEffect, useState } from "react";

type Comment = {
  id: number;
  card_id: string;
  username: string;
  content: string;
  created_at: string;
};

type CardCommentsProps = {
  boardId: number;
  cardId: string;
};

export const CardComments = ({ boardId, cardId }: CardCommentsProps) => {
  const [comments, setComments] = useState<Comment[]>([]);
  const [newComment, setNewComment] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const loadComments = useCallback(async () => {
    try {
      const resp = await fetch(
        `/api/boards/${boardId}/cards/${cardId}/comments`,
        { credentials: "include" }
      );
      if (resp.ok) {
        setComments(await resp.json());
      }
    } catch {
      // ignore
    }
  }, [boardId, cardId]);

  useEffect(() => {
    void loadComments();
  }, [loadComments]);

  const handleSubmit = async () => {
    const content = newComment.trim();
    if (!content) return;

    setIsSubmitting(true);
    try {
      const resp = await fetch(
        `/api/boards/${boardId}/cards/${cardId}/comments`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify({ content }),
        }
      );
      if (resp.ok) {
        setNewComment("");
        await loadComments();
      }
    } catch {
      // ignore
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (commentId: number) => {
    try {
      await fetch(
        `/api/boards/${boardId}/cards/${cardId}/comments/${commentId}`,
        { method: "DELETE", credentials: "include" }
      );
      await loadComments();
    } catch {
      // ignore
    }
  };

  return (
    <div className="mt-3 border-t border-[var(--stroke)] pt-3">
      <p className="text-[10px] font-semibold uppercase tracking-wider text-[var(--gray-text)]">
        Comments ({comments.length})
      </p>
      {comments.length > 0 ? (
        <div className="mt-2 space-y-2">
          {comments.map((c) => (
            <div
              key={c.id}
              className="rounded-lg bg-[var(--surface)] px-3 py-2 text-xs"
            >
              <div className="flex items-center justify-between">
                <span className="font-semibold text-[var(--primary-blue)]">
                  @{c.username}
                </span>
                <div className="flex items-center gap-2">
                  <span className="text-[var(--gray-text)]">
                    {new Date(c.created_at).toLocaleDateString()}
                  </span>
                  <button
                    type="button"
                    onClick={() => handleDelete(c.id)}
                    className="text-[var(--gray-text)] hover:text-[#b42318]"
                  >
                    x
                  </button>
                </div>
              </div>
              <p className="mt-1 text-[var(--navy-dark)]">{c.content}</p>
            </div>
          ))}
        </div>
      ) : null}
      <div className="mt-2 flex gap-2">
        <input
          type="text"
          value={newComment}
          onChange={(e) => setNewComment(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSubmit();
            }
          }}
          placeholder="Add a comment..."
          className="flex-1 rounded-lg border border-[var(--stroke)] bg-white px-2 py-1 text-xs text-[var(--navy-dark)] outline-none focus:border-[var(--primary-blue)]"
        />
        <button
          type="button"
          onClick={handleSubmit}
          disabled={isSubmitting || !newComment.trim()}
          className="rounded-lg bg-[var(--primary-blue)] px-3 py-1 text-xs font-semibold text-white disabled:opacity-50"
        >
          Post
        </button>
      </div>
    </div>
  );
};
