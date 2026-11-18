// OneOS reports (0.4.29): the service behind "Send to the OneOS team".
//
// A Cloudflare Worker; its storage is D1 since 0.5.18 (store.js: KV's interface; the Workers KV namespace
// REPORTS before it is only read and emptied). The app sends a
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
// answers) and, from 0.4.31, who sent it: the owner asked, since a report that
// names no one cannot be followed up. The contact is free text the tester typed,
// so only a Telegram username is shown, as a mention; an e-mail or a phone
// number is named as such and stays in the record (t.me/TheoneOS is a public
// group). The note still goes to the team only.
//
// 0.5.16 (owner 2026-11-15: "reports need to be refused ! we cant be solving
// issues of people that didnt even bother joining the group"): a report is
// taken only from a member of the OneOS Telegram group. The app signs in once
// through our bot: POST /v1/signin gives a one-time code and the bot's
// t.me/<bot>?start=<code> link; the bot's webhook (POST /v1/tg, Telegram's
// secret-token header) ties the code to the Telegram account that pressed
// Start; POST /v1/claim hands the app a pass signed with PASS_KEY (the account's
// id and username, good for 180 days). Every upload carries the pass
// (X-OneOS-Pass) and is checked against the group (getChatMember: a member, an
// admin or a restricted member; left or banned is refused with the group's
// link). Only a yes is cached, for an hour, so joining works at once. An app
// without a pass (0.5.15 and older) is taken until REQUIRE_MEMBER is "1".
// Installing and running OneOS stay open to everyone; only reports are gated.
// New secrets: PASS_KEY, TG_HOOK (the webhook's secret token), TG_BOT and
// TG_SIGNIN_TOKEN: the sign-in bot (@OneOSReportsBot, an admin of the group) is
// its own bot; the group pings stay on TG_TOKEN.

import { store } from './store.js'

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
const GROUP_LINK = 'https://t.me/TheoneOS'
const PASS_SECONDS = 180 * 24 * 3600
const SIGNIN_TTL = 600
const MEMBER_TTL = 3600
// 0.5.18, per signed-in account (2026-11-16: one pass sent 1115 reports of one session at the 30-a-minute IP limit,
// and its counters in KV used up the free plan's 1000 KV writes a day: every sign-in and report failed with 500).
// Counted by Cloudflare's rate limiters (no KV write): USER_LIMITER takes 3 reports a minute per account, more are
// refused (429); FLOOD_LIMITER counts every try, refused ones included, and an account past 15 a minute is banned
// from the group (owner: "ban anyone who spams like this"); a real sender stops at a refusal (the app tries a 429
// three times). The ban is the only write: banned:<id>, which refuses the account from then on.
const CODE = /^[A-Za-z0-9_-]{22}$/
const REPORTS_PAUSED = false
// 11-18 (four throwaway accounts sent 622 fake reports in two days): an account's reports are held, stored but not
// posted in the topic, for its first two days after its first sign-in (seen:<id>), and five a day is the most taken.
const HOLD_SECONDS = 2 * 24 * 3600
const DAILY_MAX = 5
const START_LABELS = { home: 'reached the home screen', logo: 'stuck on the boot logo', black: 'black screen', back: 'came back by itself' }

export default {
  async scheduled(event, env, ctx) {
    ctx.waitUntil(sweep(env).catch(() => {}))
  },
  async fetch(req, env, ctx) {
    const url = new URL(req.url)
    try {
      // 11-18 (owner: "Stop all reports"): new reports are refused until this is turned back on.
      if (REPORTS_PAUSED && req.method === 'POST' && (url.pathname === '/v1/part' || url.pathname === '/v1/report'))
        return reply(503, { error: 'reports are paused for now' })
      if (req.method === 'POST' && url.pathname === '/v1/part') return await part(req, env, url)
      if (req.method === 'POST' && url.pathname === '/v1/report') return await report(req, env, ctx)
      if (req.method === 'POST' && url.pathname === '/v1/hello') return await hello(req, env)
      if (req.method === 'POST' && url.pathname === '/v1/signin') return await signin(req, env)
      if (req.method === 'POST' && url.pathname === '/v1/claim') return await claim(req, env, url)
      if (req.method === 'POST' && url.pathname === '/v1/tg') return await hook(req, env, ctx)
      if (req.method === 'GET' && url.pathname === '/v1/list') return await list(req, env, url)
      if (req.method === 'GET' && url.pathname === '/v1/get') return await get(req, env, url)
      if (req.method === 'POST' && url.pathname === '/v1/delete') return await del(req, env, url)
      if (req.method === 'GET' && url.pathname === '/') return reply(200, { service: 'oneos-reports' })
      return reply(404, { error: 'not found' })
    } catch (e) {
      return reply(e instanceof Refused ? e.status : 500, e instanceof Refused ? { error: e.message, ...e.extra } : { error: 'internal error' })
    }
  },
}

class Refused extends Error {
  constructor(status, message, extra = {}) {
    super(message)
    this.status = status
    this.extra = extra
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

function appKey(req, env) {
  if (!same(req.headers.get('x-oneos-key') ?? '', env.UPLOAD_KEY)) throw new Refused(401, 'bad key')
}

async function limited(req, env) {
  if (env.LIMITER) {
    const { success } = await env.LIMITER.limit({ key: req.headers.get('cf-connecting-ip') ?? 'unknown' })
    if (!success) throw new Refused(429, 'too many reports, try again in a minute')
  }
}

// The sender of an upload: the group member its pass names, or null for an app
// without a pass while those are still taken (REQUIRE_MEMBER unset).
async function uploader(req, env) {
  appKey(req, env)
  await limited(req, env)
  const pass = req.headers.get('x-oneos-pass')
  if (!pass) {
    if (env.REQUIRE_MEMBER === '1') {
      throw new Refused(403, 'reports are for members of the OneOS group: update OneOS and sign in with Telegram', { signin: true, group: GROUP_LINK })
    }
    return null
  }
  const user = await readPass(env, pass)
  if (!user) throw new Refused(403, 'sign in with Telegram again', { signin: true, group: GROUP_LINK })
  if (!(await isMember(env, user.id))) throw new Refused(403, 'reports are for members of the OneOS group: join it, then send again', { join: true, group: GROUP_LINK })
  return user
}

async function perUser(env, user) {
  if (env.FLOOD_LIMITER && !(await env.FLOOD_LIMITER.limit({ key: String(user.id) })).success) {
    await floodBan(env, user)
    throw new Refused(403, 'this account was banned from the OneOS group for flooding reports')
  }
  if (env.USER_LIMITER && !(await env.USER_LIMITER.limit({ key: String(user.id) })).success) {
    throw new Refused(429, 'too many reports from this account, try again in a few minutes')
  }
}

// Ban from the group (the sign-in bot is an admin there) and remember it (the one KV write), say so in the topic.
async function floodBan(env, user) {
  if ((await store(env).get(`banned:${user.id}`)) === '1') return
  await store(env).put(`banned:${user.id}`, '1')
  let ok = false
  try { ok = (await tg(env, 'banChatMember', { chat_id: env.TG_CHAT, user_id: user.id, revoke_messages: true }))?.ok === true } catch {}
  const who = user.username ? `@${user.username}` : 'an account'
  const body = { chat_id: env.TG_CHAT, disable_web_page_preview: true,
    text: `🚫 ${who} (id ${user.id}) sent more than 15 reports in a minute: ${ok ? 'banned from the group' : 'ban FAILED, ban by hand'}. Its report pings stay; delete them by hand.` }
  if (env.TG_THREAD) body.message_thread_id = Number(env.TG_THREAD)
  try { await tg(env, 'sendMessage', body) } catch {}
}

// --- Sign-in through the bot, the pass, the group check (0.5.16) ---

const enc = (s) => new TextEncoder().encode(s)

function b64url(bytes) {
  let s = ''
  for (const b of bytes) s += String.fromCharCode(b)
  return btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

function unb64url(s) {
  const t = atob(s.replace(/-/g, '+').replace(/_/g, '/'))
  return Uint8Array.from(t, (c) => c.charCodeAt(0))
}

async function hmac(env, data) {
  const key = await crypto.subtle.importKey('raw', enc(env.PASS_KEY), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign'])
  return b64url(new Uint8Array(await crypto.subtle.sign('HMAC', key, enc(data))))
}

async function makePass(env, user) {
  const body = b64url(enc(JSON.stringify({ id: user.id, u: user.username, exp: Math.floor(Date.now() / 1000) + PASS_SECONDS })))
  return `${body}.${await hmac(env, body)}`
}

async function readPass(env, pass) {
  if (!env.PASS_KEY || pass.length > 600 || !/^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$/.test(pass)) return null
  const [body, sig] = pass.split('.')
  if (!same(sig, await hmac(env, body))) return null
  let p
  try { p = JSON.parse(new TextDecoder().decode(unb64url(body))) } catch { return null }
  if (!Number.isSafeInteger(p?.id) || p.id <= 0 || !(p.exp > Date.now() / 1000)) return null
  return { id: p.id, username: typeof p.u === 'string' && TG_USER.test(p.u) ? p.u : null }
}

// The sign-in bot answers /start and checks the group; TG_TOKEN when there is none.
async function tg(env, method, body) {
  const res = await fetch(`https://api.telegram.org/bot${env.TG_SIGNIN_TOKEN || env.TG_TOKEN}/${method}`, {
    method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body),
  })
  return res.json()
}

async function isMember(env, id) {
  if ((await store(env).get(`banned:${id}`)) === '1') return false
  if ((await store(env).get(`member:${id}`)) === '1') return true
  let r
  try { r = await tg(env, 'getChatMember', { chat_id: env.TG_CHAT, user_id: id }) } catch { r = null }
  // 400: Telegram does not know this account in the group (never joined).
  if (r?.ok !== true && r?.error_code !== 400) throw new Refused(503, 'the group could not be checked, try again in a minute')
  const m = r.ok ? r.result : {}
  const yes = ['creator', 'administrator', 'member'].includes(m.status) || (m.status === 'restricted' && m.is_member === true)
  if (yes) await store(env).put(`member:${id}`, '1', { expirationTtl: MEMBER_TTL })
  return yes
}

function signinReady(env) {
  if (!env.PASS_KEY || !env.TG_BOT || !env.TG_TOKEN || !env.TG_CHAT) throw new Refused(503, 'sign-in is not set up')
}

async function signin(req, env) {
  appKey(req, env)
  await limited(req, env)
  signinReady(env)
  const code = b64url(crypto.getRandomValues(new Uint8Array(16)))
  await store(env).put(`signin:${code}`, '{}', { expirationTtl: SIGNIN_TTL })
  return reply(200, { code, url: `https://t.me/${env.TG_BOT}?start=${code}`, group: GROUP_LINK, expiresIn: SIGNIN_TTL })
}

// Asked every few seconds while the app waits (no rate limit: one KV read).
async function claim(req, env, url) {
  appKey(req, env)
  signinReady(env)
  const code = url.searchParams.get('code') ?? ''
  if (!CODE.test(code)) throw new Refused(400, 'bad code')
  const v = await store(env).get(`signin:${code}`)
  if (v == null) throw new Refused(404, 'the sign-in ran out, start it again')
  const who = JSON.parse(v)
  if (!who.id) return reply(202, { waiting: true })
  await store(env).delete(`signin:${code}`)
  if ((await store(env).get(`seen:${who.id}`)) == null) await store(env).put(`seen:${who.id}`, String(Date.now()))
  const member = await isMember(env, who.id)
  return reply(200, { pass: await makePass(env, who), username: who.username, member, group: GROUP_LINK })
}

// The bot's webhook: only "/start <code>" in a private chat does anything.
async function hook(req, env, ctx) {
  if (!same(req.headers.get('x-telegram-bot-api-secret-token') ?? '', env.TG_HOOK)) throw new Refused(401, 'bad key')
  let u
  try { u = await req.json() } catch { return reply(200, { ok: true }) }
  if (u?.chat_join_request || u?.chat_member || u?.callback_query) {
    ctx.waitUntil(screening(env, u).catch(() => {}))
    return reply(200, { ok: true })
  }
  const m = u?.message
  const from = m?.from
  if (m?.chat?.type !== 'private' || !from || from.is_bot || !Number.isSafeInteger(from.id) || typeof m.text !== 'string') return reply(200, { ok: true })
  // Old messages (the bot had no webhook before 0.5.16; Telegram hands over what waited) get no answer.
  if (!(Date.now() / 1000 - m.date < SIGNIN_TTL)) return reply(200, { ok: true })
  const start = /^\/start(?:\s+(\S+))?$/.exec(m.text.trim())
  if (!start) return reply(200, { ok: true })
  const code = start[1] ?? ''
  const v = CODE.test(code) ? await store(env).get(`signin:${code}`) : null
  const user = { id: from.id, username: typeof from.username === 'string' && TG_USER.test(from.username) ? from.username : null }
  let answer
  if (v == null) {
    answer = 'This bot signs you in to OneOS reports. In OneOS: Send to the OneOS team → Sign in with Telegram.'
  } else if (JSON.parse(v).id) {
    answer = 'This sign-in was already used. Start it again in OneOS.'
  } else {
    await store(env).put(`signin:${code}`, JSON.stringify(user), { expirationTtl: SIGNIN_TTL })
    answer = null
  }
  ctx.waitUntil((async () => {
    if (answer == null) {
      const member = await isMember(env, user.id).catch(() => null)
      answer = member === false
        ? `Signed in to OneOS. Reports are for members of the OneOS group: join ${GROUP_LINK}, then go back to OneOS and send your report.`
        : 'Signed in to OneOS ✅ Go back to the app to send your report.'
    }
    await tg(env, 'sendMessage', { chat_id: from.id, text: answer, disable_web_page_preview: true })
  })().catch(() => {}))
  return reply(200, { ok: true })
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
  const user = await uploader(req, env)
  // The account's checks before anything is stored (11-18: parts were taken from accounts whose report the daily
  // limit then refused, every retry another KV write; 1,148 writes in an hour as queued logs went out).
  if (user) {
    if ((await store(env).get(`banned:${user.id}`)) === '1') throw new Refused(403, 'this account was banned from the OneOS group for flooding reports')
    const day = Number((await store(env).get(`day:${user.id}:${new Date().toISOString().slice(0, 10)}`)) ?? 0)
    if (day >= DAILY_MAX) throw new Refused(429, `${DAILY_MAX} reports a day is the most from one account, send more tomorrow`)
  }
  await budget(env, Number(req.headers.get('content-length') ?? 0))
  const id = url.searchParams.get('id') ?? ''
  if (!ID.test(id)) throw new Refused(400, 'bad id')
  const n = int(url.searchParams.get('n'), 1, PARTS_MAX)
  const i = int(url.searchParams.get('i'), 0, n - 1)
  const length = int(req.headers.get('content-length'), 1, PART_MAX)
  // Streamed into KV again (11-18): copying a part into D1's 1 MiB rows went past the Workers CPU limit for a log of
  // a few MB ("Worker exceeded CPU time limit", every full log refused). One KV write per part; the records stay in D1.
  // Two days, not the records' 30: the puller takes a report within minutes, and parts whose report never came
  // (refused, or the app gave up) filled KV's 1 GB (11-18: 199 such parts, 2.1 GB).
  await store(env).put(`part:${id}:${i}`, req.body, { expirationTtl: 2 * 24 * 3600, metadata: { n, bytes: length } })
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
  // 0.4.32: the app that ran the session, which can be older than the one sending
  // it. Checked like app.version, so the record says which build a result is for.
  if (r.sessionApp != null) {
    const sa = r.sessionApp
    if (!TOKEN.test(sa.version ?? '')) fail('sessionApp')
    if (sa.versionCode != null && !Number.isInteger(sa.versionCode)) fail('sessionApp')
    if (sa.date != null && !/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(sa.date)) fail('sessionApp')
  }
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
    sessionApp: r.sessionApp
      ? { version: r.sessionApp.version, versionCode: r.sessionApp.versionCode ?? null, date: r.sessionApp.date ?? null }
      : null,
    checklist: r.checklist ?? null, note: r.note ?? null, contact: r.contact ?? null, logs: r.logs ?? null,
  }
}

async function report(req, env, ctx) {
  const user = await uploader(req, env)
  const length = int(req.headers.get('content-length'), 2, RECORD_MAX)
  const text = await req.text()
  if (text.length > length) throw new Refused(400, 'bad length')
  let parsed
  try { parsed = JSON.parse(text) } catch { throw new Refused(400, 'not JSON') }
  // Who sent it comes from the pass, never from the record.
  const r = { ...check(parsed), tg: user }
  let held = false
  let dayKey = null
  let dayCount = 0
  if (user) {
    await perUser(env, user)
    dayKey = `day:${user.id}:${new Date().toISOString().slice(0, 10)}`
    dayCount = Number((await store(env).get(dayKey)) ?? 0)
    if (dayCount >= DAILY_MAX) throw new Refused(429, `${DAILY_MAX} reports a day is the most from one account, send more tomorrow`)
    let seen = Number(await store(env).get(`seen:${user.id}`))
    if (!seen) { seen = Date.now(); await store(env).put(`seen:${user.id}`, String(seen)) }
    held = Date.now() - seen < HOLD_SECONDS * 1000
  }
  // Every part must be there before the record is: the app sends them again otherwise.
  const missing = []
  for (let i = 0; i < (r.logs?.parts ?? 0); i++) {
    const v = await store(env).get(`part:${r.reportId}:${i}`, { type: 'stream' })
    if (v == null) missing.push(i)
    else await v.cancel()
  }
  if (missing.length) return reply(409, { error: 'missing parts', missing })
  const receivedAt = new Date().toISOString()
  await store(env).put(`report:${receivedAt}:${r.reportId}`, JSON.stringify({ ...r, receivedAt, ...(held ? { held: true } : {}) }), { expirationTtl: TTL })
  if (dayKey) await store(env).put(dayKey, String(dayCount + 1), { expirationTtl: 2 * 24 * 3600 })
  if (!held && env.TG_TOKEN && env.TG_CHAT) ctx.waitUntil(ping(env, r).catch(() => {}))
  return reply(200, { ok: true, reportId: r.reportId })
}

// The daily usage check-in (0.5.14; owner: real user numbers for the Statistics topic). On by
// default in the app, off with Settings > Anonymous usage count. A random install id (not tied to
// the phone or an account), the phone model and OneOS profile, the app version, the systems set up
// and how many switches since the last check-in. One Analytics Engine data point (dataset
// oneos_usage), nothing in KV; the sender's address is used for the rate limit only, never stored.
const INSTALL = /^[0-9a-f]{32}$/
const IMAGE = /^[a-z0-9][a-z0-9._-]{0,47}$/

async function hello(req, env) {
  // The anonymous daily count needs the app's key only, not a sign-in (11-18: with REQUIRE_MEMBER every app that
  // had not signed in got 403 here, and the usage numbers counted signed-in members only).
  appKey(req, env)
  await limited(req, env)
  const length = int(req.headers.get('content-length'), 2, 2048)
  const text = await req.text()
  if (text.length > length) throw new Refused(400, 'bad length')
  let h
  try { h = JSON.parse(text) } catch { throw new Refused(400, 'not JSON') }
  if (!h || typeof h !== 'object' || h.schema !== 'oneos.hello/1') throw new Refused(400, 'bad schema')
  if (!INSTALL.test(h.install ?? '')) throw new Refused(400, 'bad install id')
  const code = int(h.versionCode, 1, 100000)
  if (!MODEL.test(h.model ?? '')) throw new Refused(400, 'bad model')
  if (h.profile != null && !TOKEN.test(h.profile)) throw new Refused(400, 'bad profile')
  const systems = Array.isArray(h.systems) ? h.systems : []
  if (systems.length > 8 || !systems.every((x) => typeof x === 'string' && IMAGE.test(x))) throw new Refused(400, 'bad systems')
  const switches = int(h.switches ?? 0, 0, 500)
  if (env.USAGE) {
    env.USAGE.writeDataPoint({
      indexes: [h.install],
      blobs: [h.model, h.profile ?? '', String(code), systems.join(',')],
      doubles: [code, switches],
    })
  }
  return reply(200, { ok: true })
}

// A Telegram username: 5-32 characters, starts with a letter. Anything else the
// tester may have typed (an e-mail, a phone number, a name) is not put in the
// group; the record keeps it for the team (reports/pull.py).
const TG_USER = /^@?([A-Za-z][A-Za-z0-9_]{4,31})$/

function fromLine(contact, user) {
  if (user?.username) return `From: @${user.username}`
  if (user) return 'From: a group member without a username (id in the record)'
  const c = (contact ?? '').trim()
  if (!c) return 'From: no contact given'
  const m = TG_USER.exec(c)
  if (m) return `From: @${m[1]}`
  if (/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(c)) return 'From: an e-mail address, in the record'
  if (/^[+0-9][0-9 ()-]{5,}$/.test(c)) return 'From: a phone number, in the record'
  return 'From: a contact in the record'
}

function pingText(r) {
  const lines = [`📋 New report ${r.reportId}`]
  lines.push(fromLine(r.contact, r.tg))
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
  const r = await store(env).list({ prefix, cursor, limit: 100 })
  return reply(200, { keys: r.keys.map((k) => ({ name: k.name, metadata: k.metadata ?? null })), cursor: r.list_complete ? null : r.cursor })
}

async function get(req, env, url) {
  admin(req, env)
  const key = url.searchParams.get('key') ?? ''
  if (!KEY.test(key)) throw new Refused(400, 'bad key name')
  const v = await store(env).get(key, { type: 'stream' })
  if (v == null) return reply(404, { error: 'not found' })
  return new Response(v, { headers: { 'content-type': key.startsWith('part:') ? 'application/octet-stream' : 'application/json' } })
}

async function del(req, env, url) {
  admin(req, env)
  const key = url.searchParams.get('key') ?? ''
  if (!KEY.test(key)) throw new Refused(400, 'bad key name')
  await store(env).delete(key)
  return reply(200, { ok: true })
}

export { pingText, check, budget, sweep }

// --- Join requests (11-18, owner: the group asks admins to approve joins; flood accounts joined to send fake
// reports). Each request goes to the group's creator in a private message with what tells a person from a
// throwaway account, and Approve/Decline buttons only the creator can use. Another admin's approval shows up
// there (chat_member, via_join_request); a decline sends nothing, so a later tap says it was already handled.

const JOINREQ_TTL = 7 * 24 * 3600

async function creator(env) {
  const cached = await store(env).get('admin:creator')
  if (cached) return Number(cached)
  const r = await tg(env, 'getChatAdministrators', { chat_id: env.TG_CHAT })
  const c = (r?.result ?? []).find((a) => a.status === 'creator')?.user?.id
  if (c) await store(env).put('admin:creator', String(c), { expirationTtl: 24 * 3600 })
  return c ?? null
}

// A Telegram id's rough age: ids are handed out in order (rough edges, good enough to flag a brand-new account).
function idAge(id) {
  if (id < 1e9) return ['before 2020', 0]
  if (id < 5e9) return ['2020-2022', 0]
  if (id < 6e9) return ['2022-2023', 0]
  if (id < 7e9) return ['2023-2024', 1]
  if (id < 8e9) return ['2024-2025', 1]
  return ['2025-2026, very new', 2]
}

// gducufu, pipetkqmeow, fghe9a: short lowercase strings without a word in them.
function randomName(u) {
  if (!u) return false
  const s = u.toLowerCase()
  if (!/^[a-z0-9]{5,12}$/.test(s)) return false
  const vowels = (s.match(/[aeiou]/g) ?? []).length
  return /[bcdfghjklmnpqrstvwxz]{4}/.test(s) || /\d/.test(s) && /[a-z]/.test(s) || vowels / s.length < 0.25
}

function esc(t) { return String(t ?? '').replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c])) }

async function screening(env, u) {
  const chat = Number(env.TG_CHAT)
  if (u.chat_join_request) {
    const r = u.chat_join_request
    if (Number(r.chat?.id) !== chat || !r.from || !Number.isSafeInteger(r.from.id)) return
    const owner = await creator(env)
    if (!owner) return
    const f = r.from
    const [age, ageScore] = idAge(f.id)
    let photos = null
    try { photos = (await tg(env, 'getUserProfilePhotos', { user_id: f.id, limit: 1 }))?.result?.total_count ?? null } catch {}
    const signedIn = (await store(env).get(`seen:${f.id}`)) != null
    const banned = (await store(env).get(`banned:${f.id}`)) === '1'
    const why = []
    let score = ageScore
    if (ageScore === 2) why.push('account created very recently')
    if (photos === 0) { score += 2; why.push('no profile photo') }
    if (!f.username) { score += 1; why.push('no username') } else if (randomName(f.username)) { score += 1; why.push('random-looking username') }
    if (f.is_premium) { score -= 2 }
    if (r.bio) score -= 1
    if (signedIn) score -= 3
    if (banned) { score += 5; why.unshift('BANNED before for flooding reports') }
    const verdict = banned || score >= 4 ? '🔴 likely throwaway / bot' : score >= 2 ? '🟡 unsure' : '🟢 looks real'
    const lines = [
      `🙋 <b>Join request</b> for OneOS`,
      `${esc([f.first_name, f.last_name].filter(Boolean).join(' '))}${f.username ? ` @${esc(f.username)}` : ''} (id ${f.id})`,
      `Account: about ${age}${f.is_premium ? ' · Premium' : ''}${f.language_code ? ` · ${esc(f.language_code)}` : ''}`,
      `Profile photo: ${photos == null ? 'unknown' : photos > 0 ? 'yes' : 'no'}`,
      r.bio ? `Bio: ${esc(r.bio).slice(0, 200)}` : 'Bio: none',
      `OneOS reports: ${banned ? 'banned for flooding' : signedIn ? 'signed in before' : 'never signed in'}`,
      `<b>${verdict}</b>${why.length ? `: ${why.join(', ')}` : ''}`,
    ]
    const text = lines.join('\n')
    const sent = await tg(env, 'sendMessage', {
      chat_id: owner, text, parse_mode: 'HTML', disable_web_page_preview: true,
      reply_markup: { inline_keyboard: [[{ text: '✅ Approve', callback_data: `jr:a:${f.id}` }, { text: '❌ Decline', callback_data: `jr:d:${f.id}` }]] },
    })
    const mid = sent?.result?.message_id
    if (mid) await store(env).put(`joinreq:${f.id}`, JSON.stringify({ chat: owner, msg: mid, text }), { expirationTtl: JOINREQ_TTL })
    return
  }
  if (u.chat_member) {
    const c = u.chat_member
    const who = c.new_chat_member?.user
    if (Number(c.chat?.id) !== chat || !who || c.new_chat_member.status !== 'member' || !c.via_join_request) return
    const v = await store(env).get(`joinreq:${who.id}`)
    if (!v) return
    const j = JSON.parse(v)
    const by = c.from?.username ? `@${esc(c.from.username)}` : 'another admin'
    await tg(env, 'editMessageText', { chat_id: j.chat, message_id: j.msg, text: `${j.text}\n\n✅ Approved by ${by}`, parse_mode: 'HTML' })
    await store(env).delete(`joinreq:${who.id}`)
    return
  }
  if (u.callback_query) {
    const q = u.callback_query
    const m = /^jr:([ad]):(\d{1,20})$/.exec(q.data ?? '')
    if (!m) return
    const owner = await creator(env)
    if (!owner || q.from?.id !== owner) {
      await tg(env, 'answerCallbackQuery', { callback_query_id: q.id, text: 'Only the group owner can use these buttons.' })
      return
    }
    const uid = Number(m[2])
    const r = await tg(env, m[1] === 'a' ? 'approveChatJoinRequest' : 'declineChatJoinRequest', { chat_id: env.TG_CHAT, user_id: uid })
    const v = await store(env).get(`joinreq:${uid}`)
    const base = v ? JSON.parse(v).text : (q.message?.text ?? '')
    const note = r?.ok ? (m[1] === 'a' ? '✅ Approved by you' : '❌ Declined by you') : 'ℹ️ Already handled by another admin (or the request was withdrawn)'
    if (q.message) await tg(env, 'editMessageText', { chat_id: q.message.chat.id, message_id: q.message.message_id, text: `${base}\n\n${note}`, parse_mode: v ? 'HTML' : undefined })
    await tg(env, 'answerCallbackQuery', { callback_query_id: q.id, text: note })
    if (v) await store(env).delete(`joinreq:${uid}`)
  }
}

// --- Budget (11-18, owner: "make it robust"): the service stays under Cloudflare's free KV limits whatever the apps
// do. Log parts are the only KV writes: at most PARTS_PER_DAY a day (KV takes 1,000 writes) and PARTS_BYTES stored
// over the two days a part lives (KV holds 1 GB). Past either, an upload is told to come back later (503; the app
// keeps the report and sends it again). The counters are in D1 (budget:<day>). The owner hears it once a day.
const PARTS_PER_DAY = 700
const PARTS_BYTES = 800 * 1024 * 1024

const today = (d = 0) => new Date(Date.now() - d * 86400000).toISOString().slice(0, 10)

async function budget(env, bytes) {
  if (!env.DB) return
  const s = store(env)
  const t = JSON.parse((await s.get(`budget:${today()}`)) ?? '{"n":0,"b":0}')
  const y = JSON.parse((await s.get(`budget:${today(1)}`)) ?? '{"n":0,"b":0}')
  if (t.n >= PARTS_PER_DAY || t.b + y.b + bytes > PARTS_BYTES) {
    await warnOnce(env, `⚠️ OneOS reports at today's limit (${t.n} log parts, ${Math.round((t.b + y.b) / 1048576)} MB stored): new uploads wait until tomorrow (KV's free limits). Nothing to do unless it repeats.`)
    throw new Refused(503, 'the report service is busy, OneOS sends it again later')
  }
  await s.put(`budget:${today()}`, JSON.stringify({ n: t.n + 1, b: t.b + bytes }), { expirationTtl: 3 * 86400 })
}

async function warnOnce(env, text) {
  const k = `warned:${today()}`
  if ((await store(env).get(k)) != null) return
  await store(env).put(k, '1', { expirationTtl: 2 * 86400 })
  const owner = await creator(env).catch(() => null)
  if (owner) await tg(env, 'sendMessage', { chat_id: owner, text }).catch(() => {})
}

// Hourly (wrangler.toml crons): parts left more than 6 hours (their report never came) are deleted, 100 at most
// a run; a part lives 2 days, so its upload time is its expiry minus that.
async function sweep(env) {
  const kv = env.REPORTS
  if (!kv || !env.DB) return
  const cutoff = Date.now() / 1000 - 6 * 3600
  const r = await kv.list({ prefix: 'part:', limit: 1000 })
  let gone = 0
  for (const k of r.keys) {
    if (gone >= 100) break
    if (k.expiration && k.expiration - 2 * 86400 < cutoff) { await kv.delete(k.name); gone++ }
  }
}
