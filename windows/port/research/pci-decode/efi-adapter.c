/* GPL-2.0-only. Real UEFI protocol adapter exercised only through host mocks.
 * Deliberately not wired into probes, boot images, staging or LOCAL admission. */
#include "efi-adapter.h"
#include "../../internal-boot/unlock/gpu-path.h"

static EFI_GUID PciGuid=EFI_PCI_IO_PROTOCOL_GUID,PathGuid=EFI_DEVICE_PATH_PROTOCOL_GUID;
static BOOLEAN Bytes(const VOID *a,const VOID *b,UINTN n) {
  const UINT8 *x=a,*y=b;for(UINTN i=0;i<n;i++)if(x[i]!=y[i])return FALSE;return TRUE;
}
static BOOLEAN Overlap(const VOID *a,UINTN an,const VOID *b,UINTN bn) {
  UINTN x=(UINTN)a,y=(UINTN)b;return x<=y?y-x<an:x-y<bn;
}
static const GU_DS_DEVICE *ExpectedDevice(const GU_DS_EFI_CONTEXT *c,UINTN i) {
  return i?&c->Expected.Parents[i-1]:&c->Expected.Gpu;
}
static BOOLEAN Caps(const GU_DS_EFI_CONTEXT *c,const GU_DS_EFI_DEVICE *d) {
  return c->Boot->HandleProtocol==c->HandleProtocol && c->Boot->LocateDevicePath==c->LocateDevicePath &&
    d->Pin.Io->GetLocation==d->Location && d->Pin.Io->Pci.Read==d->Read && d->Pin.Io->Attributes==d->Attributes;
}
static BOOLEAN AllCaps(const GU_DS_EFI_CONTEXT *c) {
  for(UINTN i=0;i<1+c->Expected.ParentCount;i++)if(!Caps(c,&c->Devices[i]))return FALSE;
  return TRUE;
}
static BOOLEAN Controller(const GU_DS_EFI_BINDING *gpu,UINTN parents) {
  static const UINT8 end[]={0x7f,0xff,4,0};
  UINT8 display[GU_GPU_DISPLAY_PATH_MAX_BYTES];
  if(gpu->PathBytes<4 || gpu->PathBytes>GU_DS_EFI_MAX_PATH ||
     !Bytes(gpu->Path+gpu->PathBytes-4,end,4))return FALSE;
  UINTN body=gpu->PathBytes-4,controller=0,total=0;
  if(body+12>sizeof(display))return FALSE;
  for(UINTN i=0;i<body;i++)display[i]=gpu->Path[i];
  for(UINTN i=0;i<12;i++)display[body+i]=0;
  display[body]=2;display[body+1]=3;display[body+2]=8;
  for(UINTN i=0;i<4;i++)display[body+8+i]=end[i];
  return GuDecodeGpuDisplayPath(display,body+12,&controller,&total) && controller==body &&
    body==12+6*(parents+1) && total==body+12;
}
EFI_STATUS GuDsEfiInitialize(GU_DS_EFI_CONTEXT *c,EFI_BOOT_SERVICES *boot,
  const GU_DS_EFI_BINDING *bindings,UINTN count,const GU_DS_SNAPSHOT *expected,
  BOOLEAN (*log)(VOID *,const char *),VOID *logContext) {
  if(!c)return EFI_INVALID_PARAMETER;
  if(c->InitUsed!=FALSE)return EFI_ALREADY_STARTED;
  /* Never reset a used context, including when Init is called from a callback. */
  c->InitUsed=TRUE;c->Ready=FALSE;
  if(!boot || !bindings || !expected || !log || !count || count>1+GU_DS_EFI_MAX_PARENTS ||
     Overlap(c,sizeof(*c),bindings,sizeof(*bindings)*count) || Overlap(c,sizeof(*c),expected,sizeof(*expected)) ||
     !boot->HandleProtocol || !boot->LocateDevicePath || !GuDecodeSnapshotValid(expected) ||
     expected->ParentCount+1!=count || !Controller(&bindings[0],expected->ParentCount))return EFI_INVALID_PARAMETER;
  c->Boot=boot;c->HandleProtocol=boot->HandleProtocol;c->LocateDevicePath=boot->LocateDevicePath;
  c->Expected=*expected;c->DurableLog=log;c->LogContext=logContext;
  for(UINTN i=0;i<count;i++) {
    GU_DS_EFI_DEVICE *d=&c->Devices[i];const GU_DS_DEVICE *e=ExpectedDevice(c,i);
    const GU_DS_EFI_BINDING *pin=&bindings[i];
    if((UINTN)pin->Handle!=e->Handle || (UINTN)pin->Io!=e->Interface || !pin->Io ||
       !pin->Io->GetLocation || !pin->Io->Pci.Read || !pin->Io->Attributes)return EFI_INVALID_PARAMETER;
    if(i) {
      UINTN prefix=12+6*i;
      if(pin->PathBytes!=prefix+4 || !Bytes(pin->Path,bindings[0].Path,prefix) ||
         !Bytes(pin->Path+prefix,bindings[0].Path+bindings[0].PathBytes-4,4) ||
         e->Function!=pin->Path[prefix-2] || e->Device!=pin->Path[prefix-1])return EFI_INVALID_PARAMETER;
    }
    d->Pin=*pin;d->Location=pin->Io->GetLocation;d->Read=pin->Io->Pci.Read;d->Attributes=pin->Io->Attributes;
  }
  c->Ready=TRUE;return EFI_SUCCESS;
}
static EFI_STATUS Resolve(GU_DS_EFI_CONTEXT *c,GU_DS_EFI_DEVICE *d) {
  if(!Caps(c,d))return EFI_NOT_READY;
  VOID *io=NULL,*path=NULL;
  EFI_STATUS s=c->HandleProtocol(d->Pin.Handle,&PciGuid,&io);
  if(s!=EFI_SUCCESS || io!=d->Pin.Io || !Caps(c,d))return EFI_NOT_READY;
  s=c->HandleProtocol(d->Pin.Handle,&PathGuid,&path);
  if(s!=EFI_SUCCESS || !path || !Bytes(path,d->Pin.Path,d->Pin.PathBytes) || !Caps(c,d))return EFI_NOT_READY;
  UINT8 copy[GU_DS_EFI_MAX_PATH];
  for(UINTN i=0;i<d->Pin.PathBytes;i++)copy[i]=d->Pin.Path[i];
  EFI_DEVICE_PATH_PROTOCOL *rest=(VOID *)copy;EFI_HANDLE h=NULL;
  s=c->LocateDevicePath(&PciGuid,&rest,&h);
  if(s!=EFI_SUCCESS || h!=d->Pin.Handle || (UINTN)rest!=(UINTN)copy+d->Pin.PathBytes-4 ||
     !Bytes(copy,d->Pin.Path,d->Pin.PathBytes) || !Caps(c,d))return EFI_NOT_READY;
  return EFI_SUCCESS;
}
static EFI_STATUS ReadOne(GU_DS_EFI_CONTEXT *c,UINTN index,UINT32 sentinel,GU_DS_DEVICE *out) {
  GU_DS_EFI_DEVICE *d=&c->Devices[index];const GU_DS_DEVICE *pin=ExpectedDevice(c,index);
  if(Resolve(c,d)!=EFI_SUCCESS)return EFI_NOT_READY;
  out->Handle=(UINTN)d->Pin.Handle;out->Interface=(UINTN)d->Pin.Io;
  out->Segment=out->Bus=out->Device=out->Function=~(UINTN)0;
  EFI_STATUS s=d->Location(d->Pin.Io,&out->Segment,&out->Bus,&out->Device,&out->Function);
  if(s!=EFI_SUCCESS || !Caps(c,d) || out->Segment!=pin->Segment || out->Bus!=pin->Bus ||
     out->Device!=pin->Device || out->Function!=pin->Function)return EFI_NOT_READY;
  for(UINTN i=0;i<64;i++)out->Config[i]=sentinel;
  s=d->Read(d->Pin.Io,EfiPciIoWidthUint32,0,64,out->Config);
  if(s!=EFI_SUCCESS || !Caps(c,d))return EFI_NOT_READY;
  for(UINTN i=0;i<64;i++)if(out->Config[i]!=pin->Config[i])return EFI_NOT_READY;
  out->Attributes=out->Supported=~0ULL;
  s=d->Attributes(d->Pin.Io,EfiPciIoAttributeOperationGet,0,&out->Attributes);
  if(s!=EFI_SUCCESS || out->Attributes==~0ULL || !Caps(c,d))return EFI_NOT_READY;
  s=d->Attributes(d->Pin.Io,EfiPciIoAttributeOperationSupported,0,&out->Supported);
  if(s!=EFI_SUCCESS || out->Supported==~0ULL || !Caps(c,d))return EFI_NOT_READY;
  return Resolve(c,d);
}
static EFI_STATUS ReadLocked(GU_DS_EFI_CONTEXT *c,GU_DS_SNAPSHOT *out) {
  GU_DS_SNAPSHOT first={0},second={0};
  first.ParentCount=second.ParentCount=c->Expected.ParentCount;
  for(UINTN pass=0;pass<2;pass++) {
    GU_DS_SNAPSHOT *s=pass?&second:&first;
    for(UINTN i=0;i<1+c->Expected.ParentCount;i++) {
      GU_DS_DEVICE *d=i?&s->Parents[i-1]:&s->Gpu;
      if(ReadOne(c,i,pass?0x5a5a5a5aU:0xa5a5a5a5U,d)!=EFI_SUCCESS)return EFI_NOT_READY;
    }
    s->Complete=TRUE;
  }
  if(!AllCaps(c) || !GuDecodeSnapshotMatches(&second,&first,FALSE))return EFI_NOT_READY;
  *out=second;return EFI_SUCCESS;
}
static EFI_STATUS AdapterRead(VOID *context,GU_DS_SNAPSHOT *out) {
  GU_DS_EFI_CONTEXT *c=context;
  if(!out || Overlap(c,sizeof(*c),out,sizeof(*out)))return EFI_INVALID_PARAMETER;
  *out=(GU_DS_SNAPSHOT){0};
  if(c->Ready!=TRUE || c->Busy!=FALSE)return EFI_NOT_READY;
  c->Busy=TRUE;EFI_STATUS s=ReadLocked(c,out);c->Busy=FALSE;return s;
}
static EFI_STATUS AdapterDisable(VOID *context) {
  GU_DS_EFI_CONTEXT *c=context;
  if(c->Ready!=TRUE || c->Busy!=FALSE || c->WriteSpent!=FALSE)return EFI_ACCESS_DENIED;
  c->Busy=TRUE;c->WriteSpent=TRUE;
  GU_DS_SNAPSHOT now={0};EFI_STATUS s=ReadLocked(c,&now);
  if(s==EFI_SUCCESS && GuDecodeSnapshotMatches(&now,&c->Expected,FALSE) && AllCaps(c)) {
    GU_DS_EFI_DEVICE *g=&c->Devices[0];
    s=g->Attributes(g->Pin.Io,EfiPciIoAttributeOperationDisable,GU_DS_IO,NULL);
  } else s=EFI_NOT_READY;
  c->Busy=FALSE;return s;
}
static BOOLEAN AdapterLog(VOID *context,const char *event) {
  GU_DS_EFI_CONTEXT *c=context;
  if(c->Ready!=TRUE || c->Busy!=FALSE)return FALSE;
  c->Busy=TRUE;BOOLEAN ok=c->DurableLog(c->LogContext,event);c->Busy=FALSE;return ok==TRUE;
}
GU_DS_RESULT GuDsEfiRun(GU_DS_EFI_CONTEXT *c,GU_DS_TRANSACTION *t) {
  if(!c || !t || Overlap(c,sizeof(*c),t,sizeof(*t)) || c->Ready!=TRUE)return GU_DS_INVALID;
  if(c->RunUsed!=FALSE || c->Busy!=FALSE)return GU_DS_REUSED;
  c->RunUsed=TRUE;
  /* Keep caller-owned binding/policy edits out of an in-flight transaction. */
  GU_DS_EFI_CONTEXT active=*c;c->Busy=TRUE;
  const GU_DS_OPS ops={&active,AdapterRead,AdapterDisable,AdapterLog};
  GU_DS_RESULT result=GuDecodeSync(t,&ops,&active.Expected);
  c->WriteSpent=active.WriteSpent;c->RunUsed=TRUE;c->Busy=FALSE;
  return result;
}
