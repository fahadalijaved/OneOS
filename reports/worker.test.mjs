// node --test reports/: the report service against an in-memory KV.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import worker, { pingText } from './worker.js'

class FakeKV {
  constructor() { this.m = new Map() }
  async put(k, v, opts) {
    const bytes = v instanceof ReadableStream ? new Uint8Array(await new Response(v).arrayBuffer()) : new TextEncoder().encode(v)
    this.m.set(k, { bytes, metadata: opts?.metadata ?? null, ttl: opts?.expirationTtl })
  }
  async get(k, opts) {
    const e = this.m.get(k)
    if (!e) return null
    return opts?.type === 'stream' ? new Response(e.bytes).body : new TextDecoder().decode(e.bytes)
  }
  async list({ prefix }) {
    return { keys: [...this.m.keys()].filter((k) => k.startsWith(prefix)).sort().map((name) => ({ name, metadata: this.m.get(name).metadata })), list_complete: true }
  }
  async delete(k) { this.m.delete(k) }
}

function env(extra = {}) {
  return { REPORTS: new FakeKV(), UPLOAD_KEY: 'up-key', ADMIN_KEY: 'admin-key', ...extra }
}
const ctx = { waits: [], waitUntil(p) { this.waits.push(p) } }
const base = 'https://oneos-reports.example.workers.dev'

function record(over = {}) {
  return {
    schema: 'oneos.report/1', reportId: '8aea312c31b8821d-3f2a', createdAt: '2026-10-29T16:40:00+05:30',
    app: { id: 'com.fahadali.oneos', version: '0.4.29-s25', versionCode: 46, series: 's25' },
    phone: { model: 'SM-S911B', device: 'dm1q', profile: 's-8550', label: 'Galaxy S23' },
    image: 'infinityx41-findx9u', imageName: 'Infinity-X 4.1', sessionId: '8aea312c31b8821d', outcome: { kind: 'GUEST_DEAD', afterSeconds: 120 },
    checklist: { start: 'home', items: { screen: 'works', wifi: 'works', calls: 'problem', camera: 'not_tried' } },
    note: 'calls drop', contact: '@tester',
    sessionApp: { version: '0.4.19', versionCode: 32, date: '2026-10-19' },
    logs: { kind: 'session', name: 'oneos-logs-8aea312c31b8821d.zip', full: true, bytes: 5, sha256: 'ab'.repeat(32), parts: 1 },
    ...over,
  }
}

async function call(e, method, path, { body, headers = {} } = {}) {
  const h = { ...headers }
  if (body != null) h['content-length'] = String(typeof body === 'string' ? new TextEncoder().encode(body).length : body.length)
  const res = await worker.fetch(new Request(base + path, { method, body, headers: h }), e, ctx)
  return { status: res.status, json: res.headers.get('content-type') === 'application/json' ? await res.json() : null, res }
}

const up = { 'x-oneos-key': 'up-key' }
const adm = { authorization: 'Bearer admin-key' }

test('a report: its part, then its record; the admin reads and deletes them', async () => {
  const e = env()
  assert.equal((await call(e, 'POST', '/v1/part?id=8aea312c31b8821d-3f2a&i=0&n=1', { body: new Uint8Array([1, 2, 3, 4, 5]), headers: up })).status, 200)
  const r = await call(e, 'POST', '/v1/report', { body: JSON.stringify(record()), headers: up })
  assert.equal(r.status, 200)
  const keys = (await call(e, 'GET', '/v1/list', { headers: adm })).json.keys
  assert.equal(keys.length, 1)
  assert.match(keys[0].name, /^report:\d{4}-\d{2}-\d{2}T[0-9:.]+Z:8aea312c31b8821d-3f2a$/)
  const got = await call(e, 'GET', `/v1/get?key=${encodeURIComponent(keys[0].name)}`, { headers: adm })
  assert.equal(got.json.note, 'calls drop')
  assert.ok(got.json.receivedAt)
  const parts = (await call(e, 'GET', '/v1/list?prefix=part:', { headers: adm })).json.keys
  assert.deepEqual(parts.map((k) => k.name), ['part:8aea312c31b8821d-3f2a:0'])
  assert.deepEqual(parts[0].metadata, { n: 1, bytes: 5 })
  const raw = await call(e, 'GET', '/v1/get?key=part:8aea312c31b8821d-3f2a:0', { headers: adm })
  assert.deepEqual([...new Uint8Array(await raw.res.arrayBuffer())], [1, 2, 3, 4, 5])
  assert.equal((await call(e, 'POST', '/v1/delete?key=part:8aea312c31b8821d-3f2a:0', { headers: adm })).status, 200)
  assert.equal(e.REPORTS.m.size, 1)
  // 30 days, then KV drops what the server never collected.
  assert.equal([...e.REPORTS.m.values()][0].ttl, 30 * 24 * 3600)
})

test('the record waits for every part', async () => {
  const e = env()
  const r = await call(e, 'POST', '/v1/report', { body: JSON.stringify(record()), headers: up })
  assert.equal(r.status, 409)
  assert.deepEqual(r.json.missing, [0])
  assert.equal(e.REPORTS.m.size, 0)
})

test('keys: upload only adds, admin only reads', async () => {
  const e = env()
  assert.equal((await call(e, 'POST', '/v1/part?id=8aea312c31b8821d-3f2a&i=0&n=1', { body: 'x', headers: { 'x-oneos-key': 'nope' } })).status, 401)
  assert.equal((await call(e, 'GET', '/v1/list', { headers: up })).status, 401)
  assert.equal((await call(e, 'GET', '/v1/list', { headers: { authorization: 'Bearer up-key' } })).status, 401)
  assert.equal((await call(e, 'POST', '/v1/report', { body: JSON.stringify(record({ logs: null })), headers: adm })).status, 401)
  // No key set on the Worker: nothing gets in.
  assert.equal((await call(env({ UPLOAD_KEY: undefined }), 'POST', '/v1/report', { body: JSON.stringify(record({ logs: null })), headers: { 'x-oneos-key': '' } })).status, 401)
})

test('bad input is refused', async () => {
  const e = env()
  for (const path of ['/v1/part?id=../x-abcd&i=0&n=1', '/v1/part?id=8aea312c-3f2a&i=4&n=4', '/v1/part?id=8aea312c-3f2a&i=0&n=5']) {
    assert.equal((await call(e, 'POST', path, { body: 'x', headers: up })).status, 400, path)
  }
  // Bigger than a part may be.
  const big = await worker.fetch(new Request(`${base}/v1/part?id=8aea312c-3f2a&i=0&n=1`, { method: 'POST', body: 'x', headers: { ...up, 'content-length': String(20 * 1024 * 1024 + 1) } }), e, ctx)
  assert.equal(big.status, 400)
  const bad = [
    { schema: 'other' }, { reportId: 'A' }, { app: { id: 'x', version: '1', versionCode: '46' } },
    { phone: { model: '<b>', device: 'dm1q' } }, { image: 'Infinity X' }, { imageName: '<a href=x>' },
    { phone: { model: 'SM-S911B', device: 'dm1q', label: 'Galaxy\nS23' } }, { outcome: { kind: 'dead; rm' } },
    { checklist: { start: 'maybe' } }, { checklist: { items: { wifi: 'great' } } }, { checklist: { items: { toaster: 'works' } } },
    { note: 'x'.repeat(501) }, { logs: { kind: 'session', name: 'a.zip', full: true, bytes: 5, sha256: 'ab'.repeat(32), parts: 2 } },
  ]
  for (const over of bad) {
    const r = await call(e, 'POST', '/v1/report', { body: JSON.stringify(record(over)), headers: up })
    assert.equal(r.status, 400, JSON.stringify(over))
  }
  assert.equal((await call(e, 'POST', '/v1/report', { body: 'not json', headers: up })).status, 400)
  assert.equal((await call(e, 'GET', '/v1/get?key=../../x', { headers: adm })).status, 400)
  assert.equal(e.REPORTS.m.size, 0)
})

test('the record keeps the app the session ran on, and refuses a bad one', async () => {
  const e = env()
  assert.equal((await call(e, 'POST', '/v1/report', { body: JSON.stringify(record({ logs: null })), headers: up })).status, 200)
  const stored = JSON.parse(new TextDecoder().decode([...e.REPORTS.m.values()][0].bytes))
  assert.deepEqual(stored.sessionApp, { version: '0.4.19', versionCode: 32, date: '2026-10-19' })
  for (const bad of [{ version: 'a b' }, { version: '0.4.19', versionCode: 'x' }, { version: '0.4.19', date: '19-10-2026' }]) {
    const body = JSON.stringify(record({ logs: null, sessionApp: bad, reportId: 'sa0x-00ff' }))
    assert.equal((await call(e, 'POST', '/v1/report', { body, headers: up })).status, 400)
  }
})

test('the ping says what was checked and who sent it, never the note', async () => {
  const sent = []
  const realFetch = globalThis.fetch
  globalThis.fetch = async (u, init) => { sent.push({ u: String(u), body: JSON.parse(init.body) }); return new Response('{}') }
  try {
    const e = env({ TG_TOKEN: 'tok', TG_CHAT: '-100', TG_THREAD: '7' })
    ctx.waits = []
    assert.equal((await call(e, 'POST', '/v1/report', { body: JSON.stringify(record({ logs: null })), headers: up })).status, 200)
    await Promise.all(ctx.waits)
    assert.equal(sent.length, 1)
    assert.equal(sent[0].body.message_thread_id, 7)
    const t = sent[0].body.text
    assert.match(t, /Galaxy S23 \(SM-S911B\) · OneOS 0\.4\.29-s25/)
    assert.match(t, /System: Infinity-X 4\.1/)
    assert.match(t, /✅ Screen, Wi-Fi/)
    assert.match(t, /❌ Calls/)
    assert.match(t, /Note: sent to the team/)
    // Who sent it (0.4.31): a Telegram username, as a mention. The note stays private.
    assert.match(t, /From: @tester/)
    assert.doesNotMatch(t, /calls drop/)
    // Anything that is not a username is named, not printed: the group is public.
    for (const [contact, shown] of [
      ['tester@example.com', 'From: an e-mail address, in the record'],
      ['+1 555 0123', 'From: a phone number, in the record'],
      ['A Tester', 'From: a contact in the record'],
      [null, 'From: no contact given'],
    ]) {
      sent.length = 0
      ctx.waits = []
      const body = JSON.stringify(record({ logs: null, contact, reportId: `c${Math.abs(shown.length)}x-00ff` }))
      assert.equal((await call(e, 'POST', '/v1/report', { body, headers: up })).status, 200)
      await Promise.all(ctx.waits)
      const got = sent[0].body.text
      assert.match(got, new RegExp(shown.replace(/[.+]/g, '\\$&')))
      if (contact) assert.doesNotMatch(got, new RegExp(contact.replace(/[.+()]/g, '\\$&')))
    }
  } finally {
    globalThis.fetch = realFetch
  }
  assert.match(pingText(record({ checklist: null, outcome: null })), /Logs: full, 0\.0 MB/)
})
