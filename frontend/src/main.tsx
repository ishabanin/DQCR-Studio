import React from "react";
import ReactDOM from "react-dom/client";
import { loader } from "@monaco-editor/react";
import * as monaco from "monaco-editor";
import App from "./App";
import ErrorBoundary from "./app/providers/ErrorBoundary";
import QueryProvider from "./app/providers/QueryProvider";
import ThemeProvider from "./app/providers/ThemeProvider";
import "./styles.css";

// Force Monaco to use the locally bundled editor instead of loading from CDN.
loader.config({ monaco });

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryProvider>
      <ThemeProvider>
        <ErrorBoundary>
          <App />
        </ErrorBoundary>
      </ThemeProvider>
    </QueryProvider>
  </React.StrictMode>
);
