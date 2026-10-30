"""Restrict explicitly requested content logs to the current user."""
import os


def restrict(path, *, directory=False):
    if os.name!='nt':
        os.chmod(path,0o700 if directory else 0o600)
        return
    import ctypes
    from ctypes import wintypes
    advapi=ctypes.WinDLL('advapi32',use_last_error=True)
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    ptr=ctypes.c_void_p
    kernel.GetCurrentProcess.restype=wintypes.HANDLE
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    kernel.LocalFree.argtypes=[ptr]
    advapi.OpenProcessToken.argtypes=[wintypes.HANDLE,wintypes.DWORD,ctypes.POINTER(wintypes.HANDLE)]
    advapi.GetTokenInformation.argtypes=[wintypes.HANDLE,ctypes.c_int,ptr,wintypes.DWORD,ctypes.POINTER(wintypes.DWORD)]
    advapi.ConvertSidToStringSidW.argtypes=[ptr,ctypes.POINTER(wintypes.LPWSTR)]
    advapi.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,ctypes.POINTER(ptr),ctypes.POINTER(wintypes.DWORD)]
    advapi.GetSecurityDescriptorDacl.argtypes=[ptr,ctypes.POINTER(wintypes.BOOL),ctypes.POINTER(ptr),ctypes.POINTER(wintypes.BOOL)]
    advapi.SetNamedSecurityInfoW.argtypes=[wintypes.LPWSTR,ctypes.c_int,wintypes.DWORD,ptr,ptr,ptr,ptr]
    advapi.SetNamedSecurityInfoW.restype=wintypes.DWORD
    token=wintypes.HANDLE();sid_text=wintypes.LPWSTR();descriptor=ptr()
    try:
        if not advapi.OpenProcessToken(kernel.GetCurrentProcess(),0x8,ctypes.byref(token)):raise ctypes.WinError(ctypes.get_last_error())
        size=wintypes.DWORD()
        advapi.GetTokenInformation(token,1,None,0,ctypes.byref(size))
        data=ctypes.create_string_buffer(size.value)
        if not advapi.GetTokenInformation(token,1,data,size.value,ctypes.byref(size)):raise ctypes.WinError(ctypes.get_last_error())
        sid=ctypes.cast(data,ctypes.POINTER(ptr))[0]
        if not advapi.ConvertSidToStringSidW(sid,ctypes.byref(sid_text)):raise ctypes.WinError(ctypes.get_last_error())
        sddl='D:P(A;'+('OICI' if directory else '')+';FA;;;'+sid_text.value+')'
        if not advapi.ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl,1,ctypes.byref(descriptor),None):raise ctypes.WinError(ctypes.get_last_error())
        present=wintypes.BOOL();defaulted=wintypes.BOOL();dacl=ptr()
        if not advapi.GetSecurityDescriptorDacl(descriptor,ctypes.byref(present),ctypes.byref(dacl),ctypes.byref(defaulted)):raise ctypes.WinError(ctypes.get_last_error())
        code=advapi.SetNamedSecurityInfoW(str(path),1,0x80000004,None,None,dacl,None)
        if code:raise ctypes.WinError(code)
    finally:
        if descriptor:kernel.LocalFree(descriptor)
        if sid_text:kernel.LocalFree(ctypes.cast(sid_text,ptr))
        if token:kernel.CloseHandle(token)
