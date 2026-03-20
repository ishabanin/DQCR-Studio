import { create } from "zustand";

interface ContextStore {
  activeContext: string;
  activeContexts: string[];
  multiMode: boolean;
  setActiveContext: (context: string) => void;
  toggleMultiMode: () => void;
  toggleContextInMultiMode: (context: string) => void;
}

export const useContextStore = create<ContextStore>((set) => ({
  activeContext: "default",
  activeContexts: ["default"],
  multiMode: false,
  setActiveContext: (context) => set({ activeContext: context, activeContexts: [context] }),
  toggleMultiMode: () =>
    set((state) => ({
      multiMode: !state.multiMode,
      activeContexts: state.multiMode ? [state.activeContext] : state.activeContexts,
    })),
  toggleContextInMultiMode: (context) =>
    set((state) => {
      const exists = state.activeContexts.includes(context);
      const next = exists ? state.activeContexts.filter((item) => item !== context) : [...state.activeContexts, context];
      return {
        activeContexts: next.length > 0 ? next : [state.activeContext],
      };
    }),
}));
