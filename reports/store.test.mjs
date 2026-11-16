// node --test reports/: store.js (0.5.18), KV's interface over D1, against SQLite (node:sqlite) as D1.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { DatabaseSync } from 'node:sqlite'
import { store, SCHEMA, CHUNK } from './store.js'
import worker from './worker.js'

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
  constructor() { this.m = new Map() }
  async put(k, v) { this.m.set(k, typeof v === 'string' ? v : new TextDecoder().decode(v)) }
  async get(k, opts) { const v = this.m.get(k); if (v == null) return null; return opts?.type === 'stream' ? new Response(v).body : v }
  async list({ prefix, cursor, limit = 100 }) {
    const all = [...this.m.keys()].filter((k) => k.startsWith(prefix)).sort()
    const start = cursor ? Number(cursor) : 0
    const keys = all.slice(start, start + limit).map((name) => ({ name, metadata: null }))
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

test('what is left in the old KV namespace is read, listed after D1 and deleted; nothing is written there', async () => {
  const kv = new FakeKV()
  await kv.put('report:2026-11-15T10:00:00.000Z:old-0001', '{"old":true}')
  const s = store({ DB: new FakeD1(), REPORTS: kv })
  await s.put('report:2026-11-16T10:00:00.000Z:new-0001', '{"new":true}')
  assert.equal(await s.get('report:2026-11-15T10:00:00.000Z:old-0001'), '{"old":true}')
  const names = []
  let cursor
  do {
    const r = await s.list({ prefix: 'report:', cursor, limit: 1 })
    names.push(...r.keys.map((k) => k.name))
    cursor = r.list_complete ? undefined : r.cursor
  } while (cursor)
  assert.deepEqual(names, ['report:2026-11-16T10:00:00.000Z:new-0001', 'report:2026-11-15T10:00:00.000Z:old-0001'])
  await s.delete('report:2026-11-15T10:00:00.000Z:old-0001')
  assert.equal(kv.m.size, 0)
  await s.put('signin:zzz', '{}')
  assert.equal(kv.m.size, 0, 'writes go to D1 only')
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
