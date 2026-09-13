import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async redirects() {
    return [
      { source: "/cashflow", destination: "/bank-flow", permanent: false },
      { source: "/cc-cashflow", destination: "/credit-cards", permanent: false },
      { source: "/recurring", destination: "/expenses", permanent: false },
      { source: "/one-off", destination: "/expenses", permanent: false },
      { source: "/settings", destination: "/setup", permanent: false },
    ];
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://127.0.0.1:8000/api/:path*",
      },
    ];
  },
};

export default nextConfig;
