import type { NextConfig } from "next";

// Site 100% estático (GitHub Pages). BASE_PATH só é necessário se o site for
// publicado sem domínio próprio (ex.: usuario.github.io/central-de-editais).
const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  images: { unoptimized: true },
  basePath: process.env.BASE_PATH || undefined,
  env: {
    NEXT_PUBLIC_BASE_PATH: process.env.BASE_PATH || "",
    NEXT_PUBLIC_SITE_URL: process.env.SITE_URL || "https://radardeeditais.isadoraflores.art.br",
    NEXT_PUBLIC_REPO: process.env.REPO || "isadoraflores89/central-de-editais",
  },
};

export default nextConfig;
