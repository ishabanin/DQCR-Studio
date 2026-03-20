import { Component, ErrorInfo, ReactNode } from "react";

import { useUiStore } from "../store/uiStore";

interface ErrorBoundaryState {
  hasError: boolean;
}

class ErrorBoundaryInner extends Component<{ children: ReactNode; onError: (message: string) => void }, ErrorBoundaryState> {
  constructor(props: { children: ReactNode; onError: (message: string) => void }) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(): ErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error, _: ErrorInfo): void {
    this.props.onError(`UI error: ${error.message}`);
  }

  render() {
    if (this.state.hasError) {
      return (
        <section className="workbench">
          <h1>Something went wrong</h1>
          <p>Try refreshing the page.</p>
        </section>
      );
    }
    return this.props.children;
  }
}

export default function ErrorBoundary({ children }: { children: ReactNode }) {
  const addToast = useUiStore((state) => state.addToast);
  return <ErrorBoundaryInner onError={(message) => addToast(message, "error")}>{children}</ErrorBoundaryInner>;
}

