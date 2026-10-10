// ShipStiffs: read a golf scorecard photo with Claude and return the card as JSON.
// Deploy as a Supabase Edge Function named "scan-scorecard".
// Needs the secret ANTHROPIC_API_KEY (Edge Functions > Secrets). SUPABASE_URL and
// SUPABASE_ANON_KEY are provided by Supabase automatically.
import Anthropic from "npm:@anthropic-ai/sdk@0.128.0";

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, apikey, content-type, x-client-info",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};
const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { ...CORS, "Content-Type": "application/json" } });

const nullableInt = { anyOf: [{ type: "integer" }, { type: "null" }] };
const nullableNum = { anyOf: [{ type: "number" }, { type: "null" }] };
const nullableStr = { anyOf: [{ type: "string" }, { type: "null" }] };

// What we want back. Structured outputs guarantee the response matches this schema.
const SCHEMA = {
  type: "object",
  additionalProperties: false,
  required: ["course_name", "holes", "tees", "notes"],
  properties: {
    course_name: nullableStr,
    holes: {
      type: "array",
      description: "One entry per hole printed on the card, in hole order.",
      items: {
        type: "object",
        additionalProperties: false,
        required: ["hole", "par", "si"],
        properties: {
          hole: { type: "integer" },
          par: nullableInt,
          si: { ...nullableInt, description: "Men's handicap / stroke index for the hole (1 = hardest)." },
        },
      },
    },
    tees: {
      type: "array",
      description: "One entry per tee set printed on the card.",
      items: {
        type: "object",
        additionalProperties: false,
        required: ["name", "rating", "slope", "par", "yards"],
        properties: {
          name: { type: "string", description: "Tee name or color as printed, e.g. 'Green', 'Black/Blue combo'." },
          rating: { ...nullableNum, description: "Course rating for this tee, e.g. 71.4." },
          slope: { ...nullableInt, description: "Slope rating for this tee, e.g. 128." },
          par: nullableInt,
          yards: { type: "array", items: nullableInt, description: "Yardage for holes 1-18 in order." },
        },
      },
    },
    notes: { type: "string", description: "Anything unclear or unreadable, and which handicap row was used." },
  },
};

const PROMPT = `These photos are a golf course scorecard (front and/or back). Read it and fill in the schema.

- holes: every hole 1-18 with its par and the men's handicap (stroke index) row. If the card has separate men's and women's handicap rows, use the men's row and say so in notes. If par differs by tee, use the par for the longest common men's tee and mention the difference in notes.
- tees: every tee set printed, with its course rating and slope if shown (often near the tee name, in a small table, or written like "71.4/128"), its total par, and its 18 hole yardages. When a tee lists separate men's and women's ratings (e.g. "M-71.4/127 W-77.6/138"), use the men's. Include tee sets printed anywhere on the card, including ones on the far side of the par column.
- Use null for anything you can't read. Never guess a number - a null is better than a wrong value, because a person will review and fill in blanks.
- notes: briefly list anything unreadable, ambiguous, or that a person should double-check.`;

async function pinOk(pin: string): Promise<boolean> {
  const url = Deno.env.get("SUPABASE_URL"), key = Deno.env.get("SUPABASE_ANON_KEY");
  if (!url || !key) return false;
  const r = await fetch(`${url}/rest/v1/rpc/check_pin`, {
    method: "POST",
    headers: { apikey: key, Authorization: `Bearer ${key}`, "Content-Type": "application/json" },
    body: JSON.stringify({ p_pin: pin }),
  });
  return r.ok && (await r.json()) === true;
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });
  if (req.method !== "POST") return json({ error: "Use POST." }, 405);

  let body: { pin?: string; images?: { media_type: string; data: string }[] };
  try { body = await req.json(); } catch { return json({ error: "Send JSON." }, 400); }

  if (!body.pin || !(await pinOk(body.pin))) return json({ error: "wrong_pin" }, 403);
  const images = (body.images ?? []).filter((i) =>
    ["image/jpeg", "image/png", "image/webp"].includes(i.media_type) && typeof i.data === "string");
  if (!images.length || images.length > 4) return json({ error: "Send 1 to 4 photos." }, 400);
  if (images.some((i) => i.data.length > 7_000_000)) return json({ error: "A photo is too large." }, 413);

  // Reads ANTHROPIC_API_KEY. A key that isn't scoped to a workspace also needs
  // ANTHROPIC_WORKSPACE_ID (Console > Settings > Workspaces) so requests name their workspace.
  const workspace = Deno.env.get("ANTHROPIC_WORKSPACE_ID");
  const client = new Anthropic(workspace ? { defaultHeaders: { "anthropic-workspace-id": workspace } } : {});
  const content = [
    ...images.map((i) => ({
      type: "image" as const,
      source: { type: "base64" as const, media_type: i.media_type as "image/jpeg", data: i.data },
    })),
    { type: "text" as const, text: PROMPT },
  ];
  // Try the full request first; if the API rejects an option, retry with a simpler request
  // and report the API's own message so problems can be diagnosed.
  const attempts = [
    { label: "full", fallbacks: true, schema: true },
    { label: "no-fallbacks", fallbacks: false, schema: true },
    { label: "plain-json", fallbacks: false, schema: false },
  ];
  const errors: string[] = [];
  for (const a of attempts) {
    try {
      const response = await client.beta.messages.create({
        model: "claude-opus-5-5",
        max_tokens: 16000,
        output_config: a.schema
          ? { effort: "medium", format: { type: "json_schema", schema: SCHEMA } }
          : { effort: "medium" },
        ...(a.fallbacks ? { betas: ["server-side-fallback-2026-07-01"], fallbacks: "default" as const } : {}),
        messages: [{
          role: "user",
          content: a.schema ? content : [...content.slice(0, -1), {
            type: "text" as const,
            text: PROMPT + "\n\nReply with only a JSON object matching this JSON Schema, no other text:\n" + JSON.stringify(SCHEMA),
          }],
        }],
      });
      if (response.stop_reason === "refusal") return json({ error: "The card couldn't be read. Try another photo." }, 422);
      if (response.stop_reason === "max_tokens") return json({ error: "The card was too long to read in one go." }, 422);
      const text = response.content.flatMap((b) => (b.type === "text" ? [b.text] : [])).join("");
      const start = text.indexOf("{"), end = text.lastIndexOf("}");
      const card = JSON.parse(a.schema ? text : text.slice(start, end + 1));
      return json({ card, model: response.model, usage: response.usage, attempt: a.label, earlier_errors: errors });
    } catch (err) {
      if (err instanceof Anthropic.BadRequestError) {
        if (/workspace/i.test(err.message)) {
          return json({ error: "The Anthropic API key isn't tied to a workspace. Use a key created inside a workspace, or add the ANTHROPIC_WORKSPACE_ID secret." }, 500);
        }
        errors.push(`${a.label}: ${err.message}`); console.error(a.label, err.message); continue;
      }
      if (err instanceof Anthropic.AuthenticationError) return json({ error: "The Anthropic API key is missing or wrong." }, 500);
      if (err instanceof Anthropic.PermissionDeniedError) return json({ error: `The API key isn't allowed to do this: ${err.message}` }, 500);
      if (err instanceof Anthropic.RateLimitError) return json({ error: "Busy right now. Try again in a minute." }, 429);
      if (err instanceof Anthropic.APIError) return json({ error: `Scan service error (${err.status}): ${err.message}` }, 502);
      if (err instanceof SyntaxError) { errors.push(`${a.label}: reply wasn't valid JSON`); continue; }
      return json({ error: `Something went wrong reading the card: ${String(err)}` }, 500);
    }
  }
  return json({ error: "The scan service rejected the request.", details: errors }, 400);
});
