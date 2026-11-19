// node --test reports/: store.js (0.5.18), KV's interface over D1, against SQLite (node:sqlite) as D1.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { DatabaseSync } from 'node:sqlite'
import { store, SCHEMA, CHUNK } from './store.js'
import worker, { budget, sweep } from './worker.js'

// D1's prepare/bind/first/all/run/batch over SQLite; BLOBs come back as ArrayBuffer, as D1 gives them.
export class FakeD1 {
  constructor() {
    this.db = new DatabaseSync(':memory:')
    for (const s of SCHEMA) this.db.exec(s)
    this.written = 0
  }
  prepare(sql) {
    const d = this
    const conv = (row) => row && Object.fromEntries(Object.entries(row).map(([k, v]) =>
      [k, v instanceof Uint8Array ? v.buffer.slice(v.byteOffset, v.byteOffset + v.byteLength) : v]))
    const st = {
      args: [],
      bind(...a) { st.args = a.map((x) => (x instanceof Uint8Array ? Buffer.from(x) : x)); return st },
      async first() { return conv(d.db.prepare(sql).get(...st.args)) ?? null },
      async all() { return { results: d.db.prepare(sql).all(...st.args).map(conv) } },
      async run() { const r = d.db.prepare(sql).run(...st.args); d.written += Number(r.changes); return { success: true } },
    }
    return st
  }
  async batch(stmts) { this.db.exec('BEGIN'); try { for (const s of stmts) await s.run() } finally { this.db.exec('COMMIT') } }
}

class FakeKV {
  constructor() { this.m = new Map(); this.meta = new Map() }
  async put(k, v, opts) { this.m.set(k, typeof v === 'string' ? v : new TextDecoder().decode(v)); this.meta.set(k, opts?.metadata ?? null) }
  async get(k, opts) { const v = this.m.get(k); if (v == null) return null; return opts?.type === 'stream' ? new Response(v).body : v }
  async list({ prefix, cursor, limit = 100 }) {
    const all = [...this.m.keys()].filter((k) => k.startsWith(prefix)).sort()
    const start = cursor ? Number(cursor) : 0
    const keys = all.slice(start, start + limit).map((name) => ({ name, metadata: this.meta.get(name) ?? null }))
    const done = start + limit >= all.length
    return { keys, list_complete: done, cursor: done ? undefined : String(start + limit) }
  }
  async delete(k) { this.m.delete(k) }
}

test('small and large values, streams, metadata, delete', async () => {
  const s = store({ DB: new FakeD1() })
  await s.put('signin:abc', '{}', { expirationTtl: 600 })
  assert.equal(await s.get('signin:abc'), '{}')
  const big = new Uint8Array(CHUNK * 2 + 12345).map((_, i) => (i * 7) & 255)
  await s.put('part:x-0001:0', new Response(big).body, { expirationTtl: 60, metadata: { n: 1, bytes: big.length } })
  const back = new Uint8Array(await new Response(await s.get('part:x-0001:0', { type: 'stream' })).arrayBuffer())
  assert.equal(back.length, big.length)
  assert.deepEqual(back, big)
  const l = await s.list({ prefix: 'part:' })
  assert.deepEqual(l.keys, [{ name: 'part:x-0001:0', metadata: { n: 1, bytes: big.length } }])
  await s.put('part:x-0001:0', 'small now')
  assert.equal(await s.get('part:x-0001:0'), 'small now', 'a value replaced by a small one leaves no chunks')
  await s.delete('part:x-0001:0')
  assert.equal(await s.get('part:x-0001:0'), null)
})

test('expired values are gone; lists page with a cursor and keep to their prefix', async () => {
  const db = new FakeD1()
  const s = store({ DB: db })
  await s.put('member:1', '1', { expirationTtl: 3600 })
  db.db.prepare("UPDATE kv SET exp = 1 WHERE k = 'member:1'").run()
  assert.equal(await s.get('member:1'), null)
  for (let i = 0; i < 250; i++) await s.put(`report:2026-11-16T00:00:00.${String(i).padStart(3, '0')}Z:a-${String(i).padStart(4, '0')}`, '{}')
  await s.put('part:a-0001:0', 'p')
  const names = []
  let cursor
  do {
    const r = await s.list({ prefix: 'report:', cursor })
    names.push(...r.keys.map((k) => k.name))
    cursor = r.list_complete ? undefined : r.cursor
  } while (cursor)
  assert.equal(names.length, 250)
  assert.equal(new Set(names).size, 250)
  assert.ok(names.every((n) => n.startsWith('report:')))
})

test('with D1 the old KV namespace is never touched: not read, listed, deleted or written', async () => {
  const kv = new FakeKV()
  await kv.put('report:2026-11-15T10:00:00.000Z:old-0001', '{"old":true}')
  const s = store({ DB: new FakeD1(), REPORTS: kv })
  await s.put('report:2026-11-16T10:00:00.000Z:new-0001', '{"new":true}')
  assert.equal(await s.get('report:2026-11-15T10:00:00.000Z:old-0001'), null)
  const r = await s.list({ prefix: 'report:' })
  assert.deepEqual(r.keys.map((k) => k.name), ['report:2026-11-16T10:00:00.000Z:new-0001'])
  await s.delete('report:2026-11-15T10:00:00.000Z:old-0001')
  assert.equal(kv.m.size, 1, 'the old namespace is left alone')
})

test('the worker on D1: a report with a 3 MB log part is taken and collected', async () => {
  const realFetch = globalThis.fetch
  globalThis.fetch = async () => Response.json({ ok: true, result: {} })
  try {
    const env = { DB: new FakeD1(), UPLOAD_KEY: 'up', ADMIN_KEY: 'ad' }
    const ctx = { waitUntil() {} }
    const zip = new Uint8Array(3 * 1024 * 1024 + 5).fill(9)
    const p = await worker.fetch(new Request('https://x/v1/part?id=8aea312c31b8821d-3f2a&n=1&i=0',
      { method: 'POST', body: zip, headers: { 'x-oneos-key': 'up', 'content-length': String(zip.length) } }), env, ctx)
    assert.equal(p.status, 200)
    const list = await (await worker.fetch(new Request('https://x/v1/list?prefix=part:', { headers: { authorization: 'Bearer ad' } }), env, ctx)).json()
    assert.equal(list.keys[0].name, 'part:8aea312c31b8821d-3f2a:0')
    const got = await worker.fetch(new Request('https://x/v1/get?key=part:8aea312c31b8821d-3f2a:0', { headers: { authorization: 'Bearer ad' } }), env, ctx)
    assert.equal((await got.arrayBuffer()).byteLength, zip.length)
    assert.ok(env.DB.written < 10, `rows written for one 3 MB part: ${env.DB.written}`)
  } finally {
    globalThis.fetch = realFetch
  }
})

test('log parts go to KV (streamed, no CPU spent copying), records to D1', async () => {
  const kv = new FakeKV()
  const db = new FakeD1()
  const s = store({ DB: db, REPORTS: kv })
  await s.put('part:abc-0001:0', 'logbytes')
  await s.put('report:2026-11-18T10:00:00.000Z:abc-0001', '{"r":1}')
  assert.equal(kv.m.has('part:abc-0001:0'), true)
  assert.equal(kv.m.has('report:2026-11-18T10:00:00.000Z:abc-0001'), false)
  assert.equal(await s.get('part:abc-0001:0'), 'logbytes')
  assert.deepEqual((await s.list({ prefix: 'part:' })).keys.map((k) => k.name), ['part:abc-0001:0'])
  await s.delete('part:abc-0001:0')
  assert.equal(kv.m.size, 0)
})

test('budget: log parts stop at the daily cap (KV write limit), told to come back later', async () => {
  const db = new FakeD1()
  const e = { DB: db, REPORTS: new FakeKV() }
  const day = new Date().toISOString().slice(0, 10)
  const s = store(e)
  await s.put(`warned:${day}`, '1') // no Telegram call in the test
  await budget(e, 1000)
  assert.deepEqual(JSON.parse(await s.get(`budget:${day}`)), { n: 1, b: 1000 })
  await s.put(`budget:${day}`, JSON.stringify({ n: 700, b: 5000 }))
  await assert.rejects(budget(e, 1000), (err) => err.status === 503)
  // Bytes: what KV holds now stays under 800 MB.
  await s.put(`budget:${day}`, JSON.stringify({ n: 1, b: 799 * 1024 * 1024 }))
  await s.put('stored', JSON.stringify({ t: Date.now(), b: 799 * 1024 * 1024 }))
  await assert.rejects(budget(e, 2 * 1024 * 1024), (err) => err.status === 503)
})

test('budget: bytes the puller already collected do not count (11-19: 839 MB uploaded, 70 KB stored, every log refused)', async () => {
  const kv = new FakeKV()
  const e = { DB: new FakeD1(), REPORTS: kv }
  const day = new Date().toISOString().slice(0, 10)
  const yday = new Date(Date.now() - 86400000).toISOString().slice(0, 10)
  const s = store(e)
  await s.put(`warned:${day}`, '1')
  await s.put(`budget:${yday}`, JSON.stringify({ n: 69, b: 838850180 }))
  await s.put(`budget:${day}`, JSON.stringify({ n: 3, b: 200 * 1024 * 1024 }))
  await s.put('part:abc-0001:0', 'x'.repeat(70000), { metadata: { n: 1, bytes: 70000 } })
  await budget(e, 5 * 1024 * 1024)
  assert.equal(JSON.parse(await s.get('stored')).b, 70000 + 5 * 1024 * 1024)
  // The cached figure grows with each upload until the next count.
  await budget(e, 1000)
  assert.equal(JSON.parse(await s.get('stored')).b, 70000 + 5 * 1024 * 1024 + 1000)
})

test('sweep: leftover parts older than 6 hours go, newer ones stay', async () => {
  const now = Date.now() / 1000
  const keys = [
    { name: 'part:old-0001:0', expiration: Math.floor(now + 2 * 86400 - 7 * 3600) },
    { name: 'part:new-0001:0', expiration: Math.floor(now + 2 * 86400 - 3600) },
  ]
  const gone = []
  const kv = { list: async () => ({ keys, list_complete: true }), delete: async (k) => { gone.push(k) } }
  await sweep({ REPORTS: kv, DB: new FakeD1() })
  assert.deepEqual(gone, ['part:old-0001:0'])
})
