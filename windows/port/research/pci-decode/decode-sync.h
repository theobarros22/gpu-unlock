/* GPL-2.0-only. Research-only decode-cache transaction; no shipped build uses it. */
#pragma once
#include <Uefi.h>

#define GU_DS_MAX_PARENTS 16U
#define GU_DS_FOLLOWUPS 4U
#define GU_DS_IO 0x100ULL
#define GU_DS_MEMORY 0x200ULL
#define GU_DS_MASTER 0x400ULL

typedef struct {
  UINTN Handle, Interface, Segment, Bus, Device, Function;
  UINT32 Config[64];
  UINT64 Attributes, Supported;
} GU_DS_DEVICE;

/* Parents are the caller-verified immediate ancestry, ordered root to leaf.
 * Complete must be set only after every location/config/attribute query succeeds.
 * Tokens identify handles/interfaces, not ownership or authenticated provenance. */
typedef struct {
  BOOLEAN Complete;
  UINTN ParentCount;
  GU_DS_DEVICE Gpu, Parents[GU_DS_MAX_PARENTS];
} GU_DS_SNAPSHOT;

typedef struct {
  VOID *Context;
  EFI_STATUS (*Read)(VOID *Context, GU_DS_SNAPSHOT *Snapshot);
  /* The only write capability. Its adapter must target the verified GPU and call
   * PciIo Attributes(Disable, IO), never enable IO, memory or bus mastering. */
  EFI_STATUS (*DisableIo)(VOID *Context);
  /* TRUE means the event was durably recorded; a failed log forbids further work. */
  BOOLEAN (*Log)(VOID *Context, const char *Event);
} GU_DS_OPS;

typedef enum {
  GU_DS_INVALID, GU_DS_REUSED, GU_DS_READ_FAILED, GU_DS_LOG_FAILED,
  GU_DS_DRIFT, GU_DS_DISABLE_FAILED, GU_DS_ALREADY_CONSISTENT, GU_DS_FIXED
} GU_DS_RESULT;

/* Caller owns one zero-initialized object per authorized transaction. Never reset
 * it to retry. This core cannot police creation of a different caller object. */
typedef struct {
  BOOLEAN Started, Attempted, PostObserved;
  EFI_STATUS DisableStatus, ObservationStatus;
  GU_DS_RESULT Result;
} GU_DS_TRANSACTION;

GU_DS_RESULT GuDecodeSync(GU_DS_TRANSACTION *Transaction, const GU_DS_OPS *Ops,
                         const GU_DS_SNAPSHOT *Expected);

/* Research adapter helpers; they validate supplied values, not their provenance. */
BOOLEAN GuDecodeSnapshotValid(const GU_DS_SNAPSHOT *Snapshot);
BOOLEAN GuDecodeSnapshotMatches(const GU_DS_SNAPSHOT *Observed,const GU_DS_SNAPSHOT *Expected,BOOLEAN IoCleared);
