import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AuthGate } from "@/components/AuthGate";
import { initialData } from "@/lib/kanban";

const jsonResponse = (payload: unknown, status = 200) =>
  new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });

describe("AuthGate", () => {
  beforeEach(() => {
    window.localStorage.removeItem("pm-local-authenticated");
    window.localStorage.removeItem("pm-local-board");
    window.localStorage.removeItem("pm-local-chat-history");
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("shows sign in when session is unauthenticated", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ authenticated: false, username: null }));
    vi.stubGlobal("fetch", fetchMock);

    render(<AuthGate />);

    expect(await screen.findByRole("heading", { name: /sign in/i })).toBeInTheDocument();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/auth/session",
      expect.objectContaining({ credentials: "include" })
    );
  });

  it("logs in successfully and shows board controls", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ authenticated: false, username: null }))
      .mockResolvedValueOnce(jsonResponse({ authenticated: true, username: "user" }))
      .mockResolvedValueOnce(jsonResponse([{ id: 1, name: "My Board", updated_at: "2026-01-01" }]))
      .mockResolvedValueOnce(jsonResponse({ ...initialData, id: 1, name: "My Board" }))
      .mockResolvedValueOnce(jsonResponse([]));
    vi.stubGlobal("fetch", fetchMock);

    render(<AuthGate />);

    await screen.findByRole("heading", { name: /sign in/i });
    await userEvent.type(screen.getByLabelText(/username/i), "user");
    await userEvent.type(screen.getByLabelText(/password/i), "password");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

    // Username button opens the dropdown menu
    const userButton = await screen.findByRole("button", { name: "user" });
    expect(userButton).toBeInTheDocument();
    await userEvent.click(userButton);
    expect(screen.getByText(/log out/i)).toBeInTheDocument();
  });

  it("shows an error for invalid credentials", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ authenticated: false, username: null }))
      .mockResolvedValueOnce(jsonResponse({ detail: "Invalid credentials." }, 401));
    vi.stubGlobal("fetch", fetchMock);

    render(<AuthGate />);

    await screen.findByRole("heading", { name: /sign in/i });
    await userEvent.type(screen.getByLabelText(/username/i), "user");
    await userEvent.type(screen.getByLabelText(/password/i), "wrong");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/invalid credentials/i);
  });

  it("logs out and returns to sign in view", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ authenticated: true, username: "user" }))
      .mockResolvedValueOnce(jsonResponse([{ id: 1, name: "My Board", updated_at: "2026-01-01" }]))
      .mockResolvedValueOnce(jsonResponse({ ...initialData, id: 1, name: "My Board" }))
      .mockResolvedValueOnce(jsonResponse([]))
      .mockResolvedValueOnce(jsonResponse({ authenticated: false, username: null }));
    vi.stubGlobal("fetch", fetchMock);

    render(<AuthGate />);

    // Open the user dropdown first
    const userButton = await screen.findByRole("button", { name: "user" });
    await userEvent.click(userButton);
    await userEvent.click(screen.getByText(/log out/i));

    expect(await screen.findByRole("heading", { name: /sign in/i })).toBeInTheDocument();
  });

  it("shows registration form when clicking create account", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ authenticated: false, username: null }));
    vi.stubGlobal("fetch", fetchMock);

    render(<AuthGate />);

    await screen.findByRole("heading", { name: /sign in/i });
    await userEvent.click(screen.getByTestId("switch-to-register"));

    expect(screen.getByRole("heading", { name: /create account/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /create account/i })).toBeInTheDocument();
  });

  it("registers a new user", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ authenticated: false, username: null }))
      .mockResolvedValueOnce(jsonResponse({ authenticated: true, username: "newuser" }))
      .mockResolvedValueOnce(jsonResponse([{ id: 1, name: "My Board", updated_at: "2026-01-01" }]))
      .mockResolvedValueOnce(jsonResponse({ ...initialData, id: 1, name: "My Board" }))
      .mockResolvedValueOnce(jsonResponse([]));
    vi.stubGlobal("fetch", fetchMock);

    render(<AuthGate />);

    await screen.findByRole("heading", { name: /sign in/i });
    await userEvent.click(screen.getByTestId("switch-to-register"));

    await userEvent.type(screen.getByLabelText(/username/i), "newuser");
    await userEvent.type(screen.getByLabelText(/password/i), "securepassword");
    await userEvent.click(screen.getByRole("button", { name: /create account/i }));

    // Username button opens the dropdown menu
    const userButton = await screen.findByRole("button", { name: "newuser" });
    expect(userButton).toBeInTheDocument();
    await userEvent.click(userButton);
    expect(screen.getByText(/log out/i)).toBeInTheDocument();

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/auth/register",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ username: "newuser", password: "securepassword" }),
      })
    );
  });

  it("shows error for duplicate username during registration", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ authenticated: false, username: null }))
      .mockResolvedValueOnce(jsonResponse({ detail: "Username already taken." }, 409));
    vi.stubGlobal("fetch", fetchMock);

    render(<AuthGate />);

    await screen.findByRole("heading", { name: /sign in/i });
    await userEvent.click(screen.getByTestId("switch-to-register"));

    await userEvent.type(screen.getByLabelText(/username/i), "existing");
    await userEvent.type(screen.getByLabelText(/password/i), "securepassword");
    await userEvent.click(screen.getByRole("button", { name: /create account/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/username already taken/i);
  });
});
