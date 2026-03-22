import { moveCard, createId, priorityLabel, labelColor, priorityColor, type Column } from "@/lib/kanban";

describe("moveCard", () => {
  const baseColumns: Column[] = [
    { id: "col-a", title: "A", cardIds: ["card-1", "card-2"] },
    { id: "col-b", title: "B", cardIds: ["card-3"] },
  ];

  it("reorders cards in the same column", () => {
    const result = moveCard(baseColumns, "card-2", "card-1");
    expect(result[0].cardIds).toEqual(["card-2", "card-1"]);
  });

  it("moves cards to another column", () => {
    const result = moveCard(baseColumns, "card-2", "card-3");
    expect(result[0].cardIds).toEqual(["card-1"]);
    expect(result[1].cardIds).toEqual(["card-2", "card-3"]);
  });

  it("drops cards to the end of a column", () => {
    const result = moveCard(baseColumns, "card-1", "col-b");
    expect(result[0].cardIds).toEqual(["card-2"]);
    expect(result[1].cardIds).toEqual(["card-3", "card-1"]);
  });
});

describe("createId", () => {
  it("generates an id with the given prefix", () => {
    const id = createId("card");
    expect(id).toMatch(/^card-.+/);
  });

  it("generates unique ids", () => {
    const ids = new Set(Array.from({ length: 100 }, () => createId("col")));
    expect(ids.size).toBe(100);
  });
});

describe("priorityLabel", () => {
  it("capitalizes priority", () => {
    expect(priorityLabel("high")).toBe("High");
    expect(priorityLabel("medium")).toBe("Medium");
    expect(priorityLabel("low")).toBe("Low");
  });

  it("returns empty string for null/undefined", () => {
    expect(priorityLabel(null)).toBe("");
    expect(priorityLabel(undefined)).toBe("");
  });
});

describe("labelColor", () => {
  it("returns classes for known colors", () => {
    expect(labelColor("red")).toContain("text-red-700");
    expect(labelColor("blue")).toContain("text-blue-700");
  });

  it("returns gray fallback for unknown colors", () => {
    expect(labelColor("unknown")).toContain("text-gray-700");
  });
});

describe("priorityColor", () => {
  it("returns correct color classes", () => {
    expect(priorityColor("high")).toContain("text-red-700");
    expect(priorityColor("medium")).toContain("text-amber-700");
    expect(priorityColor("low")).toContain("text-green-700");
  });

  it("returns empty string for null", () => {
    expect(priorityColor(null)).toBe("");
  });
});
