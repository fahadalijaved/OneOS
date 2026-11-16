// OneOS reports (0.5.18): the service's storage, KV's interface over D1.
//
// Workers KV on the free plan takes 1000 writes a day; on 2026-11-16 a flood of fake reports and the per-account
// counters used them up and every sign-in and report failed with 500 until midnight UTC. D1 (the DB binding) takes
// 100 000 rows written a day on the same plan. This keeps the calls the Worker made on KV (get, put with
// expirationTtl and metadata, delete, list by prefix with a cursor) and stores in D1:
//   kv(k, v, exp, meta, n): a value up to CHUNK bytes in v; a larger one (a log part, up to 20 MiB) in n rows of
//   kv_chunk(k, i, v), since a D1 row holds at most 2 MB.
// Expired rows are never returned and are dropped now and then on a write. Anything still in the KV namespace
// (REPORTS, from before) is read, listed and deleted after D1's, never written: it empties itself as pull.py
// collects it and as its own TTL runs out.

export const CHUNK = 1024 * 1024
const enc = new TextEncoder()
const dec = new TextDecoder()
const now = () => Math.floor(Date.now() / 1000)

export const SCHEMA = [
  'CREATE TABLE IF NOT EXISTS kv (k TEXT PRIMARY KEY, v BLOB, exp INTEGER, meta TEXT, n INTEGER NOT NULL DEFAULT 0)',
  'CREATE TABLE IF NOT EXISTS kv_chunk (k TEXT NOT NULL, i INTEGER NOT NULL, v BLOB NOT NULL, PRIMARY KEY (k, i))',
  'CREATE INDEX IF NOT EXISTS kv_exp ON kv (exp)',
]

async function bytes(value) {
  if (typeof value === 'string') return enc.encode(value)
  if (value instanceof Uint8Array) return value
  if (value instanceof ArrayBuffer) return new Uint8Array(value)
  return new Uint8Array(await new Response(value).arrayBuffer())
}

function d1(db) {
  const live = '(exp IS NULL OR exp > ?)'
  return {
    async get(key, opts) {
      const row = await db.prepare(`SELECT v, n FROM kv WHERE k = ? AND ${live}`).bind(key, now()).first()
      if (!row) return null
      let b
      if (row.n > 0) {
        const { results } = await db.prepare('SELECT v FROM kv_chunk WHERE k = ? ORDER BY i').bind(key).all()
        if (results.length !== row.n) return null
        const parts = results.map((r) => new Uint8Array(r.v))
        b = new Uint8Array(parts.reduce((s, p) => s + p.length, 0))
        let o = 0
        for (const p of parts) { b.set(p, o); o += p.length }
      } else {
        b = new Uint8Array(row.v ?? new ArrayBuffer(0))
      }
      if (opts?.type === 'stream') return new Response(b).body
      return dec.decode(b)
    },
    async put(key, value, opts = {}) {
      const b = await bytes(value)
      const exp = opts.expirationTtl ? now() + opts.expirationTtl : null
      const meta = opts.metadata == null ? null : JSON.stringify(opts.metadata)
      const stmts = [db.prepare('DELETE FROM kv_chunk WHERE k = ?').bind(key)]
      if (b.length <= CHUNK) {
        stmts.push(db.prepare('INSERT OR REPLACE INTO kv (k, v, exp, meta, n) VALUES (?, ?, ?, ?, 0)').bind(key, b, exp, meta))
      } else {
        const n = Math.ceil(b.length / CHUNK)
        for (let i = 0; i < n; i++) {
          stmts.push(db.prepare('INSERT INTO kv_chunk (k, i, v) VALUES (?, ?, ?)').bind(key, i, b.subarray(i * CHUNK, (i + 1) * CHUNK)))
        }
        stmts.push(db.prepare('INSERT OR REPLACE INTO kv (k, v, exp, meta, n) VALUES (?, NULL, ?, ?, ?)').bind(key, exp, meta, n))
      }
      await db.batch(stmts)
      // Now and then, what ran out (one write in fifty; a few rows each time).
      if (Math.random() < 0.02) {
        const t = now()
        await db.batch([
          db.prepare('DELETE FROM kv_chunk WHERE k IN (SELECT k FROM kv WHERE exp IS NOT NULL AND exp <= ? LIMIT 50)').bind(t),
          db.prepare('DELETE FROM kv WHERE k IN (SELECT k FROM kv WHERE exp IS NOT NULL AND exp <= ? LIMIT 50)').bind(t),
        ])
      }
    },
    async delete(key) {
      await db.batch([db.prepare('DELETE FROM kv_chunk WHERE k = ?').bind(key), db.prepare('DELETE FROM kv WHERE k = ?').bind(key)])
    },
    async list({ prefix, cursor, limit = 100 }) {
      const { results } = await db.prepare(`SELECT k, meta FROM kv WHERE k >= ? AND k < ? AND k > ? AND ${live} ORDER BY k LIMIT ?`)
        .bind(prefix, prefix + '￿', cursor ?? '', now(), limit + 1).all()
      const keys = results.slice(0, limit).map((r) => ({ name: r.k, metadata: r.meta == null ? null : JSON.parse(r.meta) }))
      const more = results.length > limit
      return { keys, list_complete: !more, cursor: more ? keys[keys.length - 1].name : undefined }
    },
  }
}

// D1 first, the old KV namespace after it for reads; writes to D1 only. Without a DB binding: KV as before.
export function store(env) {
  if (!env.DB) return env.REPORTS
  const a = d1(env.DB)
  const old = env.REPORTS
  return {
    async get(key, opts) {
      const v = await a.get(key, opts)
      return v != null || !old ? v : old.get(key, opts)
    },
    put: (key, value, opts) => a.put(key, value, opts),
    async delete(key) {
      await a.delete(key)
      if (old) await old.delete(key).catch(() => {})
    },
    // The cursor says which store: "d1:<last key>" or "kv:<KV's cursor>".
    async list({ prefix, cursor, limit = 100 }) {
      if (!cursor || cursor.startsWith('d1:')) {
        const r = await a.list({ prefix, cursor: cursor ? cursor.slice(3) : undefined, limit })
        if (!r.list_complete) return { keys: r.keys, list_complete: false, cursor: 'd1:' + r.cursor }
        if (!old) return r
        if (r.keys.length) return { keys: r.keys, list_complete: false, cursor: 'kv:' }
        cursor = 'kv:'
      }
      const r = await old.list({ prefix, cursor: cursor.slice(3) || undefined, limit })
      return { keys: r.keys, list_complete: r.list_complete, cursor: r.list_complete ? undefined : 'kv:' + r.cursor }
    },
  }
}
