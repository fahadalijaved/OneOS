package com.fahadali.oneos.core.root;

import android.os.Parcel;

/** Primitive evidence reply for the private, read-only Stop status transaction. */
public final class RetainedStopStatus {
    public static final int TRANSACTION = 6, VERSION = 1;
    private static final int PAYLOAD_BYTES = 56;

    public final int status;
    public final Role role;

    private RetainedStopStatus(int status, Role role) {
        if (!RetainedViewAppProtocol.isStatus(status)) {
            throw new IllegalArgumentException("Invalid Stop evidence status");
        }
        if (role != null && status != RetainedViewAppProtocol.STATUS_PARTIAL
                && status != RetainedViewAppProtocol.STATUS_CLOSING
                && status != RetainedViewAppProtocol.STATUS_CLEANUP_UNCONFIRMED
                && status != RetainedViewAppProtocol.STATUS_LOCAL_TERMINAL
                && status != RetainedViewAppProtocol.STATUS_LOCAL_CLEANUP_OBSERVED) {
            throw new IllegalArgumentException("Stop role is unavailable for this status");
        }
        this.status = status;
        this.role = role;
    }

    public static RetainedStopStatus withoutRole(int status) {
        return new RetainedStopStatus(status, null);
    }

    public static RetainedStopStatus withRole(int status, Role role) {
        if (role == null) throw new IllegalArgumentException("Stop role required");
        return new RetainedStopStatus(status, role);
    }

    /** Read the payload after the caller reads the Binder exception header. */
    public static RetainedStopStatus read(Parcel source) {
        if (source.dataAvail() != PAYLOAD_BYTES || source.readInt() != VERSION) {
            throw new IllegalArgumentException("Invalid Stop evidence reply size or version");
        }
        int status = source.readInt();
        long prepareSequence = source.readLong();
        int controllerPid = source.readInt();
        long controllerStartTicks = source.readLong();
        int childPid = source.readInt();
        long childStartTicks = source.readLong();
        long childMountNamespaceInode = source.readLong();
        int appPid = source.readInt();
        int systemServerPid = source.readInt();
        source.enforceNoDataAvail();
        if (prepareSequence == 0 && controllerPid == 0 && controllerStartTicks == 0
                && childPid == 0 && childStartTicks == 0 && childMountNamespaceInode == 0
                && appPid == 0 && systemServerPid == 0) {
            return withoutRole(status);
        }
        return withRole(status, new Role(prepareSequence, controllerPid, controllerStartTicks, childPid,
                childStartTicks, childMountNamespaceInode, appPid, systemServerPid));
    }

    /** Write the payload after the caller writes the Binder exception header. */
    public void write(Parcel reply) {
        reply.writeInt(VERSION);
        reply.writeInt(status);
        reply.writeLong(role == null ? 0 : role.prepareSequence);
        reply.writeInt(role == null ? 0 : role.controllerPid);
        reply.writeLong(role == null ? 0 : role.controllerStartTicks);
        reply.writeInt(role == null ? 0 : role.childPid);
        reply.writeLong(role == null ? 0 : role.childStartTicks);
        reply.writeLong(role == null ? 0 : role.childMountNamespaceInode);
        reply.writeInt(role == null ? 0 : role.appPid);
        reply.writeInt(role == null ? 0 : role.systemServerPid);
    }

    /** Immutable process observations from the same retained Prepare occurrence. */
    public static final class Role {
        public final long prepareSequence;
        public final int controllerPid;
        public final long controllerStartTicks;
        public final int childPid;
        public final long childStartTicks;
        public final long childMountNamespaceInode;
        public final int appPid;
        public final int systemServerPid;

        public Role(long prepareSequence, int controllerPid, long controllerStartTicks, int childPid,
                long childStartTicks, long childMountNamespaceInode, int appPid, int systemServerPid) {
            if (prepareSequence < 2 || prepareSequence > 0xffffffffL
                    || controllerStartTicks <= 0 || childStartTicks <= 0 || childMountNamespaceInode == 0
                    || controllerPid <= 0 || childPid <= 0 || appPid <= 0 || systemServerPid <= 0
                    || controllerPid == childPid || controllerPid == appPid || controllerPid == systemServerPid
                    || childPid == appPid || childPid == systemServerPid || appPid == systemServerPid) {
                throw new IllegalArgumentException("Invalid Stop role identity");
            }
            this.prepareSequence = prepareSequence;
            this.controllerPid = controllerPid;
            this.controllerStartTicks = controllerStartTicks;
            this.childPid = childPid;
            this.childStartTicks = childStartTicks;
            this.childMountNamespaceInode = childMountNamespaceInode;
            this.appPid = appPid;
            this.systemServerPid = systemServerPid;
        }

        @Override public boolean equals(Object value) {
            if (!(value instanceof Role)) return false;
            Role other = (Role) value;
            return prepareSequence == other.prepareSequence && controllerPid == other.controllerPid
                    && controllerStartTicks == other.controllerStartTicks && childPid == other.childPid
                    && childStartTicks == other.childStartTicks && childMountNamespaceInode == other.childMountNamespaceInode
                    && appPid == other.appPid && systemServerPid == other.systemServerPid;
        }

        @Override public int hashCode() {
            int result = Long.hashCode(prepareSequence);
            result = 31 * result + controllerPid;
            result = 31 * result + Long.hashCode(controllerStartTicks);
            result = 31 * result + childPid;
            result = 31 * result + Long.hashCode(childStartTicks);
            result = 31 * result + Long.hashCode(childMountNamespaceInode);
            result = 31 * result + appPid;
            return 31 * result + systemServerPid;
        }
    }
}
