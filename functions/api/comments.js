// 63tube 共有コメント API（Pages Functions + KV）
// GET  /api/comments → 全コメント配列
// POST /api/comments → {video_id, nickname, body} を追記（上限500件）

export async function onRequestGet({ env }) {
  const list = (await env.TUBE_KV.get('comments', 'json')) || [];
  return Response.json(list, {
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
  const text = String(body.body || '').trim().slice(0, 300);
  if (!text) return Response.json({ error: 'empty' }, { status: 400 });
  const nickname = String(body.nickname || '').trim().slice(0, 24) || '名無しのPさん';
  const video_id = String(body.video_id || '').slice(0, 24);
  const comment = {
    video_id, nickname, body: text,
    created_at: new Date().toISOString(),
  };
  const list = (await env.TUBE_KV.get('comments', 'json')) || [];
  list.unshift(comment);
  if (list.length > 500) list.length = 500; // スパム膨張防止
  await env.TUBE_KV.put('comments', JSON.stringify(list));
  return Response.json({ ok: true, comment });
}
