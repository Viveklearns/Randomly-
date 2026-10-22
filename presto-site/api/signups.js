import { list, get } from '@vercel/blob';

// Private export of sign-ups: /api/signups?key=ADMIN_KEY  (add &format=json for JSON)
export default async function handler(req, res) {
  const key = (req.query && req.query.key) || '';
  if (!process.env.ADMIN_KEY || key !== process.env.ADMIN_KEY) return res.status(401).send('Unauthorized');
  const rows = [];
  let cursor;
  do {
    const page = await list({ prefix: 'signups/', cursor, limit: 1000 });
    for (const b of page.blobs) {
      const r = await get(b.pathname, { access: 'private' });
      if (r && r.stream) rows.push(JSON.parse(await new Response(r.stream).text()));
    }
    cursor = page.hasMore ? page.cursor : undefined;
  } while (cursor);
  rows.sort((a, b) => a.createdAt.localeCompare(b.createdAt));
  if (req.query.format === 'json') return res.status(200).json(rows);
  const esc = (v) => `"${String(v).replace(/"/g, '""')}"`;
  const csv = ['created_at,email,time_zone,classes', ...rows.map((r) => [r.createdAt, r.email, r.tz, r.slots.join(' | ')].map(esc).join(','))].join('\n');
  res.setHeader('Content-Type', 'text/csv; charset=utf-8');
  return res.status(200).send(csv);
}
