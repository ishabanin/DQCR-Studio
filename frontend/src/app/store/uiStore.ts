import { create } from "zustand";

type ToastType = "success" | "info" | "error";
type WorkflowCacheStatus = "ready" | "stale" | "building" | "error" | "missing";
type UserRole = "user" | "admin" | "viewer";

interface ToastAction {
  label: string;
  onClick: () => void;
}

interface ToastItem {
  id: string;
  title: string;
  description?: string;
  type: ToastType;
  autoCloseMs: number | null;
  action?: ToastAction;
}

interface UiStore {
  sidebarCollapsed: boolean;
  sidebarWidth: number;
  bottomPanelExpanded: boolean;
  bottomPanelHeight: number;
  bottomPanelTab: "terminal" | "logs" | "output";
  toasts: ToastItem[];
  apiLogs: string[];
  projectWizardOpen: boolean;
  userRole: UserRole;
  role: UserRole;
  userEmail: string;
  validationAutoRun: boolean;
  cacheStatus: WorkflowCacheStatus | null;
  lastSavedAt: Date | null;
  initialParam: { id: string; scope: string } | null;
  initialParamScopeFilter: string | null;
  initialModelId: string | null;
  dismissedHistoryWarning: boolean;
  toggleSidebar: () => void;
  setSidebarWidth: (width: number) => void;
  toggleBottomPanel: () => void;
  setBottomPanelTab: (tab: "terminal" | "logs" | "output") => void;
  setBottomPanelHeight: (height: number) => void;
  setProjectWizardOpen: (open: boolean) => void;
  setUserRole: (role: UserRole) => void;
  setValidationAutoRun: (enabled: boolean) => void;
  setCacheStatus: (status: WorkflowCacheStatus | null) => void;
  setLastSavedAt: (d: Date | null) => void;
  setInitialParam: (p: { id: string; scope: string } | null) => void;
  setInitialParamScopeFilter: (scope: string | null) => void;
  setInitialModelId: (modelId: string | null) => void;
  setDismissedHistoryWarning: (v: boolean) => void;
  addApiLog: (line: string) => void;
  clearApiLogs: () => void;
  addToast: (
    title: string,
    type?: ToastType,
    options?: {
      description?: string;
      autoCloseMs?: number | null;
      action?: ToastAction;
    },
  ) => void;
  removeToast: (id: string) => void;
}

export const useUiStore = create<UiStore>((set) => ({
  sidebarCollapsed: false,
  sidebarWidth: Number(window.localStorage.getItem("dqcr_sidebar_width") ?? 288),
  bottomPanelExpanded: false,
  bottomPanelHeight: Number(window.localStorage.getItem("dqcr_bottom_panel_height") ?? 104),
  bottomPanelTab: "terminal",
  toasts: [],
  apiLogs: [],
  projectWizardOpen: false,
  userRole: (window.localStorage.getItem("dqcr_role") as UserRole) || "user",
  role: (window.localStorage.getItem("dqcr_role") as UserRole) || "user",
  userEmail: window.localStorage.getItem("dqcr_user_email") || "admin@corp.ru",
  validationAutoRun: false,
  cacheStatus: null,
  lastSavedAt: null,
  initialParam: null,
  initialParamScopeFilter: null,
  initialModelId: null,
  dismissedHistoryWarning: window.localStorage.getItem("dqcr_dismissed_history_warning") === "true",
  toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
  setSidebarWidth: (width) => {
    const nextWidth = Math.min(420, Math.max(220, Math.round(width)));
    window.localStorage.setItem("dqcr_sidebar_width", String(nextWidth));
    set({ sidebarWidth: nextWidth });
  },
  toggleBottomPanel: () => set((state) => ({ bottomPanelExpanded: !state.bottomPanelExpanded })),
  setBottomPanelTab: (tab) => set({ bottomPanelTab: tab }),
  setBottomPanelHeight: (height) => {
    const nextHeight = Math.min(520, Math.max(80, Math.round(height)));
    window.localStorage.setItem("dqcr_bottom_panel_height", String(nextHeight));
    set({ bottomPanelHeight: nextHeight });
  },
  setProjectWizardOpen: (open) => set({ projectWizardOpen: open }),
  setUserRole: (role) => {
    window.localStorage.setItem("dqcr_role", role);
    set({ userRole: role, role });
  },
  setValidationAutoRun: (enabled) => set({ validationAutoRun: enabled }),
  setCacheStatus: (status) => set({ cacheStatus: status }),
  setLastSavedAt: (d) => set({ lastSavedAt: d }),
  setInitialParam: (p) => set({ initialParam: p }),
  setInitialParamScopeFilter: (scope) => set({ initialParamScopeFilter: scope }),
  setInitialModelId: (modelId) => set({ initialModelId: modelId }),
  setDismissedHistoryWarning: (v) => {
    window.localStorage.setItem("dqcr_dismissed_history_warning", v ? "true" : "false");
    set({ dismissedHistoryWarning: v });
  },
  addApiLog: (line) =>
    set((state) => ({
      apiLogs: [...state.apiLogs, line].slice(-500),
    })),
  clearApiLogs: () => set({ apiLogs: [] }),
  addToast: (title, type = "info", options) =>
    set((state) => ({
      toasts: [
        ...state.toasts,
        {
          id: `${Date.now()}-${Math.random()}`,
          title,
          description: options?.description,
          type,
          autoCloseMs: options?.autoCloseMs ?? 2500,
          action: options?.action,
        },
      ],
    })),
  removeToast: (id) =>
    set((state) => ({
      toasts: state.toasts.filter((toast) => toast.id !== id),
    })),
}));
