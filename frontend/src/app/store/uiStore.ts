import { create } from "zustand";

type ToastType = "success" | "info" | "error";

interface ToastItem {
  id: string;
  message: string;
  type: ToastType;
}

interface UiStore {
  sidebarCollapsed: boolean;
  bottomPanelExpanded: boolean;
  bottomPanelTab: "terminal" | "logs" | "output";
  toasts: ToastItem[];
  apiLogs: string[];
  projectWizardOpen: boolean;
  userRole: "user" | "admin";
  validationAutoRun: boolean;
  toggleSidebar: () => void;
  toggleBottomPanel: () => void;
  setBottomPanelTab: (tab: "terminal" | "logs" | "output") => void;
  setProjectWizardOpen: (open: boolean) => void;
  setUserRole: (role: "user" | "admin") => void;
  setValidationAutoRun: (enabled: boolean) => void;
  addApiLog: (line: string) => void;
  clearApiLogs: () => void;
  addToast: (message: string, type?: ToastType) => void;
  removeToast: (id: string) => void;
}

export const useUiStore = create<UiStore>((set) => ({
  sidebarCollapsed: false,
  bottomPanelExpanded: false,
  bottomPanelTab: "terminal",
  toasts: [],
  apiLogs: [],
  projectWizardOpen: false,
  userRole: (window.localStorage.getItem("dqcr_role") as "user" | "admin") || "user",
  validationAutoRun: false,
  toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
  toggleBottomPanel: () => set((state) => ({ bottomPanelExpanded: !state.bottomPanelExpanded })),
  setBottomPanelTab: (tab) => set({ bottomPanelTab: tab }),
  setProjectWizardOpen: (open) => set({ projectWizardOpen: open }),
  setUserRole: (role) => {
    window.localStorage.setItem("dqcr_role", role);
    set({ userRole: role });
  },
  setValidationAutoRun: (enabled) => set({ validationAutoRun: enabled }),
  addApiLog: (line) =>
    set((state) => ({
      apiLogs: [...state.apiLogs, line].slice(-500),
    })),
  clearApiLogs: () => set({ apiLogs: [] }),
  addToast: (message, type = "info") =>
    set((state) => ({
      toasts: [...state.toasts, { id: `${Date.now()}-${Math.random()}`, message, type }],
    })),
  removeToast: (id) =>
    set((state) => ({
      toasts: state.toasts.filter((toast) => toast.id !== id),
    })),
}));
