/**
 * MavadoClaw Edge Worker — Cloudflare Workers
 * Tier 1: Cloudflare Workers AI (env.AI binding — truly free, no key)
 * Tier 2: Failover to PandaStack/HF Space
 * Free: 100K req/day, 10K AI neurons/day
 */

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, X-Admin-Token, Authorization",
  "Content-Type": "application/json",
};

export default {
  async fetch(req, env, ctx) {
    const url = new URL(req.url);

    if (req.method === "OPTIONS") {
      return new Response(null, { headers: CORS_HEADERS });
    }

    // Health check
    if (url.pathname === "/health") {
      return new Response(
        JSON.stringify({
          status: "ok",
          service: "mavadoclaw-edge",
          ts: Date.now(),
          workers_ai: !!env.AI,
          backend_configured: !!(env.PANDASTACK_URL || env.HF_SPACE_URL),
        }),
        { headers: CORS_HEADERS }
      );
    }

    // Chat endpoint
    if (url.pathname === "/api/chat" && req.method === "POST") {
      let body;
      try {
        body = await req.json();
      } catch {
        return new Response(
          JSON.stringify({ error: "Invalid JSON" }),
          { status: 400, headers: CORS_HEADERS }
        );
      }

      const messages = body.messages || [];

      // Tier 1: Cloudflare Workers AI — no external API key needed
      if (env.AI) {
        try {
          const model = "@cf/meta/llama-3.1-8b-instruct";
          const result = await env.AI.run(model, { messages });
          if (result?.response) {
            return new Response(
              JSON.stringify({
                provider: "cloudflare-workers-ai",
                model,
                content: result.response,
                tier: 1,
              }),
              { headers: CORS_HEADERS }
            );
          }
        } catch (e) {
          console.log("CF Workers AI failed:", e.message);
        }
      }

      // Tier 2: PandaStack primary
      if (env.PANDASTACK_URL) {
        try {
          const resp = await fetch(`${env.PANDASTACK_URL}/api/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
            signal: AbortSignal.timeout(25000),
          });
          if (resp.ok) {
            const data = await resp.json();
            data.tier = 2;
            return new Response(JSON.stringify(data), { headers: CORS_HEADERS });
          }
        } catch (e) {
          console.log("PandaStack failover failed:", e.message);
        }
      }

      // Tier 3: HF Space fallback
      if (env.HF_SPACE_URL) {
        try {
          const resp = await fetch(`${env.HF_SPACE_URL}/api/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
            signal: AbortSignal.timeout(25000),
          });
          if (resp.ok) {
            const data = await resp.json();
            data.tier = 3;
            return new Response(JSON.stringify(data), { headers: CORS_HEADERS });
          }
        } catch (e) {
          console.log("HF Space fallback failed:", e.message);
        }
      }

      return new Response(
        JSON.stringify({ error: "All backends unavailable", tier: "exhausted" }),
        { status: 503, headers: CORS_HEADERS }
      );
    }

    // Root
    return new Response(
      JSON.stringify({
        service: "MavadoClaw Edge",
        status: "online",
        endpoints: ["/health", "/api/chat"],
        docs: "https://github.com/complianceguardaireports-wq/MavadoClaw-Worker001",
      }),
      { headers: CORS_HEADERS }
    );
  },
};
