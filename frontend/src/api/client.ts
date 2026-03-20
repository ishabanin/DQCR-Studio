import axios from "axios";
import { useUiStore } from "../app/store/uiStore";

export const apiClient = axios.create({
  baseURL: "/api/v1",
  timeout: 10000
});

apiClient.interceptors.request.use((config) => {
  const token = window.localStorage.getItem("dqcr_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  const method = (config.method ?? "get").toUpperCase();
  const url = config.url ?? "";
  const ts = new Date().toISOString();
  const line = `${ts} ${method} ${url}`;
  useUiStore.getState().addApiLog(line);
  window.dispatchEvent(new CustomEvent("dqcr:api-call", { detail: { line } }));
  return config;
});
