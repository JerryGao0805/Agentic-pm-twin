import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { KanbanBoard } from "@/components/KanbanBoard";
import { initialData, type BoardData } from "@/lib/kanban";

const jsonResponse = (payload: unknown, status = 200) =>
  new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });

const cloneInitialBoard = (): BoardData =>
  JSON.parse(JSON.stringify(initialData)) as BoardData;

const getFirstColumn = () => screen.getAllByTestId(/column-/i)[0];

describe("KanbanBoard", () => {
  beforeEach(() => {
    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/board") {
        return Promise.resolve(jsonResponse(cloneInitialBoard()));
      }
      if (url === "/api/ai/chat/history") {
        return Promise.resolve(jsonResponse([]));
      }
      return Promise.resolve(new Response("Not Found", { status: 404 }));
    });
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    window.localStorage.removeItem("pm-local-board");
    window.localStorage.removeItem("pm-local-chat-history");
  });

  it("renders five columns", async () => {
    render(<KanbanBoard />);
    expect(await screen.findAllByTestId(/^column-col/i)).toHaveLength(5);
  });

  it("renames a column", async () => {
    render(<KanbanBoard />);
    await screen.findAllByTestId(/column-/i);

    const column = getFirstColumn();
    const input = within(column).getByLabelText(/^Column title:/i);
    await userEvent.clear(input);
    await userEvent.type(input, "New Name");

    expect(input).toHaveValue("New Name");
  });

  it("adds and removes a card", async () => {
    render(<KanbanBoard />);
    await screen.findAllByTestId(/column-/i);

    const column = getFirstColumn();
    const addButton = within(column).getByRole("button", {
      name: /add a card/i,
    });
    await userEvent.click(addButton);

    const titleInput = within(column).getByPlaceholderText(/card title/i);
    await userEvent.type(titleInput, "New card");
    const detailsInput = within(column).getByPlaceholderText(/details/i);
    await userEvent.type(detailsInput, "Notes");

    await userEvent.click(within(column).getByRole("button", { name: /add card/i }));

    expect(within(column).getByText("New card")).toBeInTheDocument();

    const deleteButton = within(column).getByRole("button", {
      name: /delete new card/i,
    });
    await userEvent.click(deleteButton);

    expect(within(column).queryByText("New card")).not.toBeInTheDocument();
  });

  it("shows add column button", async () => {
    render(<KanbanBoard />);
    await screen.findAllByTestId(/column-/i);

    expect(screen.getByTestId("add-column-button")).toBeInTheDocument();
  });

  it("shows card priority badges", async () => {
    const board = cloneInitialBoard();
    board.cards["card-1"].priority = "high";
    board.cards["card-2"].priority = "medium";

    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/board") {
        return Promise.resolve(jsonResponse(board));
      }
      if (url === "/api/ai/chat/history") {
        return Promise.resolve(jsonResponse([]));
      }
      return Promise.resolve(new Response("Not Found", { status: 404 }));
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<KanbanBoard />);
    await screen.findAllByTestId(/column-/i);

    expect(screen.getByText("High")).toBeInTheDocument();
    expect(screen.getAllByText("Medium").length).toBeGreaterThanOrEqual(1);
  });

  it("loads board by id when boardId prop is provided", async () => {
    const board = cloneInitialBoard();
    board.name = "Sprint Board";

    const fetchMock = vi.fn((input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/boards/42") {
        return Promise.resolve(jsonResponse(board));
      }
      if (url.startsWith("/api/ai/chat/history")) {
        return Promise.resolve(jsonResponse([]));
      }
      return Promise.resolve(new Response("Not Found", { status: 404 }));
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<KanbanBoard boardId={42} />);
    await screen.findAllByTestId(/column-/i);

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/boards/42",
      expect.objectContaining({ credentials: "include" })
    );
  });
});
