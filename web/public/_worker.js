// Cloudflare Worker: routes /api/ask to OpenAI; everything else falls through
// to static assets (map, project pages, JSON files).

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === '/api/ask' && request.method === 'POST') {
      return handleAsk(request, env);
    }
    if (url.pathname === '/api/ask' && request.method === 'OPTIONS') {
      return new Response(null, { headers: corsHeaders() });
    }

    // Everything else: serve from the static assets bundle
    return env.ASSETS.fetch(request);
  },
};

function corsHeaders() {
  return {
    'access-control-allow-origin': '*',
    'access-control-allow-methods': 'POST, OPTIONS',
    'access-control-allow-headers': 'content-type',
  };
}

async function handleAsk(request, env) {
  try {
    if (!env.OPENAI_API_KEY) {
      return json({ error: 'Server missing OPENAI_API_KEY. Set it in the Cloudflare dashboard.' }, 500);
    }

    const body = await request.json().catch(() => ({}));
    const question = (body.question || '').toString().trim();

    if (!question) return json({ error: 'Missing question.' }, 400);
    if (question.length > 500) return json({ error: 'Question too long (max 500 chars).' }, 400);

    // Pull the same static JSON the frontend uses, via the ASSETS binding.
    const origin = new URL(request.url).origin;
    const [pRes, sRes, mRes] = await Promise.all([
      env.ASSETS.fetch(`${origin}/api/projects.json`),
      env.ASSETS.fetch(`${origin}/api/summary.json`),
      env.ASSETS.fetch(`${origin}/api/movers.json`),
    ]);
    if (!pRes.ok || !sRes.ok || !mRes.ok) {
      return json({ error: 'Failed to load context data.' }, 500);
    }

    const projectsData = await pRes.json();
    const summary = await sRes.json();
    const movers = await mRes.json();

    // Compact projects (drop verbose fields; keep only what an answer needs)
    const projects = (projectsData.projects || []).map(p => ({
      inr: p.inr,
      name: p.project_name,
      mw: p.capacity_mw,
      fuel: p.fuel,
      county: p.county,
      zone: p.cdr_zone,
      phase: p.gim_study_phase,
      cod: p.projected_cod,
      entity: p.interconnecting_entity,
    }));

    // Pre-compute slip magnitude for COD changes so the LLM doesn't do date math.
    function slipDays(detail) {
      if (!detail || typeof detail !== 'string') return null;
      const m = detail.match(/(\d{4}-\d{2}-\d{2})\s*→\s*(\d{4}-\d{2}-\d{2})/);
      if (!m) return null;
      const a = new Date(m[1] + 'T00:00:00Z').getTime();
      const b = new Date(m[2] + 'T00:00:00Z').getTime();
      if (isNaN(a) || isNaN(b)) return null;
      return Math.round((b - a) / (1000 * 60 * 60 * 24));
    }

    const compactMovers = (movers.movers || []).map(m => {
      const base = {
        inr: m.inr,
        change: m.change_type,
        detail: m.detail,
        name: m.project_name,
        mw: m.capacity_mw,
        fuel: m.fuel,
        county: m.county,
      };
      if (m.change_type === 'COD_SLIPPED' || m.change_type === 'COD_ADVANCED') {
        const days = slipDays(m.detail);
        if (days !== null) {
          base.slip_days = days;
          base.slip_years = Math.round((days / 365.25) * 100) / 100;
        }
      }
      return base;
    });

    const systemPrompt = `You are answering questions about the ERCOT (Texas) generator interconnection queue based on the July 2026 snapshot.

Data provided in the user message:
- summary: total counts and MW by fuel category
- movers: this month's changes (June 2026 → July 2026). Each has change_type ∈ {NEW, WITHDRAWN, STATUS_ADVANCED, STATUS_REVERTED, COD_SLIPPED, COD_ADVANCED, CAPACITY_CHANGED, OWNERSHIP_CHANGED}. COD_SLIPPED and COD_ADVANCED entries include pre-computed slip_days and slip_years fields — USE THESE, do not attempt date arithmetic yourself.
- projects: current state of every project in the queue

Answer rules:
- Be direct and concrete. Cite specific projects and INRs.
- Use markdown. Link projects as [Project Name](/project/INR/).
- Do not invent data. If the question can't be answered from the provided data, say so plainly.
- Do not repeat entries. Each project should appear at most once in a list.
- Do not include entries in a list only to note they should be excluded — just leave them out.
- For thresholds like "more than a year", use strict comparison: exactly 1 year does NOT qualify.
- When asked for "the biggest" or "the most", give ONE answer unless clearly plural.
- Prefer a short bulleted list over prose when enumerating.
- Round MW to the nearest whole number. Round slip times to one decimal (e.g., "1.3 years").
- Keep the total answer under 400 words.`;

    const userContent = `Summary:
${JSON.stringify(summary)}

Movers this month (${compactMovers.length} entries):
${JSON.stringify(compactMovers)}

All projects (${projects.length} entries):
${JSON.stringify(projects)}

Question: ${question}`;

    const oaiRes = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        'authorization': `Bearer ${env.OPENAI_API_KEY}`,
      },
      body: JSON.stringify({
        // gpt-4.1-mini: 1M-token context, comparable quality to gpt-4o, faster
        model: 'gpt-4.1-mini',
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: userContent },
        ],
        max_tokens: 1500,
        temperature: 0.2,
      }),
    });

    if (!oaiRes.ok) {
      const errText = await oaiRes.text();
      return json({ error: `OpenAI error (${oaiRes.status}): ${errText.slice(0, 300)}` }, 502);
    }

    const data = await oaiRes.json();
    const answer = data.choices?.[0]?.message?.content?.trim() || '(no answer)';

    return json({ answer, model: data.model, usage: data.usage });
  } catch (e) {
    return json({ error: e.message || String(e) }, 500);
  }
}

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { 'content-type': 'application/json', ...corsHeaders() },
  });
}
