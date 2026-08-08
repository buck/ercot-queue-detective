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

    const compactMovers = (movers.movers || []).map(m => ({
      inr: m.inr,
      change: m.change_type,
      detail: m.detail,
      name: m.project_name,
      mw: m.capacity_mw,
      fuel: m.fuel,
      county: m.county,
    }));

    const systemPrompt = `You are answering questions about the ERCOT (Texas) generator interconnection queue based on the July 2026 snapshot.

Answer concisely (typically 1-4 sentences, or a short bulleted list). Name specific projects with their INRs. Format links to project pages as [Project Name](/project/INR/). Round MW figures reasonably.

Data provided in the user message:
- summary: total counts and MW by fuel category
- movers: this month's changes (June 2026 → July 2026). Each has change_type ∈ {NEW, WITHDRAWN, STATUS_ADVANCED, STATUS_REVERTED, COD_SLIPPED, COD_ADVANCED, CAPACITY_CHANGED, OWNERSHIP_CHANGED}.
- projects: current state of every project in the queue

Rules:
- Cite specific projects and INRs when relevant.
- Use markdown. Link projects as [Name](/project/INR/).
- Do not invent data. If the question can't be answered from the provided data, say so plainly.
- If the user asks something ambiguous, pick the most useful interpretation and answer.
- Prefer specificity over hedging.`;

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
        max_tokens: 600,
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
