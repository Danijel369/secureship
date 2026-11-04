import { defineConfig } from "orval";

export default defineConfig({
  api: {
    input: "http://localhost:8000/openapi.json",
    output: {
      target: "./src/api/generated/index.ts",
      client: "react-query",
    },
  },
});