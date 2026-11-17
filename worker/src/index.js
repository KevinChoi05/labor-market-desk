// Labor Market Desk chat proxy.
// Holds the OpenRouter key, accepts only this dashboard's chat requests,
// and forwards them to OpenRouter with a fixed model, tool list and token cap.
// Hard spend cap: set a credit limit on the OpenRouter key itself.

const OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions";
const SYSTEM_PREFIX = "You are a labor-market analyst answering questions about the current U.S. job market";
const MAX_MESSAGES = 40;
const MAX_CHARS = 60000;      // whole request, system prompt included
const MAX_QUESTION = 1000;    // any single user message
const MAX_TOKENS = 2000;  // includes the model's internal reasoning

// The only tool the model may call. The page runs it against its own BLS data.
const TOOLS = [{
  type: "function",
  function: {
    name: "get_series",
    description: "Get monthly values for up to 4 BLS series (or derived series) between two months, inclusive. Returns [month, value] pairs; null means not published.",
    parameters: {
      type: "object",
      properties: {
        ids: { type: "array", items: { type: "string" }, description: "Series IDs from the catalog" },
        start: { type: "string", description: "YYYY-MM" },
        end: { type: "string", description: "YYYY-MM" },
      },
      required: ["ids"],
    },
  },
}];

function cors(origin, env) {
  const allowed = env.ALLOWED_ORIGINS.split(",").map(s => s.trim());
  return {
    "Access-Control-Allow-Origin": allowed.includes(origin) ? origin : allowed[0],
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Max-Age": "86400",
    "Vary": "Origin",
  };
}

const json = (body, status, headers) =>
  new Response(JSON.stringify(body), { status, headers: { ...headers, "Content-Type": "application/json" } });

function validate(body) {
  const msgs = body?.messages;
  if (!Array.isArray(msgs) || msgs.length < 2 || msgs.length > MAX_MESSAGES) return "Bad conversation length.";
  if (msgs[0].role !== "system" || typeof msgs[0].content !== "string" || !msgs[0].content.startsWith(SYSTEM_PREFIX)) return "Unexpected request.";
  if (JSON.stringify(msgs).length > MAX_CHARS) return "Conversation is too long. Reload the page to start over.";
  for (const m of msgs.slice(1)) {
    if (!["user", "assistant", "tool"].includes(m.role)) return "Unexpected message role.";
    if (m.role === "user" && (typeof m.content !== "string" || m.content.length > MAX_QUESTION)) return `Questions can be up to ${MAX_QUESTION} characters.`;
  }
  return null;
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";
    const headers = cors(origin, env);
    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers });
    if (request.method !== "POST") return json({ error: "Use POST." }, 405, headers);
    if (!env.ALLOWED_ORIGINS.split(",").map(s => s.trim()).includes(origin)) return json({ error: "This chat only works on the Labor Market Desk site." }, 403, headers);

    const ip = request.headers.get("CF-Connecting-IP") || "unknown";
    if (env.LIMITER) {
      const { success } = await env.LIMITER.limit({ key: ip });
      if (!success) return json({ error: "Too many questions in a short time. Wait a minute and try again.", code: "rate_limited" }, 429, headers);
    }

    let body;
    try { body = await request.json(); } catch { return json({ error: "Invalid JSON." }, 400, headers); }
    const problem = validate(body);
    if (problem) return json({ error: problem }, 400, headers);

    const key = (env.OPENROUTER_API_KEY || "").trim();
    if (!key.startsWith("sk-or-")) {
      console.log("OPENROUTER_API_KEY looks wrong:", { length: key.length, startsWithSkOr: false });
      return json({ error: "The chat isn't configured yet. The charts and tables still work." }, 503, headers);
    }

    const upstream = await fetch(OPENROUTER_URL, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${key}`,
        "Content-Type": "application/json",
        "HTTP-Referer": "https://kevinchoi05.github.io/labor-market-desk/",
        "X-Title": "Labor Market Desk",
      },
      body: JSON.stringify({
        model: env.MODEL,
        messages: body.messages,
        tools: TOOLS,
        max_tokens: MAX_TOKENS,
        usage: { include: true },   // OpenRouter adds token counts and cost to the response
      }),
    });

    const data = await upstream.json().catch(() => null);
    if (!upstream.ok || !data?.choices?.[0]) {
      const status = upstream.status === 402 ? 503 : upstream.status === 429 ? 429 : 502;
      const msg = upstream.status === 402 ? "The chat has used up its budget for now. The charts and tables still work."
        : upstream.status === 429 ? "The chat is busy. Try again in a minute."
        : "The AI service didn't respond. Try again.";
      console.log("openrouter error", upstream.status, JSON.stringify(data)?.slice(0, 500));
      return json({ error: msg }, status, headers);
    }
    const choice = data.choices[0];
    // One line per model call; view with `npx wrangler tail` or in the dashboard (Workers > Logs).
    // No IPs or question text are logged.
    const u = data.usage || {};
    console.log(JSON.stringify({
      event: "chat_call",
      day: new Date().toISOString().slice(0, 10),
      new_question: body.messages[body.messages.length - 1].role === "user",
      tool_calls: choice.message?.tool_calls?.length || 0,
      finish: choice.finish_reason,
      prompt_tokens: u.prompt_tokens, completion_tokens: u.completion_tokens,
      cost_usd: u.cost,
      model: data.model,
    }));
    const { content, tool_calls } = choice.message || {};
    return json({ message: { role: "assistant", content: content || "", tool_calls }, finish_reason: choice.finish_reason, model: data.model }, 200, headers);
  },
};
