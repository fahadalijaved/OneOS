// node --test reports/: 0.5.16 group-only reports (sign-in through the bot, the pass, the group check).
import { test, beforeEach, afterEach } from 'node:test'
import assert from 'node:assert/strict'
import worker from './worker.js'

class FakeKV {
  constructor() { this.m = new Map() }
  async put(k, v, opts) {
    const bytes = v instanceof ReadableStream ? new Uint8Array(await new Response(v).arrayBuffer()) : new TextEncoder().encode(v)
    this.m.set(k, { bytes, ttl: opts?.expirationTtl, metadata: opts?.metadata ?? null })
  }
  async get(k, opts) {
    const e = this.m.get(k)
    if (!e) return null
    return opts?.type === 'stream' ? new Response(e.bytes).body : new TextDecoder().decode(e.bytes)
  }
  async list({ prefix }) { return { keys: [...this.m.keys()].filter((k) => k.startsWith(prefix)).map((name) => ({ name })), list_complete: true } }
  async delete(k) { this.m.delete(k) }
}

const base = 'https://oneos-reports.example.workers.dev'
const up = { 'x-oneos-key': 'up-key' }
let status, tgCalls, realFetch
function env(extra = {}) {
  return { REPORTS: new FakeKV(), UPLOAD_KEY: 'up-key', ADMIN_KEY: 'admin-key', PASS_KEY: 'pass-key', TG_HOOK: 'hook-key',
    TG_BOT: 'OneOSBot', TG_TOKEN: 't', TG_CHAT: '-1001', ...extra }
}
function ctx() { return { waits: [], waitUntil(p) { this.waits.push(p) } } }

beforeEach(() => {
  status = { 42: 'member', 7: 'kicked' }
  tgCalls = []
  realFetch = globalThis.fetch
  globalThis.fetch = async (url, init) => {
    const method = String(url).split('/').pop()
    const body = JSON.parse(init.body)
    tgCalls.push({ method, body })
    if (method === 'getChatMember') {
      const s = status[body.user_id]
      if (s === 'down') throw new Error('network')
      return Response.json(s ? { ok: true, result: { status: s, is_member: s === 'restricted-in' } } : { ok: false, error_code: 400, description: 'user not found' })
    }
    return Response.json({ ok: true, result: {} })
  }
})
afterEach(() => { globalThis.fetch = realFetch })

async function call(e, method, path, { body, headers = {}, c = ctx() } = {}) {
  const h = { ...headers }
  if (body != null) h['content-length'] = String(new TextEncoder().encode(body).length)
  const res = await worker.fetch(new Request(base + path, { method, body, headers: h }), e, c)
  await Promise.all(c.waits)
  return { status: res.status, json: await res.json() }
}

const startMsg = (text, from = { id: 42, username: 'tester_one' }, type = 'private') =>
  JSON.stringify({ update_id: 1, message: { message_id: 1, date: Math.floor(Date.now() / 1000), chat: { id: from.id, type }, from, text } })

async function signIn(e, from = { id: 42, username: 'tester_one' }) {
  const s = await call(e, 'POST', '/v1/signin', { headers: up })
  assert.equal(s.status, 200)
  assert.equal(s.json.url, `https://t.me/OneOSBot?start=${s.json.code}`)
  assert.equal((await call(e, 'POST', `/v1/claim?code=${s.json.code}`, { headers: up })).status, 202)
  const h = await call(e, 'POST', '/v1/tg', { body: startMsg(`/start ${s.json.code}`, from), headers: { 'x-telegram-bot-api-secret-token': 'hook-key' } })
  assert.equal(h.status, 200)
  const c = await call(e, 'POST', `/v1/claim?code=${s.json.code}`, { headers: up })
  assert.equal(c.status, 200)
  assert.equal((await call(e, 'POST', `/v1/claim?code=${s.json.code}`, { headers: up })).status, 404, 'a code is used once')
  return c.json
}

const rec = (over = {}) => JSON.stringify({
  schema: 'oneos.report/1', reportId: '8aea312c31b8821d-3f2a',
  app: { id: 'com.fahadali.oneos', version: '0.5.16', versionCode: 145 },
  phone: { model: 'SM-A366B', device: 'a36xq' }, contact: '@someone_else', tg: { id: 1, username: 'spoofed' }, ...over,
})

test('a member signs in through the bot and sends a report; the record and the ping name the account from the pass', async () => {
  const e = env()
  const got = await signIn(e)
  assert.equal(got.member, true)
  assert.equal(got.username, 'tester_one')
  assert.ok(tgCalls.some((c) => c.method === 'sendMessage' && c.body.chat_id === 42 && /Signed in/.test(c.body.text)))
  const c = ctx()
  const r = await call(e, 'POST', '/v1/report', { body: rec(), headers: { ...up, 'x-oneos-pass': got.pass }, c })
  assert.equal(r.status, 200)
  const key = [...e.REPORTS.m.keys()].find((k) => k.startsWith('report:'))
  const stored = JSON.parse(await e.REPORTS.get(key))
  assert.deepEqual(stored.tg, { id: 42, username: 'tester_one' })
  const ping = tgCalls.find((x) => x.method === 'sendMessage' && x.body.chat_id === '-1001')
  assert.match(ping.body.text, /From: @tester_one/)
})

test('a banned account and one that never joined are refused with the group link; joining works at once', async () => {
  const e = env()
  const got = await signIn(e, { id: 7, username: 'banned_one' })
  assert.equal(got.member, false)
  assert.ok(tgCalls.some((c) => c.method === 'sendMessage' && c.body.chat_id === 7 && /t\.me\/TheoneOS/.test(c.body.text)))
  let r = await call(e, 'POST', '/v1/part?id=8aea312c31b8821d-3f2a&i=0&n=1', { body: 'abcde', headers: { ...up, 'x-oneos-pass': got.pass } })
  assert.equal(r.status, 403)
  assert.equal(r.json.join, true)
  assert.equal(r.json.group, 'https://t.me/TheoneOS')
  assert.ok(![...e.REPORTS.m.keys()].some((k) => k.startsWith('part:')), 'nothing stored for a refused sender')
  status[7] = 'member'
  r = await call(e, 'POST', '/v1/report', { body: rec(), headers: { ...up, 'x-oneos-pass': got.pass } })
  assert.equal(r.status, 200)
  const other = await signIn(e, { id: 99, username: 'never_joined' })
  assert.equal(other.member, false)
  assert.equal((await call(e, 'POST', '/v1/report', { body: rec(), headers: { ...up, 'x-oneos-pass': other.pass } })).status, 403)
})

test('a forged, altered or foreign-key pass is refused as "sign in again"', async () => {
  const e = env()
  const { pass } = await signIn(e)
  const [body, sig] = pass.split('.')
  const evil = Buffer.from(JSON.stringify({ id: 7, u: 'x', exp: 9e9 })).toString('base64url')
  for (const p of [`${evil}.${sig}`, `${body}.${sig.slice(0, -2)}AA`, 'garbage', `${body}.${sig}.x`]) {
    const r = await call(e, 'POST', '/v1/report', { body: rec(), headers: { ...up, 'x-oneos-pass': p } })
    assert.equal(r.status, 403, p)
    assert.equal(r.json.signin, true)
  }
  const e2 = env({ PASS_KEY: 'other-key' })
  assert.equal((await call(e2, 'POST', '/v1/report', { body: rec(), headers: { ...up, 'x-oneos-pass': pass } })).status, 403)
})

test('an app without a pass: taken until REQUIRE_MEMBER is 1, then refused with a sign-in hint', async () => {
  assert.equal((await call(env(), 'POST', '/v1/report', { body: rec(), headers: up })).status, 200)
  const r = await call(env({ REQUIRE_MEMBER: '1' }), 'POST', '/v1/report', { body: rec(), headers: up })
  assert.equal(r.status, 403)
  assert.equal(r.json.signin, true)
})

test('the webhook: wrong secret, group chats, bots, unknown and reused codes do not sign anyone in', async () => {
  const e = env()
  const s = (await call(e, 'POST', '/v1/signin', { headers: up })).json
  const hk = { 'x-telegram-bot-api-secret-token': 'hook-key' }
  assert.equal((await call(e, 'POST', '/v1/tg', { body: startMsg(`/start ${s.code}`), headers: { 'x-telegram-bot-api-secret-token': 'nope' } })).status, 401)
  await call(e, 'POST', '/v1/tg', { body: startMsg(`/start ${s.code}`, { id: 42 }, 'supergroup'), headers: hk })
  await call(e, 'POST', '/v1/tg', { body: startMsg(`/start ${s.code}`, { id: 5, is_bot: true }), headers: hk })
  assert.equal((await call(e, 'POST', `/v1/claim?code=${s.code}`, { headers: up })).status, 202)
  await call(e, 'POST', '/v1/tg', { body: startMsg('/start AAAAAAAAAAAAAAAAAAAAAA'), headers: hk })
  const old = JSON.parse(startMsg(`/start ${s.code}`, { id: 7 }))
  old.message.date -= 3600
  const before = tgCalls.length
  await call(e, 'POST', '/v1/tg', { body: JSON.stringify(old), headers: hk })
  assert.equal(tgCalls.length, before, 'an hour-old message gets no answer and signs no one in')
  assert.equal((await call(e, 'POST', '/v1/tg', { body: 'not json', headers: hk })).status, 200)
  await call(e, 'POST', '/v1/tg', { body: startMsg(`/start ${s.code}`, { id: 42 }), headers: hk })
  await call(e, 'POST', '/v1/tg', { body: startMsg(`/start ${s.code}`, { id: 7 }), headers: hk })
  const c = await call(e, 'POST', `/v1/claim?code=${s.code}`, { headers: up })
  assert.equal(c.status, 200)
  assert.equal(c.json.member, true, 'the first account to press Start keeps the code')
  assert.equal((await call(e, 'POST', '/v1/signin', { headers: {} })).status, 401)
  assert.equal((await call(e, 'POST', '/v1/claim?code=bad', { headers: up })).status, 400)
})

test('Telegram down: 503, not a refusal; sign-in not set up: 503', async () => {
  const e = env()
  const { pass } = await signIn(e)
  e.REPORTS.m.delete('member:42')
  status[42] = 'down'
  assert.equal((await call(e, 'POST', '/v1/report', { body: rec(), headers: { ...up, 'x-oneos-pass': pass } })).status, 503)
  assert.equal((await call(env({ PASS_KEY: undefined }), 'POST', '/v1/signin', { headers: up })).status, 503)
})
