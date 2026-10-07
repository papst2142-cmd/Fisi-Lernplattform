#!/usr/bin/env python3
"""F8: Warum ist speicher_mb in der Messdatei unter Windows leer?
Ruft fisi_leistung.memory_mb() der angegebenen Programmfassung auf und
vergleicht mit demselben Aufruf, bei dem Rueckgabe-/Argumenttypen fuer
GetCurrentProcess und GetProcessMemoryInfo gesetzt sind, und mit psutil.
Nur Diagnose, aendert nichts. Aufruf: python f8_speicher_windows.py ORDNER"""
import ctypes
import os
import sys
from ctypes import wintypes

sys.path.insert(0, os.path.abspath(sys.argv[1]))
os.environ.setdefault("FISI_DB_PATH", os.path.join(os.environ.get("TEMP", "."), "f8.db"))
import fisi_leistung as fle  # noqa: E402

print("Fassung:", sys.argv[1], "Python", sys.version.split()[0],
      "64 Bit" if sys.maxsize > 2 ** 32 else "32 Bit")
print("1) fisi_leistung.memory_mb() unveraendert:", fle.memory_mb())

kernel32 = ctypes.windll.kernel32
psapi = ctypes.windll.psapi
raw = kernel32.GetCurrentProcess()
print("2) GetCurrentProcess() ohne restype liefert:", raw, hex(raw & 0xFFFFFFFFFFFFFFFF))


class Counters(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
                ("PrivateUsage", ctypes.c_size_t)]


counters = Counters()
counters.cb = ctypes.sizeof(Counters)
ctypes.set_last_error(0)
ok = psapi.GetProcessMemoryInfo(raw, ctypes.byref(counters), counters.cb)
print("3) wie im Programm (Handle als int):", ok, "GetLastError", kernel32.GetLastError(),
      "WorkingSet MB", counters.WorkingSetSize / 1048576.0)

kernel32.GetCurrentProcess.restype = wintypes.HANDLE
psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD]
psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
handle = kernel32.GetCurrentProcess()
counters = Counters()
counters.cb = ctypes.sizeof(Counters)
ok = psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb)
print("4) mit restype/argtypes HANDLE:", ok, "WorkingSet MB %.1f, Private MB %.1f" % (
    counters.WorkingSetSize / 1048576.0, counters.PrivateUsage / 1048576.0))
try:
    import psutil
    info = psutil.Process().memory_info()
    print("5) psutil zum Vergleich: rss MB %.1f, private MB %.1f" % (
        info.rss / 1048576.0, getattr(info, "private", 0) / 1048576.0))
except ImportError:
    print("5) psutil nicht installiert")
