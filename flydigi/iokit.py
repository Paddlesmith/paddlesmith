"""macOS HID transport, via IOKit's IOHIDManager through ctypes.

This stands in for Linux ``hidraw``.  It needs nothing beyond the Python
that ships with macOS: IOKit and CoreFoundation are loaded with ctypes.

Semantics are kept close to hidraw so the rest of the package does not
care which one it is talking to:

* :func:`enumerate_devices` lists every HID interface with its vendor id,
  product id, name and the first usage page of its report descriptor.
* Each interface gets a stable ``path`` string built from its IORegistry
  entry id (``IOService:<id>``).
* :func:`open_path` returns a :class:`Handle`.  Like opening a hidraw node
  twice, every handle on the same interface receives its *own* copy of each
  input report, so the configuration channel and the live input monitor can
  read side by side.

Input reports are delivered by an IOKit callback on a private run-loop
thread and queued per handle.  Output reports go out synchronously with
``IOHIDDeviceSetReport``.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import queue
import threading
from ctypes import (CFUNCTYPE, POINTER, byref, c_bool, c_char_p, c_double,
                    c_int32, c_long, c_uint8, c_uint32, c_uint64, c_void_p)
from dataclasses import dataclass

_iokit = ctypes.cdll.LoadLibrary(
    "/System/Library/Frameworks/IOKit.framework/IOKit")
_cf = ctypes.cdll.LoadLibrary(
    "/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")

CFIndex = c_long
IOReturn = c_int32
io_service_t = c_uint32

kCFStringEncodingUTF8 = 0x08000100
kCFNumberSInt32Type = 3
kIOHIDReportTypeOutput = 1
kIOHIDOptionsTypeNone = 0
kIOReturnSuccess = 0
kIOReturnNotPermitted = -536870174      # 0xE00002E2
kIOReturnExclusiveAccess = -536870203   # 0xE00002C5


def _fn(lib, name, restype, *argtypes):
    f = getattr(lib, name)
    f.restype = restype
    f.argtypes = list(argtypes)
    return f


# -- CoreFoundation --------------------------------------------------------

CFRelease = _fn(_cf, "CFRelease", None, c_void_p)
CFRetain = _fn(_cf, "CFRetain", c_void_p, c_void_p)
CFGetTypeID = _fn(_cf, "CFGetTypeID", c_long, c_void_p)
CFNumberGetTypeID = _fn(_cf, "CFNumberGetTypeID", c_long)
CFStringGetTypeID = _fn(_cf, "CFStringGetTypeID", c_long)
CFDataGetTypeID = _fn(_cf, "CFDataGetTypeID", c_long)
CFStringCreateWithCString = _fn(_cf, "CFStringCreateWithCString", c_void_p,
                                c_void_p, c_char_p, c_uint32)
CFStringGetCString = _fn(_cf, "CFStringGetCString", c_bool,
                         c_void_p, c_char_p, CFIndex, c_uint32)
CFNumberGetValue = _fn(_cf, "CFNumberGetValue", c_bool,
                       c_void_p, c_long, c_void_p)
CFDataGetLength = _fn(_cf, "CFDataGetLength", CFIndex, c_void_p)
CFDataGetBytePtr = _fn(_cf, "CFDataGetBytePtr", c_void_p, c_void_p)
CFSetGetCount = _fn(_cf, "CFSetGetCount", CFIndex, c_void_p)
CFSetGetValues = _fn(_cf, "CFSetGetValues", None, c_void_p, POINTER(c_void_p))
CFRunLoopGetCurrent = _fn(_cf, "CFRunLoopGetCurrent", c_void_p)
CFRunLoopRunInMode = _fn(_cf, "CFRunLoopRunInMode", c_int32,
                         c_void_p, c_double, c_bool)
kCFRunLoopDefaultMode = c_void_p.in_dll(_cf, "kCFRunLoopDefaultMode")

# -- IOKit -----------------------------------------------------------------

IOHIDManagerCreate = _fn(_iokit, "IOHIDManagerCreate", c_void_p,
                         c_void_p, c_uint32)
IOHIDManagerSetDeviceMatching = _fn(_iokit, "IOHIDManagerSetDeviceMatching",
                                    None, c_void_p, c_void_p)
IOHIDManagerCopyDevices = _fn(_iokit, "IOHIDManagerCopyDevices", c_void_p,
                              c_void_p)
IOHIDDeviceGetProperty = _fn(_iokit, "IOHIDDeviceGetProperty", c_void_p,
                             c_void_p, c_void_p)
IOHIDDeviceGetService = _fn(_iokit, "IOHIDDeviceGetService", io_service_t,
                            c_void_p)
IOHIDDeviceCreate = _fn(_iokit, "IOHIDDeviceCreate", c_void_p,
                        c_void_p, io_service_t)
IOHIDDeviceOpen = _fn(_iokit, "IOHIDDeviceOpen", IOReturn, c_void_p, c_uint32)
IOHIDDeviceClose = _fn(_iokit, "IOHIDDeviceClose", IOReturn,
                       c_void_p, c_uint32)
IOHIDDeviceScheduleWithRunLoop = _fn(_iokit, "IOHIDDeviceScheduleWithRunLoop",
                                     None, c_void_p, c_void_p, c_void_p)
IOHIDDeviceUnscheduleFromRunLoop = _fn(
    _iokit, "IOHIDDeviceUnscheduleFromRunLoop",
    None, c_void_p, c_void_p, c_void_p)
IOHIDDeviceSetReport = _fn(_iokit, "IOHIDDeviceSetReport", IOReturn,
                           c_void_p, c_uint32, CFIndex, c_void_p, CFIndex)
IORegistryEntryGetRegistryEntryID = _fn(
    _iokit, "IORegistryEntryGetRegistryEntryID", c_int32,
    io_service_t, POINTER(c_uint64))
IORegistryEntryIDMatching = _fn(_iokit, "IORegistryEntryIDMatching", c_void_p,
                                c_uint64)
IOServiceGetMatchingService = _fn(_iokit, "IOServiceGetMatchingService",
                                  io_service_t, c_uint32, c_void_p)
IOObjectRelease = _fn(_iokit, "IOObjectRelease", c_int32, io_service_t)

# void callback(void *ctx, IOReturn result, void *sender,
#               IOHIDReportType type, uint32_t reportID,
#               uint8_t *report, CFIndex reportLength)
InputReportCallback = CFUNCTYPE(None, c_void_p, IOReturn, c_void_p,
                                c_uint32, c_uint32, POINTER(c_uint8), CFIndex)
IOHIDDeviceRegisterInputReportCallback = _fn(
    _iokit, "IOHIDDeviceRegisterInputReportCallback", None,
    c_void_p, c_void_p, CFIndex, InputReportCallback, c_void_p)


class HidError(OSError):
    pass


class PermissionDenied(HidError):
    pass


# -- property helpers ------------------------------------------------------

_cfstr_cache: dict = {}


def _cfstr(s: str):
    ref = _cfstr_cache.get(s)
    if ref is None:
        ref = CFStringCreateWithCString(None, s.encode(), kCFStringEncodingUTF8)
        _cfstr_cache[s] = ref     # kept for the life of the process
    return ref


def _prop(dev, key: str):
    return IOHIDDeviceGetProperty(dev, _cfstr(key))


def _prop_int(dev, key: str):
    ref = _prop(dev, key)
    if not ref or CFGetTypeID(ref) != CFNumberGetTypeID():
        return None
    out = c_int32()
    if not CFNumberGetValue(ref, kCFNumberSInt32Type, byref(out)):
        return None
    return out.value


def _prop_str(dev, key: str) -> str:
    ref = _prop(dev, key)
    if not ref or CFGetTypeID(ref) != CFStringGetTypeID():
        return ""
    buf = ctypes.create_string_buffer(512)
    if not CFStringGetCString(ref, buf, len(buf), kCFStringEncodingUTF8):
        return ""
    return buf.value.decode("utf-8", "replace")


def _prop_bytes(dev, key: str) -> bytes:
    ref = _prop(dev, key)
    if not ref or CFGetTypeID(ref) != CFDataGetTypeID():
        return b""
    n = CFDataGetLength(ref)
    ptr = CFDataGetBytePtr(ref)
    return ctypes.string_at(ptr, n) if ptr and n > 0 else b""


def _entry_id(dev) -> int:
    service = IOHIDDeviceGetService(dev)
    out = c_uint64()
    if not service or IORegistryEntryGetRegistryEntryID(service, byref(out)):
        return 0
    return out.value


# -- enumeration -----------------------------------------------------------

@dataclass
class DeviceRecord:
    path: str
    vid: int
    pid: int
    name: str
    report_descriptor: bytes
    primary_usage_page: int | None
    max_input: int
    max_output: int


def enumerate_devices() -> list[DeviceRecord]:
    mgr = IOHIDManagerCreate(None, kIOHIDOptionsTypeNone)
    if not mgr:
        raise HidError("IOHIDManagerCreate failed")
    try:
        IOHIDManagerSetDeviceMatching(mgr, None)
        devset = IOHIDManagerCopyDevices(mgr)
        if not devset:
            return []
        try:
            n = CFSetGetCount(devset)
            refs = (c_void_p * n)()
            CFSetGetValues(devset, refs)
            out = []
            for dev in refs:
                if not dev:
                    continue
                eid = _entry_id(dev)
                if not eid:
                    continue
                out.append(DeviceRecord(
                    path=f"IOService:{eid}",
                    vid=_prop_int(dev, "VendorID") or 0,
                    pid=_prop_int(dev, "ProductID") or 0,
                    name=_prop_str(dev, "Product"),
                    report_descriptor=_prop_bytes(dev, "ReportDescriptor"),
                    primary_usage_page=_prop_int(dev, "PrimaryUsagePage"),
                    max_input=_prop_int(dev, "MaxInputReportSize") or 64,
                    max_output=_prop_int(dev, "MaxOutputReportSize") or 0,
                ))
            out.sort(key=lambda r: r.path)
            return out
        finally:
            CFRelease(devset)
    finally:
        CFRelease(mgr)


# -- open devices ----------------------------------------------------------

class _SharedDevice:
    """One IOHIDDevice, opened once, fanned out to any number of handles."""

    def __init__(self, path: str):
        self.path = path
        self.handles: list[Handle] = []
        self.lock = threading.Lock()
        self._stop = threading.Event()
        self._ready = threading.Event()
        self._open_error: Exception | None = None

        try:
            eid = int(path.split(":", 1)[1])
        except (IndexError, ValueError):
            raise HidError(f"Not an IOKit device path: {path}")
        matching = IORegistryEntryIDMatching(eid)   # consumed by the call below
        service = IOServiceGetMatchingService(0, matching)
        if not service:
            raise HidError(f"{path} is no longer present (was it unplugged?)")
        try:
            self.dev = IOHIDDeviceCreate(None, service)
        finally:
            IOObjectRelease(service)
        if not self.dev:
            raise HidError(f"IOHIDDeviceCreate failed for {path}")

        rc = IOHIDDeviceOpen(self.dev, kIOHIDOptionsTypeNone)
        if rc != kIOReturnSuccess:
            CFRelease(self.dev)
            self.dev = None
            if rc == kIOReturnNotPermitted:
                raise PermissionDenied(
                    "macOS refused access to the controller. Allow this app "
                    "(Terminal, or whichever app you launched it from) under "
                    "System Settings > Privacy & Security > Input Monitoring, "
                    "then quit and reopen it.")
            if rc == kIOReturnExclusiveAccess:
                raise HidError("Another program has the controller open "
                               "exclusively. Quit it and try again.")
            raise HidError(f"IOHIDDeviceOpen failed (0x{rc & 0xFFFFFFFF:08X})")

        self.max_output = _prop_int(self.dev, "MaxOutputReportSize") or 0
        size = max(64, _prop_int(self.dev, "MaxInputReportSize") or 64)
        self._buf = (c_uint8 * size)()
        self._callback = InputReportCallback(self._on_report)  # keep alive

        self._thread = threading.Thread(target=self._run, name=f"hid {path}",
                                        daemon=True)
        self._thread.start()
        self._ready.wait(2.0)
        if self._open_error:
            raise self._open_error

    # run-loop thread
    def _run(self):
        try:
            loop = CFRunLoopGetCurrent()
            IOHIDDeviceRegisterInputReportCallback(
                self.dev, ctypes.cast(self._buf, c_void_p), len(self._buf),
                self._callback, None)
            IOHIDDeviceScheduleWithRunLoop(self.dev, loop, kCFRunLoopDefaultMode)
        except Exception as exc:          # pragma: no cover - defensive
            self._open_error = HidError(f"Could not start reading: {exc}")
            self._ready.set()
            return
        self._ready.set()
        while not self._stop.is_set():
            CFRunLoopRunInMode(kCFRunLoopDefaultMode, 0.05, False)
        IOHIDDeviceUnscheduleFromRunLoop(self.dev, loop, kCFRunLoopDefaultMode)

    def _on_report(self, _ctx, result, _sender, _type, _report_id, report, length):
        if result != kIOReturnSuccess or length <= 0:
            return
        data = ctypes.string_at(report, length)
        with self.lock:
            handles = list(self.handles)
        for h in handles:
            h._push(data)

    def write(self, data: bytes) -> None:
        """Send an output report.  ``data`` excludes the report-ID byte."""
        attempts = [data]
        if self.max_output and len(data) < self.max_output:
            attempts.append(data + bytes(self.max_output - len(data)))
        rc = 0
        for payload in attempts:
            buf = (c_uint8 * len(payload)).from_buffer_copy(payload)
            rc = IOHIDDeviceSetReport(self.dev, kIOHIDReportTypeOutput, 0,
                                      ctypes.cast(buf, c_void_p), len(payload))
            if rc == kIOReturnSuccess:
                return
        raise HidError(f"IOHIDDeviceSetReport failed (0x{rc & 0xFFFFFFFF:08X})")

    def shutdown(self) -> None:
        self._stop.set()
        self._thread.join(1.0)
        if self.dev:
            IOHIDDeviceClose(self.dev, kIOHIDOptionsTypeNone)
            CFRelease(self.dev)
            self.dev = None


_open: dict[str, _SharedDevice] = {}
_open_lock = threading.Lock()


class Handle:
    """What :func:`open_path` returns: a private queue of input reports
    plus the ability to write output reports."""

    def __init__(self, shared: _SharedDevice):
        self._shared = shared
        self._q: queue.Queue = queue.Queue(maxsize=4096)
        self.closed = False

    def _push(self, data: bytes) -> None:
        try:
            self._q.put_nowait(data)
        except queue.Full:                # a reader stopped reading; keep newest
            try:
                self._q.get_nowait()
            except queue.Empty:
                pass
            self._q.put_nowait(data)

    def read(self, timeout: float):
        """Next input report, or None after ``timeout`` seconds."""
        try:
            return self._q.get(timeout=max(0.0, timeout))
        except queue.Empty:
            return None

    def drain(self) -> None:
        while True:
            try:
                self._q.get_nowait()
            except queue.Empty:
                return

    def write(self, data: bytes) -> None:
        self._shared.write(data)

    def close(self) -> None:
        if self.closed:
            return
        self.closed = True
        shared = self._shared
        with _open_lock:
            with shared.lock:
                shared.handles.remove(self)
                last = not shared.handles
            if last:
                _open.pop(shared.path, None)
        if last:
            shared.shutdown()


def open_path(path: str) -> Handle:
    with _open_lock:
        shared = _open.get(path)
        if shared is None:
            shared = _SharedDevice(path)
            _open[path] = shared
        handle = Handle(shared)
        with shared.lock:
            shared.handles.append(handle)
    return handle
