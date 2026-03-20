import { useEffect, useRef } from "react";
import { Terminal as XTerm } from "xterm";
import { FitAddon } from "@xterm/addon-fit";
import "xterm/css/xterm.css";

export default function Terminal() {
  const rootRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!rootRef.current) return;

    const terminal = new XTerm({
      cursorBlink: true,
      fontSize: 11,
      fontFamily: '"SF Mono", "Fira Code", "Cascadia Code", "Courier New", monospace',
      theme: {
        background: "#1E1E1E",
        foreground: "#CDCDCD",
      },
    });
    const fitAddon = new FitAddon();
    terminal.loadAddon(fitAddon);
    terminal.open(rootRef.current);
    fitAddon.fit();
    terminal.writeln("DQCR Studio Terminal");
    terminal.writeln("\x1b[32mANSI colors enabled\x1b[0m");
    terminal.writeln("Connecting to WebSocket terminal...");
    terminal.write("> ");

    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const websocket = new WebSocket(`${protocol}://${window.location.host}/ws/terminal/default`);

    websocket.onopen = () => {
      terminal.writeln("WebSocket connected.");
      websocket.send("help");
    };
    websocket.onmessage = (event) => {
      terminal.writeln(event.data);
    };
    websocket.onclose = () => {
      terminal.writeln("WebSocket disconnected.");
    };
    websocket.onerror = () => {
      terminal.writeln("WebSocket error.");
    };

    const history: string[] = [];
    let historyIndex = -1;
    let currentLine = "";

    const rewriteCurrentLine = (value: string) => {
      terminal.write("\r\x1b[2K> ");
      terminal.write(value);
    };

    terminal.onKey(({ key, domEvent }) => {
      if ((domEvent.ctrlKey || domEvent.metaKey) && domEvent.key.toLowerCase() === "l") {
        terminal.clear();
        terminal.write("> ");
        currentLine = "";
        return;
      }

      if (domEvent.key === "Enter") {
        terminal.write("\r\n");
        if (currentLine.trim() && websocket.readyState === WebSocket.OPEN) {
          websocket.send(`${currentLine}\n`);
          history.push(currentLine);
        }
        historyIndex = history.length;
        currentLine = "";
        terminal.write("> ");
        return;
      }

      if (domEvent.key === "Backspace") {
        if (currentLine.length > 0) {
          currentLine = currentLine.slice(0, -1);
          terminal.write("\b \b");
        }
        return;
      }

      if (domEvent.key === "ArrowUp") {
        if (history.length === 0) return;
        historyIndex = Math.max(0, historyIndex - 1);
        currentLine = history[historyIndex];
        rewriteCurrentLine(currentLine);
        return;
      }

      if (domEvent.key === "ArrowDown") {
        if (history.length === 0) return;
        historyIndex = Math.min(history.length, historyIndex + 1);
        currentLine = historyIndex >= history.length ? "" : history[historyIndex];
        rewriteCurrentLine(currentLine);
        return;
      }

      if (key.length === 1 && !domEvent.ctrlKey && !domEvent.metaKey) {
        currentLine += key;
        terminal.write(key);
      }
    });

    const onResize = () => fitAddon.fit();
    const onApiCall = (event: Event) => {
      const customEvent = event as CustomEvent<{ line?: string }>;
      const line = customEvent.detail?.line;
      if (!line) return;
      terminal.writeln(`\x1b[36m$ api ${line}\x1b[0m`);
      terminal.write("> ");
    };
    window.addEventListener("resize", onResize);
    window.addEventListener("dqcr:api-call", onApiCall);

    return () => {
      window.removeEventListener("resize", onResize);
      window.removeEventListener("dqcr:api-call", onApiCall);
      websocket.close();
      terminal.dispose();
    };
  }, []);

  return <div className="terminal-host" ref={rootRef} />;
}
