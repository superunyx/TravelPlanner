import { create } from "zustand";
import { persist } from "zustand/middleware";

interface Toast {
  id: string;
  type: "success" | "error" | "info";
  message: string;
}

interface UIState {
  isDarkMode: boolean;
  toggleDarkMode: () => void;
  toasts: Toast[];
  addToast: (type: "success" | "error" | "info", message: string) => void;
  removeToast: (id: string) => void;
  isServerWakingUp: boolean;
  setIsServerWakingUp: (waking: boolean) => void;
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      isDarkMode: false,
      toggleDarkMode: () =>
        set((state) => {
          const next = !state.isDarkMode;
          if (next) {
            document.documentElement.classList.add("dark");
          } else {
            document.documentElement.classList.remove("dark");
          }
          return { isDarkMode: next };
        }),
      toasts: [],
      addToast: (type, message) => {
        const id = Math.random().toString(36).substring(2, 9);
        set((state) => ({ toasts: [...state.toasts, { id, type, message }] }));
        setTimeout(() => {
          set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) }));
        }, 4000);
      },
      removeToast: (id) =>
        set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) })),
      isServerWakingUp: false,
      setIsServerWakingUp: (isServerWakingUp) => set({ isServerWakingUp }),
    }),
    {
      name: "travel-ui-storage",
      partialize: (state) => ({ isDarkMode: state.isDarkMode }),
    }
  )
);
