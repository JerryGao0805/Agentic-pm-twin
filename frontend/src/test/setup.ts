import "@testing-library/jest-dom";

const createMemoryStorage = (): Storage => {
  const store = new Map<string, string>();

  return {
    get length() {
      return store.size;
    },
    clear() {
      store.clear();
    },
    getItem(key: string) {
      return store.has(key) ? store.get(key) ?? null : null;
    },
    key(index: number) {
      return Array.from(store.keys())[index] ?? null;
    },
    removeItem(key: string) {
      store.delete(key);
    },
    setItem(key: string, value: string) {
      store.set(key, value);
    },
  };
};

if (
  typeof window !== "undefined" &&
  (typeof window.localStorage === "undefined" ||
    typeof window.localStorage.getItem !== "function")
) {
  Object.defineProperty(window, "localStorage", {
    value: createMemoryStorage(),
    configurable: true,
  });
}
