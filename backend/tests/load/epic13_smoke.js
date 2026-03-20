import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  vus: 50,
  duration: "30s",
  thresholds: {
    http_req_failed: ["rate<0.05"],
    http_req_duration: ["p(95)<1500"],
  },
};

const BASE_URL = __ENV.BASE_URL || "http://127.0.0.1:80";
const PROJECT_ID = __ENV.PROJECT_ID || "demo";

export default function () {
  const projects = http.get(`${BASE_URL}/api/v1/projects`);
  check(projects, { "projects status 200": (r) => r.status === 200 });

  const lineage = http.get(`${BASE_URL}/api/v1/projects/${PROJECT_ID}/models/SampleModel/lineage`);
  check(lineage, { "lineage status 200": (r) => r.status === 200 || r.status === 404 });

  const validatePayload = JSON.stringify({ model_id: "SampleModel", categories: ["general", "sql"] });
  const validate = http.post(`${BASE_URL}/api/v1/projects/${PROJECT_ID}/validate`, validatePayload, {
    headers: { "Content-Type": "application/json" },
  });
  check(validate, { "validate status 200": (r) => r.status === 200 || r.status === 404 });

  sleep(1);
}

