"""Native worker resource limits; failure prevents unbounded inference."""
import os


def apply(memory_mb,cpu_seconds):
    if os.name!='nt':
        import resource
        resource.setrlimit(resource.RLIMIT_AS,(memory_mb*1024**2,memory_mb*1024**2))
        resource.setrlimit(resource.RLIMIT_CPU,(cpu_seconds,cpu_seconds))
        return None
    import ctypes
    from ctypes import wintypes
    size=ctypes.c_size_t
    class Basic(ctypes.Structure):
        _fields_=[('process_time',ctypes.c_int64),('job_time',ctypes.c_int64),('flags',wintypes.DWORD),('min_working',size),('max_working',size),('active',wintypes.DWORD),('affinity',size),('priority',wintypes.DWORD),('scheduling',wintypes.DWORD)]
    class IO(ctypes.Structure):
        _fields_=[(name,ctypes.c_uint64) for name in ['reads','writes','other','read_bytes','write_bytes','other_bytes']]
    class Extended(ctypes.Structure):
        _fields_=[('basic',Basic),('io',IO),('process_memory',size),('job_memory',size),('peak_process',size),('peak_job',size)]
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateJobObjectW.restype=wintypes.HANDLE;kernel.GetCurrentProcess.restype=wintypes.HANDLE
    kernel.SetInformationJobObject.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD]
    kernel.AssignProcessToJobObject.argtypes=[wintypes.HANDLE,wintypes.HANDLE]
    handle=kernel.CreateJobObjectW(None,None)
    limits=Extended();limits.basic.flags=0x2|0x100|0x2000;limits.basic.process_time=cpu_seconds*10000000;limits.process_memory=memory_mb*1024**2
    if not handle or not kernel.SetInformationJobObject(handle,9,ctypes.byref(limits),ctypes.sizeof(limits)) or not kernel.AssignProcessToJobObject(handle,kernel.GetCurrentProcess()):raise RuntimeError('Cannot establish native worker resource limits')
    # Keep the job handle alive until worker exit; closing it kills the worker.
    return handle
