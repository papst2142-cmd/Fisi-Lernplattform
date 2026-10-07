#!/bin/bash
# Fuehrt einen Befehl in einer cgroup (v1) mit Speicher- und/oder CPU-Grenze aus.
# Aufruf: mit_grenze.sh SPEICHER_MB CPU_PROZENT BEFEHL...   (0 = keine Grenze)
MEM=$1; CPU=$2; shift 2
MBASE=$(dirname /sys/fs/cgroup/memory$(grep ":memory:" /proc/self/cgroup | cut -d: -f3))/$(basename $(grep ":memory:" /proc/self/cgroup | cut -d: -f3))
G=fisi_$$
mkdir -p $MBASE/$G /sys/fs/cgroup/cpu/$G
if [ "$MEM" != 0 ]; then echo $((MEM*1024*1024)) > $MBASE/$G/memory.limit_in_bytes; fi
if [ "$CPU" != 0 ]; then echo 100000 > /sys/fs/cgroup/cpu/$G/cpu.cfs_period_us; echo $((CPU*1000)) > /sys/fs/cgroup/cpu/$G/cpu.cfs_quota_us; fi
echo $$ > $MBASE/$G/cgroup.procs
echo $$ > /sys/fs/cgroup/cpu/$G/cgroup.procs
"$@"; RC=$?
echo "Grenze Speicher ${MEM} MB, CPU ${CPU} %: Rueckgabe $RC, Hoechststand $(( $(cat $MBASE/$G/memory.max_usage_in_bytes) / 1048576 )) MB, Begrenzungstreffer $(cat $MBASE/$G/memory.failcnt), OOM: $(grep oom_kill $MBASE/$G/memory.oom_control | tr '\n' ' ')"
exit $RC
