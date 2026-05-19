from flags import *
import re
import sys
import os
import ctypes
import requests
from types import SimpleNamespace
from memory import *
import time
import random 
import string
import math
import threading
import socketio

from flask import Flask, render_template, send_from_directory
from flask_socketio import SocketIO, emit

app = Flask(__name__, 
            static_url_path='',
            static_folder='templates', 
            template_folder='templates')

socketio_server = SocketIO(app, cors_allowed_origins="*")

@app.route('/maps/<path:filename>')
def serve_map(filename):
    return send_from_directory('maps', filename)

@app.route('/weapons/<path:filename>')
def serve_weapon(filename):
    return send_from_directory('weapons', filename)

@app.route('/')
def index():
    return render_template('index.html')

@socketio_server.on('update_data')
def handle_update(data):
    emit('draw_radar', data, broadcast=True)

@socketio_server.on('map_update')
def handle_map_update(data):
    emit('map_update', data, broadcast=True)


def get_data(url):
    content = requests.get(url).text
    pattern = r'(\w+)\s*=\s*(0x[0-9a-fA-F]+|\d+);'
    matches = re.findall(pattern, content)
    data = {name: int(value, 0) for name, value in matches}
    if not data:
        return None
    return SimpleNamespace(**data)

offsets = get_data('https://raw.githubusercontent.com/a2x/cs2-dumper/refs/heads/main/output/offsets.hpp')
netvars = get_data('https://raw.githubusercontent.com/a2x/cs2-dumper/refs/heads/main/output/client_dll.hpp')

def random_string(length=12):
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))


while True:
    try:
        h_proc = get_process_handle()
        if not h_proc:
            time.sleep(2)
            continue
        client = get_module_base_address(h_proc, "client.dll")
        engine = get_module_base_address(h_proc, "engine2.dll")
        if not client or not engine:
            time.sleep(2)
            continue
        break
    except Exception as e:
        print(f"Ошибка при получении handle или адреса модуля: {e}")
        pass


m_pItemServices = netvars.m_pItemServices
m_bHasHelmet  = netvars.m_bHasHelmet
m_bHasDefuser = netvars.m_bHasDefuser
dwEntityList = offsets.dwEntityList
m_hPlayerPawn = netvars.m_hPlayerPawn
m_pInGameMoneyServices = netvars.m_pInGameMoneyServices
m_iAccount = netvars.m_iAccount
m_sSanitizedPlayerName = netvars.m_sSanitizedPlayerName
m_iTeamNum = netvars.m_iTeamNum
m_iHealth = netvars.m_iHealth
m_ArmorValue = netvars.m_ArmorValue
m_vOldOrigin = netvars.m_vOldOrigin
m_iItemDefinitionIndex = netvars.m_iItemDefinitionIndex
dwLocalPlayerController = offsets.dwLocalPlayerController
m_angEyeAngles = netvars.m_angEyeAngles
m_bPawnHasDefuser  = netvars.m_bPawnHasDefuser
m_iCompTeammateColor = netvars.m_iCompTeammateColor
m_steamID = netvars.m_steamID
dwGlobalVars = offsets.dwGlobalVars

m_pWeaponServices = netvars.m_pWeaponServices
m_hActiveWeapon = netvars.m_hActiveWeapon
m_AttributeManager = 0x1180
m_Item = netvars.m_Item
m_iItemDefinitionIndex = netvars.m_iItemDefinitionIndex



font = None  
avatar_textures = {}
players_lock = threading.Lock()
avatars_lock = threading.Lock()
cs2_colors = {
    -1: (0.5, 0.5, 0.5, 1.0),    # Unknown/Gray
    0: (0.263, 0.902, 1.0, 1.0), # Blue
    1: (0.0, 0.741, 0.435, 1.0), # Green
    2: (1.0, 1.0, 0.0, 1.0),     # Yellow
    3: (1.0, 0.5, 0.0, 1.0),     # Orange
    4: (0.663, 0.0, 0.788, 1.0), # Purple
}




def get_map() -> None:
    map_name = None
    offset_x = None
    offset_y = None
    map_scale = None
    map_path = None
    
    while True:
        try:
            gv_ptr = read_mem(h_proc, client + dwGlobalVars, ctypes.c_void_p)
            ptr = read_mem(h_proc, gv_ptr + 0x188, ctypes.c_void_p)
            map_name = read_string(h_proc, ptr, 64)
            
            if map_name in ("<empty>", "Error", "", "None"):
                try:
                    socketio_server.emit('map_update', {'map_name': "<empty>"})
                except Exception as e:
                    print(f"SocketIO error: {e}")
                time.sleep(1.5)
                continue
            
            if not os.path.exists(f"maps/{map_name}.txt"):
                print(f"Map config not found: maps/{map_name}.txt")
                time.sleep(1.5)
                continue

            with open(f"maps/{map_name}.txt", "r") as f:
                content = f.read()
            
            def parse_val(key):
                match = re.search(rf'"{key}"\s+"([^"]+)"', content)
                return match.group(1) if match else None

            offset_x = float(v) if (v := parse_val("pos_x")) else None
            offset_y = float(v) if (v := parse_val("pos_y")) else None
            map_scale = float(v) if (v := parse_val("scale")) else None
            map_path = f"maps/{map_name}.png" if os.path.exists(f"maps/{map_name}.png") else None
            
            socketio_server.emit('map_update', {
                'map_name': map_name,
                'offset_x': offset_x,
                'offset_y': offset_y,
                'map_scale': map_scale,
                'map_path': map_path
            })
        except Exception as e:
            print(f"Error in get_map: {e}")
        
        time.sleep(1.5)





def main() -> None:
    global players_data
    while True:
        entity_list = read_mem(h_proc, client + dwEntityList, ctypes.c_void_p)
        if not entity_list:
            time.sleep(random.uniform(0.5, 0.9))
            continue
            
        radar_payload = []
        for i in range(1, 64):
            try:
                list_entry = read_mem(h_proc, entity_list + (8 * (i & 0x7FFF) >> 9) + 16, ctypes.c_void_p)
                if not list_entry: continue
                
                player_controller = read_mem(h_proc, list_entry + 112 * (i & 0x1FF), ctypes.c_void_p)
                if not player_controller or player_controller == 0: continue
                
                
                team = read_mem(h_proc, player_controller + m_iTeamNum, ctypes.c_int)
                if team not in [2, 3]: continue

                color_id = read_mem(h_proc, player_controller + m_iCompTeammateColor, ctypes.c_int)


                name_address = read_mem(h_proc, player_controller + m_sSanitizedPlayerName, ctypes.c_void_p)
                name = read_string(h_proc, name_address, 32)
                
                money_services = read_mem(h_proc, player_controller + m_pInGameMoneyServices, ctypes.c_void_p)
                money = read_mem(h_proc, money_services + m_iAccount, ctypes.c_int)
                

                pawn_handle = read_mem(h_proc, player_controller + m_hPlayerPawn, ctypes.c_uint32)
                if not pawn_handle: continue
                
                pawn_entry  = read_mem(h_proc, entity_list + 8 * ((pawn_handle & 0x7FFF) >> 9) + 16, ctypes.c_void_p)
                if not pawn_entry : continue
                
                pawn_ptr = read_mem(h_proc, pawn_entry  + 112 * (pawn_handle & 0x1FF), ctypes.c_void_p)
                if not pawn_ptr: continue
                
                item_services = read_mem(h_proc, pawn_ptr + m_pItemServices, ctypes.c_void_p)  
                
                health = read_mem(h_proc, pawn_ptr + m_iHealth, ctypes.c_int)
                armor = read_mem(h_proc, pawn_ptr + m_ArmorValue, ctypes.c_int)
                
                # WEAPON READ
                weapon_name = None
                if health > 0:
                    try:
                        weapon_services = read_mem(h_proc, pawn_ptr + m_pWeaponServices, ctypes.c_void_p)
                        if weapon_services:
                            weapon_handle = read_mem(h_proc, weapon_services + m_hActiveWeapon, ctypes.c_uint32)
                            if weapon_handle != 0xFFFFFFFF:
                                weapon_entry = read_mem(h_proc, entity_list + 8 * ((weapon_handle & 0x7FFF) >> 9) + 16, ctypes.c_void_p)
                                weapon_ptr = read_mem(h_proc, weapon_entry + 112 * (weapon_handle & 0x1FF), ctypes.c_void_p)
                                weapon_id = read_mem(h_proc, weapon_ptr + m_AttributeManager + m_Item + m_iItemDefinitionIndex , ctypes.c_uint16)
                                weapon_name = get_weapon_name_by_index(weapon_id)
                    except Exception as e:
                        pass
                

                eye_angles = read_vec3(h_proc, pawn_ptr + m_angEyeAngles)
                yaw = eye_angles[1]
                has_helmet = read_mem(h_proc, item_services + m_bHasHelmet, ctypes.c_bool)
                has_defuse = read_mem(h_proc, item_services + m_bHasDefuser, ctypes.c_bool)
                pos = read_vec3(h_proc, pawn_ptr + m_vOldOrigin)
                
                radar_payload.append({
                    'name': name,
                    'x': pos[0],
                    'y': pos[1],
                    'yaw': yaw,
                    'team': team,
                    'hp': health,
                    "armor": armor,
                    "colorid": color_id,
                    "money": money,
                    "has_helmet": has_helmet,
                    "has_defuse": has_defuse,
                    "weapon_name": weapon_name,
                })
            except Exception:
                continue
        
        try:
            socketio_server.emit('update_data', radar_payload)
        except Exception as e:
            print(f"[ ! ] SocketIO error: {e}")
            
        time.sleep(random.uniform(0.06, 0.09))
    



if __name__ == "__main__":
    threading.Thread(target=main, daemon=True).start()
    threading.Thread(target=get_map, daemon=True).start()
    
    print("[*] Starting server on http://localhost:5000")
    print("[*] Open http://localhost:5000 in your browser")
    
    socketio_server.run(app, host='0.0.0.0', port=5000, debug=True)