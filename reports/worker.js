// OneOS reports (0.4.29): the service behind "Send to the OneOS team".
//
// A Cloudflare Worker with one Workers KV namespace (REPORTS). The app sends a
// report's zip in parts (POST /v1/part, at most 20 MiB each: one KV value holds
// 25 MiB) and then its record (POST /v1/report, schema oneos.report/1,
// app-android/core/model/.../Reports.kt). The team's server collects them with
// the admin key (GET /v1/list, /v1/get, POST /v1/delete; reports/pull.py) and
// deletes each once it has a verified copy; anything left expires after 30 days.
//
// Secrets (wrangler secret put): UPLOAD_KEY (in the app: it can only add
// reports), ADMIN_KEY (the server only), TG_TOKEN and TG_CHAT / TG_THREAD (the
// ping to the group's Phone reports topic). Nothing is served publicly, and the
// sender's address is used for the rate limit only, never stored.
//
// The ping carries only checked fields (ids, versions, the fixed checklist
// answers): the user's note and contact go to the team, never to the group.

const PART_MAX = 20 * 1024 * 1024
const RECORD_MAX = 32 * 1024
const PARTS_MAX = 4
const TTL = 30 * 24 * 3600
const ID = /^[a-z0-9]{1,32}-[0-9a-f]{4,8}$/
const TOKEN = /^[a-z0-9][a-z0-9._-]{0,47}$/
const MODEL = /^[A-Za-z0-9][A-Za-z0-9 ._+-]{0,39}$/
const SHA = /^[0-9a-f]{64}$/
const KIND = /^[A-Z_]{1,24}$/
const LABEL = /^[A-Za-z0-9][A-Za-z0-9 .+()_-]{0,47}$/
const STARTS = ['home', 'logo', 'black', 'back']
const ITEMS = ['screen', 'wifi', 'data', 'calls', 'sms', 'bluetooth', 'sound', 'camera', 'google', 'location', 'back', 'heat', 'fold']
const ANSWERS = ['works', 'problem', 'not_tried']
const LABELS = {
  screen: 'Screen', wifi: 'Wi-Fi', data: 'Mobile data', calls: 'Calls', sms: 'SMS', bluetooth: 'Bluetooth', sound: 'Sound',
  camera: 'Camera', google: 'Google', location: 'Location', back: 'Back to One UI', heat: 'Heat', fold: 'Both screens',
}
const START_LABELS = { home: 'reached the home screen', logo: 'stuck on the boot logo', black: 'black screen', back: 'came back by itself' }

export default {
  async fetch(req, env, ctx) {
    const url = new URL(req.url)
    try {
      if (req.method === 'POST' && url.pathname === '/v1/part') return await part(req, env, url)
      if (req.method === 'POST' && url.pathname === '/v1/report') return await report(req, env, ctx)
      if (req.method === 'GET' && url.pathname === '/v1/list') return await list(req, env, url)
      if (req.method === 'GET' && url.pathname === '/v1/get') return await get(req, env, url)
      if (req.method === 'POST' && url.pathname === '/v1/delete') return await del(req, env, url)
      if (req.method === 'GET' && url.pathname === '/') return reply(200, { service: 'oneos-reports' })
      return reply(404, { error: 'not found' })
    } catch (e) {
      return reply(e instanceof Refused ? e.status : 500, { error: e instanceof Refused ? e.message : 'internal error' })
    }
  },
}

class Refused extends Error {
  constructor(status, message) {
    super(message)
    this.status = status
  }
}

function reply(status, body) {
  return new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } })
}

// Constant time, so the keys cannot be guessed a character at a time.
function same(a, b) {
  if (typeof a !== 'string' || typeof b !== 'string' || !b) return false
  const x = new TextEncoder().encode(a)
  const y = new TextEncoder().encode(b)
  let d = x.length ^ y.length
  for (let i = 0; i < Math.max(x.length, y.length); i++) d |= (x[i] ?? 0) ^ (y[i] ?? 0)
  return d === 0
}

async function uploader(req, env) {
  if (!same(req.headers.get('x-oneos-key') ?? '', env.UPLOAD_KEY)) throw new Refused(401, 'bad key')
  if (env.LIMITER) {
    const { success } = await env.LIMITER.limit({ key: req.headers.get('cf-connecting-ip') ?? 'unknown' })
    if (!success) throw new Refused(429, 'too many reports, try again in a minute')
  }
}

function admin(req, env) {
  const auth = req.headers.get('authorization') ?? ''
  if (!same(auth.replace(/^Bearer /, ''), env.ADMIN_KEY)) throw new Refused(401, 'bad key')
}

function int(v, lo, hi) {
  const n = Number(v)
  if (!Number.isInteger(n) || n < lo || n > hi) throw new Refused(400, 'bad number')
  return n
}

async function part(req, env, url) {
  await uploader(req, env)
  const id = url.searchParams.get('id') ?? ''
  if (!ID.test(id)) throw new Refused(400, 'bad id')
  const n = int(url.searchParams.get('n'), 1, PARTS_MAX)
  const i = int(url.searchParams.get('i'), 0, n - 1)
  const length = int(req.headers.get('content-length'), 1, PART_MAX)
  // Streamed into KV as it arrives: the Worker never holds the part.
  await env.REPORTS.put(`part:${id}:${i}`, req.body, { expirationTtl: TTL, metadata: { n, bytes: length } })
  return reply(200, { ok: true, id, part: i })
}

// The record as sent, checked field by field; anything else in it is dropped.
function check(r) {
  const fail = (what) => { throw new Refused(400, `bad ${what}`) }
  if (r?.schema !== 'oneos.report/1') fail('schema')
  if (!ID.test(r.reportId ?? '')) fail('reportId')
  const app = r.app ?? {}
  if (!TOKEN.test(app.id ?? '') || !TOKEN.test(app.version ?? '') || !Number.isInteger(app.versionCode)) fail('app')
  if (app.series && !TOKEN.test(app.series)) fail('series')
  const phone = r.phone ?? {}
  if (!MODEL.test(phone.model ?? '') || !TOKEN.test(phone.device ?? '')) fail('phone')
  if (phone.profile != null && !TOKEN.test(phone.profile)) fail('profile')
  if (phone.label != null && !LABEL.test(phone.label)) fail('phone label')
  if (r.image != null && !TOKEN.test(r.image)) fail('image')
  if (r.imageName != null && !LABEL.test(r.imageName)) fail('image name')
  if (r.sessionId != null && !/^[0-9a-f]{8,32}$/.test(r.sessionId)) fail('sessionId')
  if (r.outcome != null && (!KIND.test(r.outcome.kind ?? '') || (r.outcome.afterSeconds != null && !Number.isInteger(r.outcome.afterSeconds)))) fail('outcome')
  if (r.checklist != null) {
    const c = r.checklist
    if (c.start != null && !STARTS.includes(c.start)) fail('start')
    for (const [k, v] of Object.entries(c.items ?? {})) if (!ITEMS.includes(k) || !ANSWERS.includes(v)) fail('checklist')
  }
  if (r.note != null && (typeof r.note !== 'string' || r.note.length > 500)) fail('note')
  if (r.contact != null && (typeof r.contact !== 'string' || r.contact.length > 64)) fail('contact')
  if (r.logs != null) {
    const l = r.logs
    if (!['session', 'probe'].includes(l.kind) || !/^[A-Za-z0-9._-]{1,80}$/.test(l.name ?? '') || typeof l.full !== 'boolean') fail('logs')
    if (!Number.isInteger(l.bytes) || l.bytes < 1 || l.bytes > PARTS_MAX * PART_MAX || !SHA.test(l.sha256 ?? '')) fail('logs')
    if (l.parts !== Math.ceil(l.bytes / PART_MAX)) fail('parts')
  }
  return {
    schema: r.schema, reportId: r.reportId, createdAt: String(r.createdAt ?? '').slice(0, 40),
    app: { id: app.id, version: app.version, versionCode: app.versionCode, series: app.series ?? '' },
    phone: { model: phone.model, device: phone.device, profile: phone.profile ?? null, label: phone.label ?? null },
    image: r.image ?? null, imageName: r.imageName ?? null, sessionId: r.sessionId ?? null, outcome: r.outcome ?? null,
    checklist: r.checklist ?? null, note: r.note ?? null, contact: r.contact ?? null, logs: r.logs ?? null,
  }
}

async function report(req, env, ctx) {
  await uploader(req, env)
  const length = int(req.headers.get('content-length'), 2, RECORD_MAX)
  const text = await req.text()
  if (text.length > length) throw new Refused(400, 'bad length')
  let parsed
  try { parsed = JSON.parse(text) } catch { throw new Refused(400, 'not JSON') }
  const r = check(parsed)
  // Every part must be there before the record is: the app sends them again otherwise.
  const missing = []
  for (let i = 0; i < (r.logs?.parts ?? 0); i++) {
    const v = await env.REPORTS.get(`part:${r.reportId}:${i}`, { type: 'stream' })
    if (v == null) missing.push(i)
    else await v.cancel()
  }
  if (missing.length) return reply(409, { error: 'missing parts', missing })
  const receivedAt = new Date().toISOString()
  await env.REPORTS.put(`report:${receivedAt}:${r.reportId}`, JSON.stringify({ ...r, receivedAt }), { expirationTtl: TTL })
  if (env.TG_TOKEN && env.TG_CHAT) ctx.waitUntil(ping(env, r).catch(() => {}))
  return reply(200, { ok: true, reportId: r.reportId })
}

function pingText(r) {
  const lines = [`📋 New report ${r.reportId}`]
  lines.push(`${r.phone.label ?? r.phone.model} (${r.phone.model}) · OneOS ${r.app.version}`)
  if (r.image) lines.push(`System: ${r.imageName ?? r.image}`)
  if (r.outcome) lines.push(`Ended: ${r.outcome.kind}${r.outcome.afterSeconds != null ? ` after ${r.outcome.afterSeconds} s` : ''}`)
  const c = r.checklist
  if (c?.start) lines.push(`Start: ${START_LABELS[c.start]}`)
  if (c?.items) {
    const by = (a) => Object.entries(c.items).filter(([, v]) => v === a).map(([k]) => LABELS[k])
    const ok = by('works')
    const bad = by('problem')
    if (ok.length) lines.push(`✅ ${ok.join(', ')}`)
    if (bad.length) lines.push(`❌ ${bad.join(', ')}`)
  }
  if (r.note) lines.push('Note: sent to the team')
  if (r.logs) lines.push(`Logs: ${r.logs.kind === 'probe' ? 'probe findings' : r.logs.full ? 'full' : 'short'}, ${(r.logs.bytes / 1048576).toFixed(1)} MB`)
  else lines.push('Logs: none')
  return lines.join('\n')
}

async function ping(env, r) {
  const body = { chat_id: env.TG_CHAT, text: pingText(r), disable_web_page_preview: true }
  if (env.TG_THREAD) body.message_thread_id = Number(env.TG_THREAD)
  await fetch(`https://api.telegram.org/bot${env.TG_TOKEN}/sendMessage`, {
    method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body),
  })
}

const KEY = /^(report:[0-9TZ:.-]{20,30}:|part:)[a-z0-9]{1,32}-[0-9a-f]{4,8}(:[0-3])?$/

async function list(req, env, url) {
  admin(req, env)
  const prefix = url.searchParams.get('prefix') === 'part:' ? 'part:' : 'report:'
  const cursor = url.searchParams.get('cursor') || undefined
  const r = await env.REPORTS.list({ prefix, cursor, limit: 100 })
  return reply(200, { keys: r.keys.map((k) => ({ name: k.name, metadata: k.metadata ?? null })), cursor: r.list_complete ? null : r.cursor })
}

async function get(req, env, url) {
  admin(req, env)
  const key = url.searchParams.get('key') ?? ''
  if (!KEY.test(key)) throw new Refused(400, 'bad key name')
  const v = await env.REPORTS.get(key, { type: 'stream' })
  if (v == null) return reply(404, { error: 'not found' })
  return new Response(v, { headers: { 'content-type': key.startsWith('part:') ? 'application/octet-stream' : 'application/json' } })
}

async function del(req, env, url) {
  admin(req, env)
  const key = url.searchParams.get('key') ?? ''
  if (!KEY.test(key)) throw new Refused(400, 'bad key name')
  await env.REPORTS.delete(key)
  return reply(200, { ok: true })
}

export { pingText, check }
