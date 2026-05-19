import ctypes
from ctypes import wintypes
import psutil
import struct
from flags import AVATAR_SIZE, PROCESS_VM_READ, PROCESS_QUERY_INFORMATION



kernel32 = ctypes.windll.kernel32
_RPM = kernel32.ReadProcessMemory
_RPM.argtypes = [wintypes.HANDLE, wintypes.LPCVOID, wintypes.LPVOID, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]
_RPM.restype = wintypes.BOOL

def get_process_handle(pid=None):
    if pid is None:
        pid = next((p.pid for p in psutil.process_iter(['pid', 'name']) if p.info['name'] == "cs2.exe"), None)
    if pid is None:
        return None
    return kernel32.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)

def get_module_base_address(h_proc, module_name):
    psapi = ctypes.windll.psapi
    kernel32 = ctypes.windll.kernel32
    psapi.EnumProcessModules.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    psapi.GetModuleBaseNameW.argtypes = [wintypes.HANDLE, wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD]

    modules = (wintypes.HANDLE * 1024)()
    cb = ctypes.sizeof(modules)
    cb_needed = wintypes.DWORD()

    if psapi.EnumProcessModules(h_proc, modules, cb, ctypes.byref(cb_needed)):
        module_count = int(cb_needed.value / ctypes.sizeof(wintypes.HANDLE))
        
        for i in range(module_count):
            name_buffer = ctypes.create_unicode_buffer(260)
            psapi.GetModuleBaseNameW(h_proc, modules[i], name_buffer, 260)
            
            if name_buffer.value.lower() == module_name.lower():
                psapi.GetModuleInformation.argtypes = [wintypes.HANDLE, wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD]
                class MODULEINFO(ctypes.Structure):
                    _fields_ = [
                        ("lpBaseOfDll", ctypes.c_void_p),
                        ("SizeOfImage", wintypes.DWORD),
                        ("EntryPoint", ctypes.c_void_p),
                    ]
                info = MODULEINFO()
                psapi.GetModuleInformation(h_proc, modules[i], ctypes.byref(info), ctypes.sizeof(info))
                return info.lpBaseOfDll
    return None



def read_mem(h_proc, address, data_type):
    buffer = data_type()
    data = _RPM(h_proc, address, ctypes.byref(buffer), ctypes.sizeof(data_type), None)
    if data:
        return buffer.value
    return None

def read_string(h_proc, address, max_length=64):
    buffer = ctypes.create_string_buffer(max_length)
    if ctypes.windll.kernel32.ReadProcessMemory(h_proc, ctypes.c_void_p(address), buffer, max_length, None):
        try:
            return buffer.value.decode('utf-8')
        except:
            return "Unknown"
    return "Error"


def read_vec3(h_proc, address):
    buffer = ctypes.create_string_buffer(12)
    if ctypes.windll.kernel32.ReadProcessMemory(h_proc, ctypes.c_void_p(address), buffer, 12, None):
        return struct.unpack('fff', buffer.raw)
    return (0.0, 0.0, 0.0)



def get_weapon_name_by_index(index: int) -> str:
    weapons = {
        1: "Deagle", 2: "elite", 3: "fiveseven", 4: "Glock",
        30: "tec9", 32: "P2000", 36: "p250", 61: "usp_silencer", 63: "cz75a",
        17: "mac10", 19: "p90", 23: "mp5sd", 24: "ump45", 26: "Bizon", 34: "MP9", 33: "MP7",
        7: "ak47", 8: "AUG", 10: "FAMAS", 13: "GalilAR", 16: "m4a1",
        60: "m4a1_silencer", 39: "SG556",
        9: "AWP", 11: "G3SG1", 38: "SCAR20", 40: "SSG08",
        25: "XM1014", 27: "Mag-7", 28: "Negev", 29: "M249", 35: "sawedoff",
        42: "Knife", 59: "Knife", 500: "Knife", 505: "knife_flip", 506: "knife_gut", 
        507: "knife_karambit", 508: "knife_m9_bayonet", 509: "Knife", 515: "knife_butterfly",
        31: "Taser", 43: "Flashbang", 44: "hegrenade", 45: "smokegrenade", 
        46: "Molotov", 47: "Decoy", 48: "incgrenade", 49: "C4"
    }
    return weapons.get(index, f"disconnect")
       
