/* First-party closed host-control v2; no guest/security authority operation. */
#ifndef ONEOS_RETAINED_ROOT_HANDOFF_H
#define ONEOS_RETAINED_ROOT_HANDOFF_H
#define ORH_FRAME_BYTES 64U
#define ORH_PAYLOAD_OFFSET 16U
#define ORH_VERSION 2U
#define ORH_MAGIC_0 'O'
#define ORH_MAGIC_1 'R'
#define ORH_MAGIC_2 'S'
#define ORH_MAGIC_3 'H'
/* Big-endian magic/version:u16/kind:u16/sequence:u32/status:u32/payload[48]. */
enum orh_kind {
    ORH_INIT=1, ORH_OFFER=2, ORH_IDENTITY=3, ORH_PING=4,
    ORH_PONG=5, ORH_CLOSE=6, ORH_CLOSED=7, ORH_COMMIT=8, ORH_COMMITTED=9
};
enum orh_status {
    ORH_REQUEST=0, ORH_ADMISSION_CLOSED=1, ORH_LOCAL_CLOSED=2, ORH_REFUSED=3
};
/* INIT0/request: actual Binder-derived host pid:u32 and uid:u32=1000; zero tail.
 * OFFER0/closed: native pid:u32 and oneos.orh.+32lowerhex[42], two zero bytes.
 * IDENTITY0/closed: native pid:u32, zero tail; exactly one actual self-pidfd.
 * Host alone connects; COMMIT1/request has zero payload. Irrevocable native
 * adoption precedes COMMITTED1/closed. PING/PONG and CLOSE/CLOSED start at2.
 * Incoming ancillary is refused/adopted for cleanup. CLOSED is local cutoff,
 * not native exit, inherited-resource drain, host authority or guest readiness. */
#endif
