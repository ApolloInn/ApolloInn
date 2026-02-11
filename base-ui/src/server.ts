/**
 * AURORA Web UI — 开发服务器
 * 纯静态文件服务，前端通过 API 连接 AURORA Gateway
 */

import { readFileSync, existsSync } from "node:fs";
import { resolve, extname } from "node:path";

const PORT = 3001;
const STATIC_DIR = resolve(import.meta.dir, "../public");

const MIME_TYPES: Record<string, string> = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".json": "application/json",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".ico": "image/x-icon",
  ".woff2": "font/woff2",
};

Bun.serve({
  port: PORT,
  fetch(req) {
    const url = new URL(req.url);
    let pathname = url.pathname === "/" ? "/index.html" : url.pathname;
    const filePath = resolve(STATIC_DIR, `.${pathname}`);

    if (!filePath.startsWith(STATIC_DIR)) {
      return new Response("Forbidden", { status: 403 });
    }

    if (!existsSync(filePath)) {
      const indexPath = resolve(STATIC_DIR, "index.html");
      if (existsSync(indexPath)) {
        return new Response(readFileSync(indexPath), {
          headers: { "Content-Type": "text/html; charset=utf-8" },
        });
      }
      return new Response("Not Found", { status: 404 });
    }

    const ext = extname(filePath);
    const contentType = MIME_TYPES[ext] ?? "application/octet-stream";
    return new Response(readFileSync(filePath), {
      headers: { "Content-Type": contentType },
    });
  },
});

console.log(`🌟 AURORA Web UI running at http://localhost:${PORT}`);
