// 63tube 共有ハートカウンター API（Pages Functions + KV）
// GET  /api/likes → {video_id: count}
// POST /api/likes → {video_id, n} n件加算（1リクエスト最大20）

export async function onRequestGet({ env }) {
  const counts = (await env.TUBE_KV.get('likes', 'json')) || {};
  return Response.json(counts, {
    headers: { 'Cache-Control': 'no-store' },
  });
}

export async function onRequestPost({ env, request }) {
  let body;
  try {
    body = await request.json();
  } catch {
    return Response.json({ error: 'invalid json' }, { status: 400 });
  }
  const video_id = String(body.video_id || '').slice(0, 24);
  if (!video_id) return Response.json({ error: 'no video_id' }, { status: 400 });
  const n = Math.min(Math.max(parseInt(body.n, 10) || 1, 1), 20);
  const counts = (await env.TUBE_KV.get('likes', 'json')) || {};
  counts[video_id] = (counts[video_id] || 0) + n;
  await env.TUBE_KV.put('likes', JSON.stringify(counts));
  return Response.json({ ok: true, count: counts[video_id] });
}
