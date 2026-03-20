import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AISidebarChat } from "@/components/AISidebarChat";
import { initialData, type BoardData } from "@/lib/kanban";

const jsonResponse = (payload: unknown, status = 200) =>
  new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });

const cloneInitialBoard = (): BoardData =>
  JSON.parse(JSON.stringify(initialData)) as BoardData;

describe("AISidebarChat", () => {
  beforeEach(() => {
    window.localStorage.removeItem("pm-local-chat-history");
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("renders chat history from the API", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/ai/chat/history") {
        return Promise.resolve(
          jsonResponse([{ role: "assistant", content: "How can I help?" }])
        );
      }
      return Promise.resolve(new Response("Not Found", { status: 404 }));
    });
    vi.stubGlobal("fetch", fetchMock);

    render(
      <AISidebarChat
        board={cloneInitialBoard()}
        onBoardUpdate={vi.fn()}
      />
    );

    expect(await screen.findByText("How can I help?")).toBeInTheDocument();
    expect(screen.getByText("Connected")).toBeInTheDocument();
  });

  it("sends a message and applies API board updates", async () => {
    const board = cloneInitialBoard();
    const updatedBoard = cloneInitialBoard();
    updatedBoard.columns[0] = { ...updatedBoard.columns[0], title: "Intake" };

    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/ai/chat/history") {
        return Promise.resolve(jsonResponse([]));
      }
      if (url === "/api/ai/chat" && init?.method === "POST") {
        return Promise.resolve(
          jsonResponse({
            assistant_message: "Renamed Backlog to Intake.",
            board: updatedBoard,
            board_updated: true,
            board_update_error: null,
            chat_history: [
              { role: "user", content: "Rename backlog to Intake" },
              { role: "assistant", content: "Renamed Backlog to Intake." },
            ],
          })
        );
      }
      return Promise.resolve(new Response("Not Found", { status: 404 }));
    });
    vi.stubGlobal("fetch", fetchMock);

    const onBoardUpdate = vi.fn();
    render(
      <AISidebarChat board={board} onBoardUpdate={onBoardUpdate} />
    );

    await screen.findByText(/ask for planning help/i);

    await userEvent.type(
      screen.getByLabelText(/ask the assistant/i),
      "Rename backlog to Intake"
    );
    await userEvent.click(screen.getByRole("button", { name: /send/i }));

    expect(await screen.findByText("Renamed Backlog to Intake.")).toBeInTheDocument();
    expect(onBoardUpdate).toHaveBeenCalledWith(updatedBoard, { persist: false });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/ai/chat",
      expect.objectContaining({
        method: "POST",
        credentials: "include",
      })
    );
  });

  it("shows API errors when send fails", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/ai/chat/history") {
        return Promise.resolve(jsonResponse([]));
      }
      if (url === "/api/ai/chat" && init?.method === "POST") {
        return Promise.resolve(
          jsonResponse({ detail: "AI response did not match expected schema." }, 502)
        );
      }
      return Promise.resolve(new Response("Not Found", { status: 404 }));
    });
    vi.stubGlobal("fetch", fetchMock);

    const onBoardUpdate = vi.fn();
    render(
      <AISidebarChat
        board={cloneInitialBoard()}
        onBoardUpdate={onBoardUpdate}
      />
    );

    await screen.findByText(/ask for planning help/i);

    await userEvent.type(screen.getByLabelText(/ask the assistant/i), "Help");
    await userEvent.click(screen.getByRole("button", { name: /send/i }));

    expect(
      await screen.findByText("AI response did not match expected schema.")
    ).toBeInTheDocument();
    expect(onBoardUpdate).not.toHaveBeenCalled();
    expect(screen.getByText("Help")).toBeInTheDocument();
  });

  it("uses boardId in API URLs when provided", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/ai/chat/history?board_id=42") {
        return Promise.resolve(jsonResponse([]));
      }
      return Promise.resolve(new Response("Not Found", { status: 404 }));
    });
    vi.stubGlobal("fetch", fetchMock);

    render(
      <AISidebarChat
        board={cloneInitialBoard()}
        onBoardUpdate={vi.fn()}
        boardId={42}
      />
    );

    await screen.findByText(/ask for planning help/i);

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/ai/chat/history?board_id=42",
      expect.objectContaining({ credentials: "include" })
    );
  });
});
