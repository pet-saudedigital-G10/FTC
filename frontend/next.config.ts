import type { NextConfig } from "next";

const djangoApiUrl = process.env.DJANGO_API_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  // Django routes use trailing slashes. Preserve them before the rewrite so
  // Django does not redirect back to a non-existent Next.js API route.
  skipTrailingSlashRedirect: true,
  async rewrites() {
    return [
      {
        source: "/api/backend/:path*",
        // Next strips the matched trailing slash from `:path*`. Add it back so
        // Django never needs to redirect a POST and lose its request body.
        destination: `${djangoApiUrl}/:path*/`,
      },
    ];
  },
};

export default nextConfig;
