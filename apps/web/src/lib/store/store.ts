import { useSyncExternalStore } from "react";

/** A minimal external store, so state outlives the tab (route) that shows it. */
export function createStore<T extends object>(initial: T) {
  let state = initial;
  const listeners = new Set<() => void>();
  return {
    initial,
    get: () => state,
    set(update: Partial<T> | ((current: T) => Partial<T>)) {
      state = { ...state, ...(typeof update === "function" ? update(state) : update) };
      listeners.forEach((listener) => listener());
    },
    subscribe(listener: () => void) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
  };
}

export type Store<T extends object> = ReturnType<typeof createStore<T>>;

/** Selectors must return stored values (not new objects), or React re-renders forever. */
export function useStore<T extends object, U>(store: Store<T>, select: (state: T) => U): U {
  return useSyncExternalStore(
    store.subscribe,
    () => select(store.get()),
    () => select(store.initial),
  );
}
