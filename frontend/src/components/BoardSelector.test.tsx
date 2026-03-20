import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BoardSelector } from "@/components/BoardSelector";

const jsonResponse = (payload: unknown, status = 200) =>
  new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });

describe("BoardSelector", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("renders board tabs from API", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/boards") {
        return Promise.resolve(
          jsonResponse([
            { id: 1, name: "Sprint 1", updated_at: "2026-01-01" },
            { id: 2, name: "Backlog", updated_at: "2026-01-02" },
          ])
        );
      }
      return Promise.resolve(new Response("Not Found", { status: 404 }));
    });
    vi.stubGlobal("fetch", fetchMock);

    const onSelectBoard = vi.fn();
    render(
      <BoardSelector activeBoardId={1} onSelectBoard={onSelectBoard} />
    );

    expect(await screen.findByTestId("board-tab-1")).toBeInTheDocument();
    expect(screen.getByTestId("board-tab-2")).toBeInTheDocument();
    expect(screen.getByTestId("board-tab-1")).toHaveTextContent("Sprint 1");
    expect(screen.getByTestId("board-tab-2")).toHaveTextContent("Backlog");
  });

  it("auto-selects first board when activeBoardId is null", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/boards") {
        return Promise.resolve(
          jsonResponse([
            { id: 5, name: "My Board", updated_at: "2026-01-01" },
          ])
        );
      }
      return Promise.resolve(new Response("Not Found", { status: 404 }));
    });
    vi.stubGlobal("fetch", fetchMock);

    const onSelectBoard = vi.fn();
    render(
      <BoardSelector activeBoardId={null} onSelectBoard={onSelectBoard} />
    );

    await screen.findByTestId("board-tab-5");
    expect(onSelectBoard).toHaveBeenCalledWith(5);
  });

  it("shows new board button", async () => {
    const fetchMock = vi.fn(() =>
      Promise.resolve(jsonResponse([]))
    );
    vi.stubGlobal("fetch", fetchMock);

    render(
      <BoardSelector activeBoardId={null} onSelectBoard={vi.fn()} />
    );

    expect(await screen.findByTestId("create-board-button")).toBeInTheDocument();
  });

  it("creates a new board", async () => {
    const boards = [{ id: 1, name: "Existing", updated_at: "2026-01-01" }];
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/boards" && (!init || init.method !== "POST")) {
        return Promise.resolve(jsonResponse(boards));
      }
      if (url === "/api/boards" && init?.method === "POST") {
        const newBoard = { id: 2, name: "New Board", columns: [], cards: {} };
        boards.push({ id: 2, name: "New Board", updated_at: "2026-01-01" });
        return Promise.resolve(jsonResponse(newBoard, 201));
      }
      return Promise.resolve(new Response("Not Found", { status: 404 }));
    });
    vi.stubGlobal("fetch", fetchMock);

    const onSelectBoard = vi.fn();
    render(
      <BoardSelector activeBoardId={1} onSelectBoard={onSelectBoard} />
    );

    await screen.findByTestId("board-tab-1");
    await userEvent.click(screen.getByTestId("create-board-button"));

    const input = screen.getByPlaceholderText("Board name");
    await userEvent.type(input, "New Board");
    await userEvent.click(screen.getByRole("button", { name: /create/i }));

    expect(onSelectBoard).toHaveBeenCalledWith(2);
  });

  it("deletes a board", async () => {
    const fetchMock = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/boards" && (!init || !init.method || init.method === "GET")) {
        return Promise.resolve(
          jsonResponse([
            { id: 1, name: "Board A", updated_at: "2026-01-01" },
            { id: 2, name: "Board B", updated_at: "2026-01-02" },
          ])
        );
      }
      if (url === "/api/boards/2" && init?.method === "DELETE") {
        return Promise.resolve(new Response(null, { status: 204 }));
      }
      return Promise.resolve(new Response("Not Found", { status: 404 }));
    });
    vi.stubGlobal("fetch", fetchMock);

    const onSelectBoard = vi.fn();
    render(
      <BoardSelector activeBoardId={2} onSelectBoard={onSelectBoard} />
    );

    await screen.findByTestId("board-tab-1");
    const deleteButton = screen.getByRole("button", {
      name: /delete board board b/i,
    });
    await userEvent.click(deleteButton);

    // Should select first remaining board since active was deleted
    expect(onSelectBoard).toHaveBeenCalledWith(1);
  });

  it("clicking a board tab calls onSelectBoard", async () => {
    const fetchMock = vi.fn(() =>
      Promise.resolve(
        jsonResponse([
          { id: 1, name: "Board A", updated_at: "2026-01-01" },
          { id: 2, name: "Board B", updated_at: "2026-01-02" },
        ])
      )
    );
    vi.stubGlobal("fetch", fetchMock);

    const onSelectBoard = vi.fn();
    render(
      <BoardSelector activeBoardId={1} onSelectBoard={onSelectBoard} />
    );

    await screen.findByTestId("board-tab-2");
    await userEvent.click(screen.getByTestId("board-tab-2"));

    expect(onSelectBoard).toHaveBeenCalledWith(2);
  });
});
