import { put } from '@vercel/blob';

const VALID_SLOTS = new Set(['tue-eve', 'thu-lunch', 'thu-eve', 'sat-am']);
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });
  let body = req.body;
  if (typeof body === 'string') { try { body = JSON.parse(body); } catch { body = {}; } }
  body = body || {};
  // Honeypot: bots fill the hidden field; pretend success.
  if (body.company) return res.status(200).json({ ok: true });
  const email = String(body.email || '').trim().toLowerCase().slice(0, 200);
  const slots = Array.isArray(body.slots) ? body.slots.filter((s) => VALID_SLOTS.has(s)) : [];
  const tz = String(body.tz || '').slice(0, 20);
  if (!EMAIL.test(email)) return res.status(400).json({ error: 'Invalid email' });
  if (!slots.length) return res.status(400).json({ error: 'Pick at least one class' });
  const record = { email, slots, tz, createdAt: new Date().toISOString() };
  try {
    await put(`signups/${Date.now()}-${Math.random().toString(36).slice(2, 8)}.json`, JSON.stringify(record), {
      access: 'private',
      contentType: 'application/json',
      addRandomSuffix: false,
    });
    return res.status(200).json({ ok: true });
  } catch (e) {
    console.error('signup save failed', e);
    return res.status(500).json({ error: 'Could not save' });
  }
}
