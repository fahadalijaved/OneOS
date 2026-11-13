/* Authored closed-session transport; no host authority or guest admission. */
#ifndef ONEOS_RETAINED_ROOT_SESSION_PROTOCOL_H
#define ONEOS_RETAINED_ROOT_SESSION_PROTOCOL_H
#define ORS_FRAME_BYTES 64U
#define ORS_PAYLOAD_OFFSET 16U
#define ORS_VERSION 1U
#define ORS_MAGIC_0 'O'
#define ORS_MAGIC_1 'R'
#define ORS_MAGIC_2 'S'
#define ORS_MAGIC_3 'C'
/* Big-endian: magic[4], version:u16, kind:u16, sequence:u32, status:u32,
 * payload[48]. Unused payload bytes must be zero. No struct ABI is on wire. */
enum ors_kind {
    ORS_INIT=1, ORS_OFFER=2, ORS_IDENTITY=3, ORS_PING=4,
    ORS_PONG=5, ORS_CLOSE=6, ORS_CLOSED=7, ORS_ERROR=255
};
enum ors_status {
    ORS_REQUEST=0, ORS_ADMISSION_CLOSED=1, ORS_LOCAL_CLOSED=2, ORS_REFUSED=3
};
/* INIT(seq0/request): caller pid:u32, uid:u32. These are transport association,
 * not authority. Native accept must match actual SO_PEERCRED to them.
 * OFFER(seq0/closed): native pid:u32, abstract address NUL-padded[44].
 * IDENTITY(seq0/closed): native pid:u32, zero padding; SCM_RIGHTS exactly one
 * actual self pidfd. No raw descriptor number is transmitted as an identity.
 * PING/PONG and CLOSE/CLOSED: zero payload, increasing nonzero request sequence.
 * CLOSED is a local-control acknowledgement, never a native-exit proof.
 * No JOIN/START/VERIFY operation exists in this closed-session protocol. */
#endif
