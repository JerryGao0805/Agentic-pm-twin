"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import type { BoardData } from "@/lib/kanban";

type ChatRole = "user" | "assistant";

type ChatMessage = {
  role: ChatRole;
  content: string;
};

type ChatMode = "api" | "local";

type AIChatResponse = {
  assistant_message: string;
  board: BoardData;
  board_updated: boolean;
  board_update_error: string | null;
  chat_history: ChatMessage[];
};

type BoardUpdateOptions = {
  persist: boolean;
};

type AISidebarChatProps = {
  board: BoardData;
  onBoardUpdate: (nextBoard: BoardData, options: BoardUpdateOptions) => void;
  boardId?: number;
};

const LOCAL_CHAT_KEY = "pm-local-chat-history";
const canUseLocalFallback = process.env.NODE_ENV !== "production";

const cloneBoard = (board: BoardData): BoardData =>
  JSON.parse(JSON.stringify(board)) as BoardData;

const parseMessages = (value: unknown): ChatMessage[] => {
  if (!Array.isArray(value)) {
    return [];
  }

  const messages: ChatMessage[] = [];
  for (const entry of value) {
    if (!entry || typeof entry !== "object") {
      continue;
    }

    const role = (entry as { role?: unknown }).role;
    const content = (entry as { content?: unknown }).content;
    if ((role === "user" || role === "assistant") && typeof content === "string") {
      const trimmed = content.trim();
      if (trimmed) {
        messages.push({ role, content: trimmed });
      }
    }
  }

  return messages;
};

const readLocalMessages = (): ChatMessage[] => {
  if (typeof window === "undefined") {
    return [];
  }

  const raw = window.localStorage.getItem(LOCAL_CHAT_KEY);
  if (!raw) {
    return [];
  }

  try {
    return parseMessages(JSON.parse(raw));
  } catch {
    return [];
  }
};

const writeLocalMessages = (messages: ChatMessage[]) => {
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(LOCAL_CHAT_KEY, JSON.stringify(messages));
};

const resolveColumnId = (board: BoardData, target: string): string | null => {
  const normalized = target.trim().toLowerCase();
  if (!normalized) {
    return null;
  }

  const aliasMap: Record<string, string> = {
    backlog: "col-backlog",
    discovery: "col-discovery",
    progress: "col-progress",
    "in progress": "col-progress",
    review: "col-review",
    done: "col-done",
  };

  if (aliasMap[normalized]) {
    return aliasMap[normalized];
  }

  const byId = board.columns.find((column) => column.id.toLowerCase() === normalized);
  if (byId) {
    return byId.id;
  }

  const byTitle = board.columns.find(
    (column) => column.title.trim().toLowerCase() === normalized
  );
  if (byTitle) {
    return byTitle.id;
  }

  return null;
};

const runLocalAssistant = (
  board: BoardData,
  userMessage: string
): { assistantMessage: string; board: BoardData; boardUpdated: boolean } => {
  const renameMatch = userMessage.match(
    /rename\s+(?:the\s+)?(.+?)\s+(?:column\s+)?to\s+["'“”]?(.+?)["'“”]?\s*[.!?]?$/i
  );

  if (renameMatch) {
    const sourceRaw = renameMatch[1]?.replace(/\s+column\s*$/i, "") ?? "";
    const nextTitle = renameMatch[2]?.trim() ?? "";
    const columnId = resolveColumnId(board, sourceRaw);

    if (!columnId) {
      return {
        assistantMessage: `I could not find a column named \"${sourceRaw.trim()}\".`,
        board,
        boardUpdated: false,
      };
    }

    if (!nextTitle) {
      return {
        assistantMessage: "Tell me the new column title after 'to'.",
        board,
        boardUpdated: false,
      };
    }

    const nextBoard = cloneBoard(board);
    const sourceTitle =
      nextBoard.columns.find((column) => column.id === columnId)?.title ??
      sourceRaw.trim();
    nextBoard.columns = nextBoard.columns.map((column) =>
      column.id === columnId ? { ...column, title: nextTitle } : column
    );

    return {
      assistantMessage: `Renamed ${sourceTitle} to ${nextTitle}.`,
      board: nextBoard,
      boardUpdated: true,
    };
  }

  return {
    assistantMessage:
      "Local mode supports simple rename requests like 'Rename backlog to Intake'.",
    board,
    boardUpdated: false,
  };
};

const normalizeError = (error: unknown): string => {
  if (error instanceof Error && error.message) {
    return error.message;
  }
  return "Unable to send message. Try again.";
};

const isNetworkError = (error: unknown): boolean => error instanceof TypeError;

export const AISidebarChat = ({ board, onBoardUpdate, boardId }: AISidebarChatProps) => {
  const [chatMode, setChatMode] = useState<ChatMode>("api");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [messageInput, setMessageInput] = useState("");
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [sendError, setSendError] = useState<string | null>(null);
  const [boardWarning, setBoardWarning] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    const loadHistory = async () => {
      setHistoryError(null);
      setIsLoadingHistory(true);

      try {
        const historyUrl = boardId
          ? `/api/ai/chat/history?board_id=${boardId}`
          : "/api/ai/chat/history";
        const response = await fetch(historyUrl, {
          credentials: "include",
        });

        if (response.status === 404 && canUseLocalFallback) {
          if (!active) {
            return;
          }
          setChatMode("local");
          setMessages(readLocalMessages());
          return;
        }

        if (!response.ok) {
          throw new Error("Unable to load chat history.");
        }

        const payload = parseMessages(await response.json());
        if (!active) {
          return;
        }

        setChatMode("api");
        setMessages(payload);
      } catch (error) {
        if (!active) {
          return;
        }

        if (canUseLocalFallback && isNetworkError(error)) {
          setChatMode("local");
          setMessages(readLocalMessages());
        } else {
          setHistoryError("Unable to load chat history.");
        }
      } finally {
        if (active) {
          setIsLoadingHistory(false);
        }
      }
    };

    void loadHistory();

    return () => {
      active = false;
    };
  }, [boardId]);

  const applyLocalResponse = useCallback(
    (userMessage: string, baseMessages: ChatMessage[]) => {
      const localResult = runLocalAssistant(board, userMessage);
      const nextMessages = [
        ...baseMessages,
        { role: "assistant", content: localResult.assistantMessage } as const,
      ];

      setMessages(nextMessages);
      writeLocalMessages(nextMessages);

      if (localResult.boardUpdated) {
        onBoardUpdate(localResult.board, { persist: true });
      }
      setBoardWarning(null);
      return nextMessages;
    },
    [board, onBoardUpdate]
  );

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (isSending) {
      return;
    }

    const trimmedMessage = messageInput.trim();
    if (!trimmedMessage) {
      setSendError("Type a message before sending.");
      return;
    }

    setMessageInput("");
    setSendError(null);
    setBoardWarning(null);

    const userEntry: ChatMessage = { role: "user", content: trimmedMessage };
    const baseMessages = [...messages, userEntry];
    setMessages(baseMessages);

    if (chatMode === "local") {
      applyLocalResponse(trimmedMessage, baseMessages);
      return;
    }

    setIsSending(true);
    try {
      const chatUrl = boardId
        ? `/api/ai/chat?board_id=${boardId}`
        : "/api/ai/chat";
      const response = await fetch(chatUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ message: trimmedMessage }),
      });

      if (response.status === 404 && canUseLocalFallback) {
        setChatMode("local");
        applyLocalResponse(trimmedMessage, baseMessages);
        return;
      }

      if (!response.ok) {
        let detail = "Unable to send message. Try again.";
        try {
          const errorPayload = (await response.json()) as { detail?: string };
          if (typeof errorPayload.detail === "string" && errorPayload.detail.trim()) {
            detail = errorPayload.detail;
          }
        } catch {
          detail = "Unable to send message. Try again.";
        }
        throw new Error(detail);
      }

      const payload = (await response.json()) as AIChatResponse;
      const nextMessages = parseMessages(payload.chat_history);
      setMessages(nextMessages);

      if (
        payload.board_updated &&
        payload.board &&
        Array.isArray(payload.board.columns) &&
        typeof payload.board.cards === "object" &&
        payload.board.cards !== null
      ) {
        onBoardUpdate(payload.board, { persist: false });
      }
      setBoardWarning(payload.board_update_error);
    } catch (error) {
      if (canUseLocalFallback && isNetworkError(error)) {
        setChatMode("local");
        applyLocalResponse(trimmedMessage, baseMessages);
      } else {
        setSendError(normalizeError(error));
      }
    } finally {
      setIsSending(false);
    }
  };

  return (
    <aside
      className="flex h-full min-h-[520px] flex-col rounded-3xl border border-[var(--stroke)] bg-white/90 p-5 shadow-[var(--shadow)] backdrop-blur"
      data-testid="ai-chat-sidebar"
    >
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.25em] text-[var(--gray-text)]">
            AI Assistant
          </p>
          <h2 className="mt-2 font-display text-2xl font-semibold text-[var(--navy-dark)]">
            Copilot Chat
          </h2>
        </div>
        <p className="rounded-full border border-[var(--stroke)] px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
          {chatMode === "local" ? "Local" : "Connected"}
        </p>
      </div>

      <div className="mt-4 flex-1 overflow-y-auto rounded-2xl border border-[var(--stroke)] bg-[var(--surface)]/70 p-3">
        {isLoadingHistory ? (
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
            Loading chat...
          </p>
        ) : messages.length === 0 ? (
          <p className="text-sm leading-6 text-[var(--gray-text)]">
            Ask for planning help or request a board update.
          </p>
        ) : (
          <ol className="space-y-3" aria-live="polite" data-testid="ai-chat-messages">
            {messages.map((message, index) => {
              const isUser = message.role === "user";
              return (
                <li
                  key={`${message.role}-${index}`}
                  className={`flex ${isUser ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[92%] rounded-2xl px-3 py-2 text-sm leading-6 ${
                      isUser
                        ? "bg-[var(--secondary-purple)] text-white"
                        : "border border-[var(--stroke)] bg-white text-[var(--navy-dark)]"
                    }`}
                  >
                    {message.content}
                  </div>
                </li>
              );
            })}
          </ol>
        )}
      </div>

      <form onSubmit={handleSubmit} className="mt-4 space-y-3">
        <label
          htmlFor="ai-chat-input"
          className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]"
        >
          Ask the assistant
        </label>
        <textarea
          id="ai-chat-input"
          value={messageInput}
          onChange={(event) => setMessageInput(event.target.value)}
          placeholder="Try: Rename backlog to Intake"
          rows={3}
          className="w-full resize-none rounded-2xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)]"
          disabled={isSending}
        />
        {historyError ? (
          <p className="text-xs font-semibold text-[#b42318]" role="alert">
            {historyError}
          </p>
        ) : null}
        {sendError ? (
          <p className="text-xs font-semibold text-[#b42318]" role="alert">
            {sendError}
          </p>
        ) : null}
        {boardWarning ? (
          <p className="text-xs font-semibold text-[#b54708]" role="status">
            {boardWarning}
          </p>
        ) : null}
        <button
          type="submit"
          className="w-full rounded-full bg-[var(--secondary-purple)] px-4 py-3 text-xs font-semibold uppercase tracking-[0.2em] text-white transition hover:brightness-110 disabled:opacity-60"
          disabled={isSending}
        >
          {isSending ? "Thinking..." : "Send"}
        </button>
      </form>
    </aside>
  );
};
