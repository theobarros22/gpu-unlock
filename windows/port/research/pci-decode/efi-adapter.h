/* GPL-2.0-only. Research library only; no EFI entry point or shipped build. */
#pragma once
#include "decode-sync.h"
#include <Protocol/PciIo.h>
#include <Protocol/DevicePath.h>

#define GU_DS_EFI_MAX_PATH 112U
#define GU_DS_EFI_MAX_PARENTS 15U
typedef struct {
  EFI_HANDLE Handle;
  EFI_PCI_IO_PROTOCOL *Io;
  UINTN PathBytes;
  UINT8 Path[GU_DS_EFI_MAX_PATH];
} GU_DS_EFI_BINDING;
typedef struct {
  GU_DS_EFI_BINDING Pin;
  EFI_PCI_IO_PROTOCOL_GET_LOCATION Location;
  EFI_PCI_IO_PROTOCOL_CONFIG Read;
  EFI_PCI_IO_PROTOCOL_ATTRIBUTES Attributes;
} GU_DS_EFI_DEVICE;
/* One zero-initialized context. Treat initialized fields as private/immutable.
 * The caller must establish ownership and authorize any future physical use.
 * A matching path and repeated reads do not establish either fact. */
typedef struct {
  BOOLEAN InitUsed,Ready,RunUsed,Busy,WriteSpent;
  EFI_BOOT_SERVICES *Boot;
  EFI_HANDLE_PROTOCOL HandleProtocol;
  EFI_LOCATE_DEVICE_PATH LocateDevicePath;
  GU_DS_EFI_DEVICE Devices[1+GU_DS_EFI_MAX_PARENTS];
  GU_DS_SNAPSHOT Expected;
  BOOLEAN (*DurableLog)(VOID *Context,const char *Event);
  VOID *LogContext;
} GU_DS_EFI_CONTEXT;

/* Bindings[0] is GPU; following bindings are its immediate root-to-leaf parents.
 * Init is pure validation/copying and calls no firmware or log callback. */
EFI_STATUS GuDsEfiInitialize(GU_DS_EFI_CONTEXT *Context,EFI_BOOT_SERVICES *Boot,
  const GU_DS_EFI_BINDING *Bindings,UINTN Count,const GU_DS_SNAPSHOT *Expected,
  BOOLEAN (*DurableLog)(VOID *,const char *),VOID *LogContext);
GU_DS_RESULT GuDsEfiRun(GU_DS_EFI_CONTEXT *Context,GU_DS_TRANSACTION *Transaction);
