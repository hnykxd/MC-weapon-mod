import os
import json
import math
import struct
import wave
import subprocess
import glob
from PIL import Image, ImageDraw

BUILD_DIR = '/tmp/mcweapon_build'
OUT_JAR = '/tmp/mcweapon-1.0.0.jar'

if os.path.exists(BUILD_DIR):
    subprocess.run(['rm', '-rf', BUILD_DIR])
os.makedirs(BUILD_DIR, exist_ok=True)

def make_dirs(p):
    os.makedirs(p, exist_ok=True)

classes_dir = os.path.join(BUILD_DIR, 'classes')
assets_dir = os.path.join(BUILD_DIR, 'assets', 'mcweapon')
data_dir = os.path.join(BUILD_DIR, 'data', 'mcweapon')

make_dirs(classes_dir)
make_dirs(os.path.join(assets_dir, 'textures', 'item'))
make_dirs(os.path.join(assets_dir, 'models', 'item'))
make_dirs(os.path.join(assets_dir, 'items'))
make_dirs(os.path.join(assets_dir, 'lang'))
make_dirs(os.path.join(assets_dir, 'sounds', 'gun'))
make_dirs(os.path.join(data_dir, 'recipe'))

# Weapon Specifications:
# (id, zh_name, en_name, category_id, zh_cat, damage, pellets, fire_interval_ticks, mag_size, reload_ticks, range_blocks, hip_spread, scoped_spread, zoom_level, headshot_mult, piercing, silenced, sound_key, rarity)
WEAPONS = [
    # Sniper Rifles (狙击枪)
    ("awp", "AWP 极地狙击步枪", "AWP Sniper Rifle", "SNIPER", "狙击步枪", 38.0, 1, 30, 10, 46, 120.0, 0.035, 0.0005, 8.0, 1.8, 2, False, "sniper_awp", "EPIC"),
    ("barrett_m82", "巴雷特 M82A1 重型反器材狙击枪", "Barrett M82A1 .50 BMG", "SNIPER", "反器材重狙", 55.0, 1, 40, 10, 56, 140.0, 0.045, 0.0005, 10.0, 1.8, 4, False, "sniper_heavy", "EPIC"),
    ("kar98k", "Kar98k 经典毛瑟狙击步枪", "Karabiner 98k Sniper", "SNIPER", "栓动狙击枪", 28.0, 1, 22, 5, 38, 105.0, 0.025, 0.0008, 6.0, 2.0, 2, False, "sniper_awp", "RARE"),

    # SMGs (冲锋枪)
    ("kriss_vector", "KRISS Vector 维克托短剑冲锋枪", "KRISS Vector .45 ACP", "SMG", "高射速冲锋枪", 5.5, 1, 1, 33, 26, 48.0, 0.032, 0.005, 1.6, 1.5, 1, False, "smg_fast", "RARE"),
    ("mp5", "HK MP5A5 战术冲锋枪", "HK MP5A5 Tactical SMG", "SMG", "战术冲锋枪", 7.0, 1, 2, 30, 28, 56.0, 0.024, 0.004, 2.0, 1.5, 1, False, "smg_shot", "RARE"),
    ("p90", "FN P90 突击冲锋枪", "FN P90 PDW", "SMG", "大弹匣冲锋枪", 6.5, 1, 2, 50, 34, 58.0, 0.028, 0.0045, 2.0, 1.5, 2, False, "smg_shot", "RARE"),
    ("uzi", "Micro UZI 乌兹微型冲锋枪", "Micro UZI SMG", "SMG", "微型冲锋枪", 5.0, 1, 1, 32, 24, 42.0, 0.038, 0.007, 1.5, 1.4, 1, False, "smg_fast", "UNCOMMON"),

    # Pistols (手枪)
    ("desert_eagle", "沙漠之鹰 .50 AE 重型手枪", "Desert Eagle .50 AE", "PISTOL", "重型手枪", 19.0, 1, 9, 7, 26, 68.0, 0.022, 0.002, 2.2, 1.75, 2, False, "pistol_heavy", "RARE"),
    ("glock_18", "格洛克 18C 全自动战术手枪", "Glock-18C Auto Pistol", "PISTOL", "全自动手枪", 6.0, 1, 2, 20, 22, 46.0, 0.030, 0.005, 1.5, 1.5, 1, False, "pistol_shot", "UNCOMMON"),
    ("usp_s", "USP-S 消音特战手枪", "USP-S Tactical Silenced", "PISTOL", "消音手枪", 11.0, 1, 5, 12, 22, 58.0, 0.015, 0.0015, 1.8, 1.65, 1, True, "silenced_shot", "RARE"),

    # Assault Rifles & Shotguns (突击步枪 & 霰弹枪)
    ("ak47", "AK-47 黄金卡拉什尼科夫步枪", "AK-47 Assault Rifle", "RIFLE", "突击步枪", 12.5, 1, 3, 30, 34, 85.0, 0.028, 0.003, 3.0, 1.65, 2, False, "rifle_heavy", "RARE"),
    ("m4a1", "M4A1-S 消音战术卡宾步枪", "M4A1-S Tactical Carbine", "RIFLE", "战术步枪", 10.5, 1, 2, 30, 30, 88.0, 0.018, 0.002, 3.0, 1.6, 1, True, "silenced_shot", "RARE"),
    ("spas_12", "SPAS-12 战术泵动霰弹枪", "Franchi SPAS-12 Shotgun", "SHOTGUN", "战术霰弹枪", 4.5, 8, 16, 8, 36, 32.0, 0.068, 0.022, 1.6, 1.4, 1, False, "shotgun_blast", "RARE"),
]

# 1. Synthesize Custom Gun Sound Effects (.ogg)
print("Synthesizing custom gun sound effects...")
import random
random.seed(42)

def synth_sound(filename, duration, fn):
    wav_path = f"/tmp/{filename}.wav"
    ogg_path = os.path.join(assets_dir, 'sounds', 'gun', f"{filename}.ogg")
    sample_rate = 22050
    n_samples = int(sample_rate * duration)
    with wave.open(wav_path, 'w') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        frames = bytearray()
        for i in range(n_samples):
            t = i / sample_rate
            val = max(-1.0, min(1.0, fn(t, duration)))
            frames += struct.pack('<h', int(val * 32767))
        w.writeframes(frames)
    subprocess.run([
        'ffmpeg', '-y', '-i', wav_path,
        '-c:a', 'libvorbis', '-ac', '1', '-ar', '22050', '-b:a', '48k',
        ogg_path
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    os.remove(wav_path)

# Heavy sniper boom (.50 BMG)
synth_sound("sniper_heavy", 0.65, lambda t, d: (
    (random.uniform(-1, 1) * math.exp(-t * 14.0) * 0.85) +
    (math.sin(2 * math.pi * (95 * math.exp(-t * 4.5)) * t) * math.exp(-t * 6.0) * 0.9) +
    (math.sin(2 * math.pi * 42 * t) * math.exp(-t * 4.0) * 0.6)
))

# Crisp AWP / Kar98k crack
synth_sound("sniper_awp", 0.50, lambda t, d: (
    (random.uniform(-1, 1) * math.exp(-t * 18.0) * 0.9) +
    (math.sin(2 * math.pi * (140 * math.exp(-t * 6.0)) * t) * math.exp(-t * 8.0) * 0.8) +
    (math.sin(2 * math.pi * 65 * t) * math.exp(-t * 5.5) * 0.5)
))

# Fast SMG pop
synth_sound("smg_fast", 0.14, lambda t, d: (
    (random.uniform(-1, 1) * math.exp(-t * 48.0) * 0.8) +
    (math.sin(2 * math.pi * (240 * math.exp(-t * 18.0)) * t) * math.exp(-t * 28.0) * 0.7)
))

# Tactical SMG shot
synth_sound("smg_shot", 0.17, lambda t, d: (
    (random.uniform(-1, 1) * math.exp(-t * 40.0) * 0.85) +
    (math.sin(2 * math.pi * (195 * math.exp(-t * 15.0)) * t) * math.exp(-t * 24.0) * 0.75)
))

# Heavy Desert Eagle cannon
synth_sound("pistol_heavy", 0.34, lambda t, d: (
    (random.uniform(-1, 1) * math.exp(-t * 22.0) * 0.9) +
    (math.sin(2 * math.pi * (130 * math.exp(-t * 8.0)) * t) * math.exp(-t * 12.0) * 0.85)
))

# Standard Pistol shot
synth_sound("pistol_shot", 0.16, lambda t, d: (
    (random.uniform(-1, 1) * math.exp(-t * 42.0) * 0.8) +
    (math.sin(2 * math.pi * (220 * math.exp(-t * 16.0)) * t) * math.exp(-t * 25.0) * 0.7)
))

# Silenced pew (USP-S / M4A1-S)
synth_sound("silenced_shot", 0.14, lambda t, d: (
    (random.uniform(-1, 1) * math.exp(-t * 55.0) * 0.45) +
    (math.sin(2 * math.pi * (320 * math.exp(-t * 22.0)) * t) * math.exp(-t * 32.0) * 0.65)
))

# AK-47 heavy rifle crack
synth_sound("rifle_heavy", 0.24, lambda t, d: (
    (random.uniform(-1, 1) * math.exp(-t * 30.0) * 0.9) +
    (math.sin(2 * math.pi * (160 * math.exp(-t * 10.0)) * t) * math.exp(-t * 16.0) * 0.8)
))

# Shotgun blast
synth_sound("shotgun_blast", 0.38, lambda t, d: (
    (random.uniform(-1, 1) * math.exp(-t * 19.0) * 0.95) +
    (math.sin(2 * math.pi * (105 * math.exp(-t * 7.0)) * t) * math.exp(-t * 10.0) * 0.85)
))

SOUND_KEYS = [
    "sniper_heavy", "sniper_awp", "smg_fast", "smg_shot",
    "pistol_heavy", "pistol_shot", "silenced_shot", "rifle_heavy", "shotgun_blast"
]

sounds_json = {}
for sk in SOUND_KEYS:
    sounds_json[f"gun.{sk}"] = {
        "sounds": [{"name": f"mcweapon:gun/{sk}", "stream": False}]
    }
with open(os.path.join(assets_dir, 'sounds.json'), 'w', encoding='utf-8') as f:
    json.dump(sounds_json, f, indent=2)

# 2. Generate Detailed 32x32 Pixel-Art Weapon Textures
print("Generating 32x32 pixel-art textures for all 13 weapons + tactical ammo box...")

def draw_gun_texture(weapon_id):
    img = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Helper to draw pixel or rect with outline
    def rect(x1, y1, x2, y2, fill, outline=None):
        d.rectangle([x1, y1, x2, y2], fill=fill, outline=outline)

    def line(x1, y1, x2, y2, fill, width=1):
        d.line([x1, y1, x2, y2], fill=fill, width=width)

    # Colors
    DARK_STEEL = (38, 42, 48, 255)
    MID_STEEL = (68, 74, 84, 255)
    LIGHT_STEEL = (110, 118, 130, 255)
    BLACK_POLY = (24, 26, 30, 255)
    LASER_RED = (255, 30, 30, 255)
    LASER_GLOW = (255, 110, 110, 255)
    SCOPE_GLASS = (50, 210, 255, 255)
    WOOD_DARK = (105, 58, 28, 255)
    WOOD_LIGHT = (148, 86, 42, 255)
    GOLD_MAIN = (235, 190, 55, 255)
    GOLD_HI = (255, 230, 110, 255)
    AWP_GREEN = (52, 102, 58, 255)
    AWP_GREEN_HI = (72, 135, 78, 255)
    TAN_BODY = (194, 168, 120, 255)

    # All guns drawn horizontally pointing right (from left stock x=2..8 to right barrel x=26..31, y centered around 14..18)
    if weapon_id == "awp":
        # Stock & chassis (Arctic Warfare green)
        rect(2, 15, 9, 20, AWP_GREEN, BLACK_POLY)
        rect(4, 17, 7, 18, BLACK_POLY) # thumbhole
        rect(9, 14, 20, 18, AWP_GREEN, BLACK_POLY)
        rect(10, 15, 19, 16, AWP_GREEN_HI)
        # Pistol grip & trigger
        rect(9, 18, 11, 23, BLACK_POLY)
        # Magazine
        rect(14, 18, 17, 23, DARK_STEEL, BLACK_POLY)
        # Long heavy barrel + muzzle brake
        rect(20, 14, 30, 16, DARK_STEEL)
        rect(29, 13, 31, 17, BLACK_POLY)
        # Bipod folded under barrel
        line(21, 17, 25, 20, MID_STEEL, 1)
        # Large 8x Sniper Scope on top
        rect(10, 9, 22, 12, BLACK_POLY)
        rect(9, 8, 11, 13, DARK_STEEL)
        rect(21, 8, 23, 13, DARK_STEEL)
        rect(23, 9, 23, 12, SCOPE_GLASS)
        line(12, 12, 12, 14, MID_STEEL)
        line(19, 12, 19, 14, MID_STEEL)
        # Under-barrel Laser Sight Red Dot module
        rect(21, 16, 24, 18, BLACK_POLY)
        rect(25, 17, 26, 17, LASER_RED)
        img.putpixel((27, 17), LASER_GLOW)

    elif weapon_id == "barrett_m82":
        # Heavy anti-materiel grey steel chassis
        rect(1, 14, 8, 20, DARK_STEEL, BLACK_POLY)
        rect(8, 13, 21, 18, MID_STEEL, BLACK_POLY)
        rect(9, 14, 20, 15, LIGHT_STEEL)
        # Grip & large .50 BMG tilted box mag
        rect(9, 18, 11, 23, BLACK_POLY)
        rect(14, 18, 19, 24, DARK_STEEL, BLACK_POLY)
        # Fluted heavy barrel + iconic arrowhead muzzle brake
        rect(21, 14, 28, 16, DARK_STEEL)
        rect(28, 12, 31, 18, BLACK_POLY)
        line(29, 13, 29, 17, LIGHT_STEEL)
        # 10x Heavy Optical Scope
        rect(9, 7, 22, 11, BLACK_POLY)
        rect(8, 6, 10, 12, DARK_STEEL)
        rect(21, 6, 24, 12, DARK_STEEL)
        rect(24, 7, 24, 11, SCOPE_GLASS)
        line(11, 11, 11, 13, MID_STEEL)
        line(19, 11, 19, 13, MID_STEEL)
        # Laser module
        rect(22, 17, 25, 18, BLACK_POLY)
        rect(26, 17, 27, 18, LASER_RED)

    elif weapon_id == "kar98k":
        # Classic wooden rifle stock & body
        rect(2, 15, 9, 20, WOOD_DARK, BLACK_POLY)
        rect(3, 16, 8, 18, WOOD_LIGHT)
        rect(9, 14, 23, 18, WOOD_DARK, BLACK_POLY)
        rect(10, 15, 22, 16, WOOD_LIGHT)
        # Steel receiver & bolt knob
        rect(11, 13, 16, 15, LIGHT_STEEL)
        # Long barrel
        rect(23, 14, 30, 16, DARK_STEEL)
        rect(29, 13, 30, 15, MID_STEEL)
        # Vintage 6x scope
        rect(10, 9, 20, 11, DARK_STEEL)
        rect(20, 9, 21, 11, SCOPE_GLASS)
        line(12, 11, 12, 13, BLACK_POLY)
        line(18, 11, 18, 13, BLACK_POLY)
        # Laser sight
        rect(23, 16, 25, 17, BLACK_POLY)
        rect(26, 16, 27, 17, LASER_RED)

    elif weapon_id == "kriss_vector":
        # Futuristic Super-V body (Tan & Black)
        rect(4, 14, 9, 17, BLACK_POLY) # folding stock
        rect(9, 13, 21, 19, TAN_BODY, BLACK_POLY)
        rect(15, 14, 20, 22, TAN_BODY, BLACK_POLY) # Super-V magwell
        rect(10, 19, 12, 24, BLACK_POLY) # grip
        # Extended diagonal magazine
        rect(16, 22, 19, 29, BLACK_POLY)
        # Barrel + suppressor shroud
        rect(21, 14, 27, 17, DARK_STEEL)
        # EOTech holographic red dot sight
        rect(11, 9, 16, 13, BLACK_POLY)
        rect(13, 10, 15, 11, LASER_RED)
        # Integrated front laser red dot
        rect(21, 17, 23, 18, BLACK_POLY)
        rect(24, 17, 25, 18, LASER_RED)

    elif weapon_id == "mp5":
        # Classic HK MP5 black steel
        rect(3, 14, 9, 17, BLACK_POLY)
        rect(9, 13, 22, 18, DARK_STEEL, BLACK_POLY)
        rect(10, 14, 18, 16, MID_STEEL)
        rect(10, 18, 12, 23, BLACK_POLY) # grip
        # Iconic curved 9mm magazine
        line(16, 18, 18, 25, MID_STEEL, 2)
        line(17, 18, 19, 25, BLACK_POLY, 1)
        # Barrel
        rect(22, 14, 27, 16, DARK_STEEL)
        # Red dot reflex scope
        rect(12, 9, 17, 13, BLACK_POLY)
        rect(16, 10, 17, 12, SCOPE_GLASS)
        # Under-barrel laser
        rect(20, 17, 23, 18, BLACK_POLY)
        rect(24, 17, 25, 18, LASER_RED)

    elif weapon_id == "p90":
        # Compact bullpup ergonomic frame
        rect(5, 13, 23, 21, DARK_STEEL, BLACK_POLY)
        rect(7, 16, 9, 19, BLACK_POLY) # thumbhole
        rect(13, 16, 15, 19, BLACK_POLY) # front grip cutout
        # Top translucent amber 50-round magazine
        rect(8, 11, 20, 13, (215, 145, 45, 255), BLACK_POLY)
        # Top reflex sight rail
        rect(15, 7, 20, 11, BLACK_POLY)
        rect(19, 8, 20, 10, SCOPE_GLASS)
        # Front barrel & built-in laser dot
        rect(23, 14, 26, 16, MID_STEEL)
        rect(23, 17, 25, 18, LASER_RED)

    elif weapon_id == "uzi":
        # Compact Micro UZI T-frame
        rect(9, 12, 22, 17, DARK_STEEL, BLACK_POLY)
        rect(11, 13, 20, 15, MID_STEEL)
        rect(13, 10, 15, 12, BLACK_POLY) # top charging knob
        # Grip with protruding extended magazine
        rect(13, 17, 16, 27, BLACK_POLY)
        rect(14, 22, 15, 27, MID_STEEL)
        # Short barrel & laser
        rect(22, 13, 26, 15, LIGHT_STEEL)
        rect(19, 17, 22, 18, BLACK_POLY)
        rect(23, 17, 24, 18, LASER_RED)

    elif weapon_id == "desert_eagle":
        # Iconic Golden Desert Eagle .50 AE
        rect(9, 11, 25, 17, GOLD_MAIN, BLACK_POLY)
        rect(11, 12, 24, 14, GOLD_HI)
        rect(10, 17, 15, 25, BLACK_POLY) # ergonomic grip
        rect(11, 18, 13, 24, DARK_STEEL)
        rect(15, 17, 18, 19, GOLD_MAIN) # trigger guard
        # Top mini red-dot sight
        rect(11, 8, 15, 11, BLACK_POLY)
        rect(14, 9, 15, 10, SCOPE_GLASS)
        # Under-barrel tactical laser
        rect(19, 17, 23, 19, BLACK_POLY)
        rect(24, 17, 26, 18, LASER_RED)

    elif weapon_id == "glock_18":
        # Tactical blocky Glock-18C with extended mag
        rect(10, 12, 23, 16, DARK_STEEL, BLACK_POLY)
        rect(11, 13, 22, 14, MID_STEEL)
        rect(10, 16, 14, 27, BLACK_POLY) # grip + extended 20rd mag
        rect(11, 22, 13, 27, MID_STEEL)
        # Mini reflex red dot
        rect(11, 9, 14, 12, BLACK_POLY)
        rect(13, 10, 14, 11, LASER_RED)
        # Under-barrel rail laser
        rect(18, 16, 21, 18, BLACK_POLY)
        rect(22, 16, 24, 17, LASER_RED)

    elif weapon_id == "usp_s":
        # Tactical USP-S with long matte black suppressor
        rect(8, 12, 20, 16, MID_STEEL, BLACK_POLY)
        rect(9, 13, 19, 14, LIGHT_STEEL)
        rect(9, 16, 13, 23, BLACK_POLY)
        # Long cylindrical suppressor
        rect(20, 12, 30, 15, BLACK_POLY)
        line(21, 13, 29, 13, DARK_STEEL)
        # Optical sight + under-barrel laser
        rect(10, 9, 14, 12, BLACK_POLY)
        rect(13, 10, 14, 11, SCOPE_GLASS)
        rect(16, 16, 19, 18, BLACK_POLY)
        rect(20, 16, 22, 17, LASER_RED)

    elif weapon_id == "ak47":
        # Classic AK-47 wood & steel + orange bakelite curved magazine
        rect(2, 15, 8, 20, WOOD_DARK, BLACK_POLY)
        rect(3, 16, 7, 18, WOOD_LIGHT)
        rect(8, 13, 19, 18, DARK_STEEL, BLACK_POLY)
        rect(19, 14, 24, 17, WOOD_LIGHT, BLACK_POLY) # wooden handguard
        rect(9, 18, 11, 23, WOOD_DARK) # grip
        # Curved orange-brown bakelite 30rd magazine
        line(15, 18, 18, 26, (195, 88, 34, 255), 3)
        # Barrel & gas tube + front sight
        rect(24, 13, 30, 16, DARK_STEEL)
        rect(28, 11, 29, 14, DARK_STEEL)
        # 3x ACOG Scope
        rect(10, 8, 17, 13, BLACK_POLY)
        rect(16, 9, 17, 11, SCOPE_GLASS)
        # Tactical laser pointer
        rect(23, 17, 26, 18, BLACK_POLY)
        rect(27, 17, 29, 18, LASER_RED)

    elif weapon_id == "m4a1":
        # M4A1-S Tactical Carbine with suppressor & ACOG + PEQ laser
        rect(2, 13, 8, 19, BLACK_POLY) # collapsible stock
        rect(8, 13, 23, 18, DARK_STEEL, BLACK_POLY)
        rect(9, 14, 22, 16, MID_STEEL)
        rect(9, 18, 11, 23, BLACK_POLY) # grip
        rect(14, 18, 17, 25, MID_STEEL, BLACK_POLY) # STANAG mag
        # Silencer barrel
        rect(23, 14, 31, 16, BLACK_POLY)
        # 3x Scope
        rect(10, 8, 18, 13, BLACK_POLY)
        rect(17, 9, 18, 12, SCOPE_GLASS)
        # PEQ-15 Laser Box
        rect(20, 11, 23, 13, TAN_BODY)
        rect(24, 12, 26, 12, LASER_RED)

    elif weapon_id == "spas_12":
        # Heavy SPAS-12 Tactical Shotgun
        rect(2, 14, 8, 19, BLACK_POLY)
        rect(8, 13, 24, 18, DARK_STEEL, BLACK_POLY)
        rect(10, 14, 23, 15, LIGHT_STEEL) # perforated heatshield
        rect(15, 16, 22, 19, BLACK_POLY) # pump forend
        rect(8, 18, 10, 23, BLACK_POLY) # grip
        rect(24, 13, 29, 17, MID_STEEL) # double tube barrel
        # Top holo sight + laser
        rect(11, 9, 16, 13, BLACK_POLY)
        rect(15, 10, 16, 12, LASER_RED)
        rect(24, 17, 27, 18, LASER_RED)

    elif weapon_id == "tactical_ammo_box":
        # Military olive ammo crate with brass bullets & red laser badge
        rect(4, 7, 27, 26, (58, 88, 48, 255), BLACK_POLY)
        rect(5, 8, 26, 11, (75, 112, 62, 255))
        rect(11, 4, 20, 7, DARK_STEEL) # carry handle
        # Gold bullets emblem in center
        for bx in [10, 14, 18, 22]:
            rect(bx, 15, bx+2, 22, GOLD_MAIN)
            rect(bx, 13, bx+2, 15, (210, 110, 45, 255))

    return img

for w in WEAPONS:
    wid = w[0]
    im = draw_gun_texture(wid)
    im.save(os.path.join(assets_dir, 'textures', 'item', f'{wid}.png'))

ammo_im = draw_gun_texture("tactical_ammo_box")
ammo_im.save(os.path.join(assets_dir, 'textures', 'item', 'tactical_ammo_box.png'))

# Mod icon (128x128 showcase with AWP + Crosshair)
icon = Image.new('RGBA', (128, 128), (22, 26, 34, 255))
idraw = ImageDraw.Draw(icon)
idraw.ellipse([12, 12, 116, 116], outline=(255, 45, 45, 220), width=4)
idraw.line([64, 4, 64, 124], fill=(255, 45, 45, 160), width=2)
idraw.line([4, 64, 124, 64], fill=(255, 45, 45, 160), width=2)
awp_big = draw_gun_texture("awp").resize((112, 112), Image.NEAREST)
icon.paste(awp_big, (8, 8), awp_big)
icon.save(os.path.join(assets_dir, 'icon.png'))

# 3. Generate Item Models with 3D Gun Display Transforms
print("Generating item models...")
ALL_ITEM_IDS = [w[0] for w in WEAPONS] + ["tactical_ammo_box"]

for item_id in ALL_ITEM_IDS:
    with open(os.path.join(assets_dir, 'items', f'{item_id}.json'), 'w', encoding='utf-8') as f:
        json.dump({
            "model": {
                "type": "minecraft:model",
                "model": f"mcweapon:item/{item_id}"
            }
        }, f, indent=2)

    if item_id == "tactical_ammo_box":
        model_data = {
            "parent": "minecraft:item/generated",
            "textures": {
                "layer0": f"mcweapon:item/{item_id}"
            }
        }
    else:
        # Custom firearm display so the horizontal gun texture points forward naturally in 1st & 3rd person!
        model_data = {
            "parent": "minecraft:item/generated",
            "textures": {
                "layer0": f"mcweapon:item/{item_id}"
            },
            "display": {
                "thirdperson_righthand": {
                    "rotation": [0, -90, 0],
                    "translation": [0, 2.5, 1.0],
                    "scale": [0.95, 0.95, 0.85]
                },
                "thirdperson_lefthand": {
                    "rotation": [0, 90, 0],
                    "translation": [0, 2.5, 1.0],
                    "scale": [0.95, 0.95, 0.85]
                },
                "firstperson_righthand": {
                    "rotation": [0, -90, 5],
                    "translation": [1.13, 3.2, 1.13],
                    "scale": [0.85, 0.85, 0.85]
                },
                "firstperson_lefthand": {
                    "rotation": [0, 90, -5],
                    "translation": [1.13, 3.2, 1.13],
                    "scale": [0.85, 0.85, 0.85]
                },
                "gui": {
                    "rotation": [0, 0, -25],
                    "translation": [0, 0, 0],
                    "scale": [1.15, 1.15, 1.0]
                }
            }
        }
    with open(os.path.join(assets_dir, 'models', 'item', f'{item_id}.json'), 'w', encoding='utf-8') as f:
        json.dump(model_data, f, indent=2)

# 4. Generate Language Files (zh_cn.json and en_us.json)
print("Generating language files...")
zh_cn = {
    "itemGroup.mcweapon.tab": "现代战术枪械库 (MCWeapon)",
    "item.mcweapon.tactical_ammo_box": "战术高爆弹药箱",
}
en_us = {
    "itemGroup.mcweapon.tab": "Tactical Weapons Arsenal",
    "item.mcweapon.tactical_ammo_box": "Tactical High-Power Ammo Box",
}
for w in WEAPONS:
    wid, zname, ename = w[0], w[1], w[2]
    zh_cn[f"item.mcweapon.{wid}"] = zname
    en_us[f"item.mcweapon.{wid}"] = ename

with open(os.path.join(assets_dir, 'lang', 'zh_cn.json'), 'w', encoding='utf-8') as f:
    json.dump(zh_cn, f, ensure_ascii=False, indent=2)
with open(os.path.join(assets_dir, 'lang', 'en_us.json'), 'w', encoding='utf-8') as f:
    json.dump(en_us, f, ensure_ascii=False, indent=2)

# 5. Generate Crafting Recipes for all 13 Weapons + Ammo Box
print("Generating survival crafting recipes...")
RECIPES = {
    "awp": (["ASA", "III", " R "], {"A": "minecraft:amethyst_shard", "S": "minecraft:spyglass", "I": "minecraft:iron_block", "R": "minecraft:redstone"}),
    "barrett_m82": (["ASA", "NBI", " R "], {"A": "minecraft:amethyst_shard", "S": "minecraft:spyglass", "N": "minecraft:netherite_Scrap", "B": "minecraft:iron_block", "I": "minecraft:obsidian", "R": "minecraft:redstone_block"}),
    "kar98k": ([" SA", "III", " W "], {"S": "minecraft:spyglass", "A": "minecraft:redstone", "I": "minecraft:iron_ingot", "W": "minecraft:oak_planks"}),
    "kriss_vector": ([" R ", "IGI", " C "], {"R": "minecraft:redstone", "I": "minecraft:iron_ingot", "G": "minecraft:gold_ingot", "C": "minecraft:copper_ingot"}),
    "mp5": ([" R ", "III", " C "], {"R": "minecraft:redstone", "I": "minecraft:iron_ingot", "C": "minecraft:coal"}),
    "p90": (["GGG", "IRI", " C "], {"G": "minecraft:glass", "I": "minecraft:iron_ingot", "R": "minecraft:redstone", "C": "minecraft:copper_ingot"}),
    "uzi": ([" R ", "II ", " I "], {"R": "minecraft:redstone", "I": "minecraft:iron_ingot"}),
    "desert_eagle": ([" R ", "GGG", " I "], {"R": "minecraft:redstone", "G": "minecraft:gold_ingot", "I": "minecraft:iron_ingot"}),
    "glock_18": ([" R ", "IC ", " I "], {"R": "minecraft:redstone", "I": "minecraft:iron_ingot", "C": "minecraft:coal"}),
    "usp_s": ([" R ", "IIW", " I "], {"R": "minecraft:redstone", "I": "minecraft:iron_ingot", "W": "minecraft:black_wool"}),
    "ak47": ([" R ", "III", "WCW"], {"R": "minecraft:redstone", "I": "minecraft:iron_ingot", "W": "minecraft:oak_planks", "C": "minecraft:copper_ingot"}),
    "m4a1": ([" A ", "III", " R "], {"A": "minecraft:amethyst_shard", "I": "minecraft:iron_ingot", "R": "minecraft:redstone"}),
    "spas_12": ([" R ", "IIB", " C "], {"R": "minecraft:redstone", "I": "minecraft:iron_ingot", "B": "minecraft:iron_block", "C": "minecraft:copper_ingot"}),
    "tactical_ammo_box": (["III", "GGG", "III"], {"I": "minecraft:iron_ingot", "G": "minecraft:gunpowder"}),
}
# Fix lowercase on netherite_scrap
RECIPES["barrett_m82"] = (["ASA", "NBI", " R "], {"A": "minecraft:amethyst_shard", "S": "minecraft:spyglass", "N": "minecraft:netherite_scrap", "B": "minecraft:iron_block", "I": "minecraft:obsidian", "R": "minecraft:redstone_block"})

for item_id, (pattern, key) in RECIPES.items():
    recipe_json = {
        "type": "minecraft:crafting_shaped",
        "pattern": pattern,
        "key": key,
        "result": {
            "id": f"mcweapon:{item_id}",
            "count": 1
        }
    }
    with open(os.path.join(data_dir, 'recipe', f'{item_id}.json'), 'w', encoding='utf-8') as f:
        json.dump(recipe_json, f, indent=2)

# 6. Generate fabric.mod.json and mcweapon.mixins.json
print("Generating fabric.mod.json and mcweapon.mixins.json...")
fabric_mod_json = {
    "schemaVersion": 1,
    "id": "mcweapon",
    "version": "1.0.0",
    "name": "Tactical Weapons Arsenal (现代战术枪械)",
    "description": "包含狙击枪(AWP/巴雷特/Kar98k)、冲锋枪(Vector/MP5/P90/UZI)、手枪(沙漠之鹰/Glock18/USP-S)、步枪与霰弹枪。配备激光瞄准红点与光学开镜放大，仅对生物实体产生伤害，不破坏任何世界方块。",
    "authors": ["Antigravity"],
    "license": "MIT",
    "icon": "assets/mcweapon/icon.png",
    "environment": "*",
    "entrypoints": {
        "main": [
            "com.mcweapon.McWeaponMod"
        ]
    },
    "mixins": [
        "mcweapon.mixins.json"
    ],
    "depends": {
        "fabricloader": ">=0.19.5",
        "minecraft": ">=26.3",
        "java": ">=25",
        "fabric-api": "*"
    }
}
with open(os.path.join(BUILD_DIR, 'fabric.mod.json'), 'w', encoding='utf-8') as f:
    json.dump(fabric_mod_json, f, ensure_ascii=False, indent=2)

mixins_json = {
    "required": True,
    "package": "com.mcweapon.mixin",
    "compatibilityLevel": "JAVA_25",
    "mixins": [
        "PlayerScopeMixin"
    ],
    "injectors": {
        "defaultRequire": 1
    }
}
with open(os.path.join(BUILD_DIR, 'mcweapon.mixins.json'), 'w', encoding='utf-8') as f:
    json.dump(mixins_json, f, indent=2)

# 7. Write Java Source Code
print("Writing Java sources...")
src_java_dir = os.path.join(BUILD_DIR, 'src', 'com', 'mcweapon')
src_mixin_dir = os.path.join(src_java_dir, 'mixin')
make_dirs(src_java_dir)
make_dirs(src_mixin_dir)

weapon_spec_java = '''package com.mcweapon;

import net.minecraft.world.item.Rarity;

public record WeaponSpec(
    String id,
    String zhName,
    String enName,
    String categoryId,
    String zhCategory,
    float damage,
    int pellets,
    int fireIntervalTicks,
    int magazineSize,
    int reloadTicks,
    double range,
    float hipSpread,
    float scopedSpread,
    float zoomLevel,
    float headshotMultiplier,
    int piercing,
    boolean silenced,
    String soundKey,
    Rarity rarity
) {
    public float shotsPerSecond() {
        return 20.0f / Math.max(1, fireIntervalTicks);
    }

    public float theoreticalDps() {
        return damage * pellets * shotsPerSecond();
    }
}
'''

player_scope_mixin_java = '''package com.mcweapon.mixin;

import com.mcweapon.GunItem;
import net.minecraft.world.entity.player.Player;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(Player.class)
public class PlayerScopeMixin {
    @Inject(method = "isScoping", at = @At("HEAD"), cancellable = true)
    private void mcweapon$onIsScoping(CallbackInfoReturnable<Boolean> cir) {
        Player self = (Player) (Object) this;
        if (GunItem.isPlayerScopingWithGun(self)) {
            cir.setReturnValue(true);
        }
    }
}
'''

gun_item_java = '''package com.mcweapon;

import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Holder;
import net.minecraft.core.component.DataComponents;
import net.minecraft.core.particles.DustParticleOptions;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.Identifier;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.util.Mth;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.ai.attributes.AttributeInstance;
import net.minecraft.world.entity.ai.attributes.AttributeModifier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.decoration.ArmorStand;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.ItemUseAnimation;
import net.minecraft.world.item.TooltipFlag;
import net.minecraft.world.item.component.CustomData;
import net.minecraft.world.item.component.TooltipDisplay;
import net.minecraft.world.item.context.UseOnContext;
import net.minecraft.world.level.ClipContext;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.HitResult;
import net.minecraft.world.phys.Vec3;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.Consumer;

public class GunItem extends Item {
    public static final Identifier SCOPE_SPEED_MODIFIER_ID = Identifier.fromNamespaceAndPath(McWeaponMod.MOD_ID, "scope_zoom_fov");
    public static final DustParticleOptions LASER_DOT_BRIGHT = new DustParticleOptions(0xFF0000, 0.72f);
    public static final DustParticleOptions LASER_DOT_SCOPED = new DustParticleOptions(0xFF1111, 0.50f);
    public static final DustParticleOptions LASER_BEAM_FINE = new DustParticleOptions(0xFF2222, 0.30f);
    public static final DustParticleOptions BULLET_TRACER_GOLD = new DustParticleOptions(0xFFCC33, 0.42f);

    private static final Map<UUID, Long> LAST_FIRE_TICK = new ConcurrentHashMap<>();
    private static final Map<UUID, Boolean> PREV_SCOPE_STATE = new ConcurrentHashMap<>();

    private final WeaponSpec spec;
    private final SoundEvent customFireSound;

    public GunItem(WeaponSpec spec, SoundEvent customFireSound, Item.Properties properties) {
        super(properties);
        this.spec = spec;
        this.customFireSound = customFireSound;
    }

    public WeaponSpec getSpec() {
        return this.spec;
    }

    // === 1. STRICT ZERO BLOCK DESTRUCTION ===
    @Override
    public boolean canDestroyBlock(ItemStack stack, BlockState state, Level level, BlockPos pos, LivingEntity entity) {
        return false;
    }

    @Override
    public float getDestroySpeed(ItemStack stack, BlockState state) {
        return 0.0F;
    }

    @Override
    public boolean mineBlock(ItemStack stack, Level level, BlockState state, BlockPos pos, LivingEntity miningEntity) {
        return false;
    }

    @Override
    public InteractionResult useOn(UseOnContext context) {
        Player player = context.getPlayer();
        if (player == null) {
            return InteractionResult.PASS;
        }
        return this.use(context.getLevel(), player, context.getHand());
    }

    // === 2. CONTINUOUS FULL-AUTO / SEMI-AUTO SHOOTING ===
    @Override
    public int getUseDuration(ItemStack stack, LivingEntity user) {
        return 72000;
    }

    @Override
    public ItemUseAnimation getUseAnimation(ItemStack stack) {
        return ItemUseAnimation.NONE;
    }

    @Override
    public InteractionResult use(Level level, Player player, InteractionHand hand) {
        ItemStack stack = player.getItemInHand(hand);
        player.startUsingItem(hand);
        if (level instanceof ServerLevel serverLevel) {
            tryShoot(serverLevel, player, stack);
        }
        return InteractionResult.CONSUME;
    }

    @Override
    public void onUseTick(Level level, LivingEntity user, ItemStack stack, int remainingUseDuration) {
        if (level instanceof ServerLevel serverLevel && user instanceof Player player) {
            tryShoot(serverLevel, player, stack);
        }
    }

    // === 3. MAGAZINE & SCOPE NBT HELPERS ===
    public static CompoundTag getTag(ItemStack stack) {
        CustomData data = stack.getOrDefault(DataComponents.CUSTOM_DATA, CustomData.EMPTY);
        return data.copyTag();
    }

    public static void saveTag(ItemStack stack, CompoundTag tag) {
        stack.set(DataComponents.CUSTOM_DATA, CustomData.of(tag));
    }

    public int getAmmo(ItemStack stack) {
        CompoundTag tag = getTag(stack);
        if (!tag.contains("ammo")) {
            return spec.magazineSize();
        }
        return tag.getIntOr("ammo", spec.magazineSize());
    }

    public void setAmmo(ItemStack stack, int ammo) {
        CompoundTag tag = getTag(stack);
        tag.putInt("ammo", Mth.clamp(ammo, 0, spec.magazineSize()));
        saveTag(stack, tag);
    }

    public boolean isReloading(ItemStack stack, long gameTime) {
        CompoundTag tag = getTag(stack);
        long reloadEnd = tag.getLongOr("reloadEnd", 0L);
        return reloadEnd > gameTime;
    }

    public long getReloadEnd(ItemStack stack) {
        return getTag(stack).getLongOr("reloadEnd", 0L);
    }

    public static boolean isScopeToggled(ItemStack stack) {
        if (stack.isEmpty() || !(stack.getItem() instanceof GunItem)) {
            return false;
        }
        return getTag(stack).getBooleanOr("scoped", false);
    }

    public static void toggleScopeLock(ServerLevel level, Player player, ItemStack stack) {
        if (!(stack.getItem() instanceof GunItem gun)) return;
        CompoundTag tag = getTag(stack);
        boolean next = !tag.getBooleanOr("scoped", false);
        tag.putBoolean("scoped", next);
        saveTag(stack, tag);

        level.playSound(null, player.getX(), player.getY(), player.getZ(),
            next ? SoundEvents.SPYGLASS_USE : SoundEvents.SPYGLASS_STOP_USING,
            SoundSource.PLAYERS, 1.0f, next ? 1.15f : 0.95f);

        if (player instanceof ServerPlayer sp) {
            String stateText = next
                ? "§b§l[🔍 光学倍镜已开启 " + String.format("%.1fx", gun.spec.zoomLevel()) + "]"
                : "§7[🎯 光学倍镜已关闭 - 腰射红点模式]";
            sp.sendOverlayMessage(Component.literal(stateText));
        }
    }

    public static boolean isPlayerScopingWithGun(Player player) {
        if (player == null) return false;
        ItemStack main = player.getMainHandItem();
        ItemStack off = player.getOffhandItem();
        ItemStack gunStack = (main.getItem() instanceof GunItem) ? main : ((off.getItem() instanceof GunItem) ? off : ItemStack.EMPTY);
        if (gunStack.isEmpty()) return false;
        return player.isShiftKeyDown() || isScopeToggled(gunStack);
    }

    public void startReload(ServerLevel level, Player player, ItemStack stack) {
        long now = level.getGameTime();
        if (isReloading(stack, now)) return;
        int currentAmmo = getAmmo(stack);
        if (currentAmmo >= spec.magazineSize()) return;

        boolean hasAmmoBox = hasTacticalAmmoBox(player);
        int effectiveReloadTicks = hasAmmoBox ? Math.max(8, spec.reloadTicks() / 2) : spec.reloadTicks();

        CompoundTag tag = getTag(stack);
        tag.putLong("reloadStart", now);
        tag.putLong("reloadEnd", now + effectiveReloadTicks);
        saveTag(stack, tag);

        level.playSound(null, player.getX(), player.getY(), player.getZ(),
            SoundEvents.IRON_DOOR_OPEN, SoundSource.PLAYERS, 0.7f, 1.45f);
        level.playSound(null, player.getX(), player.getY(), player.getZ(),
            SoundEvents.LEVER_CLICK, SoundSource.PLAYERS, 0.8f, 0.85f);

        if (player instanceof ServerPlayer sp) {
            sp.sendOverlayMessage(Component.literal("§e⟳ 正在换弹 [" + spec.zhName() + "] ... " + String.format("%.1fs", effectiveReloadTicks / 20.0f)));
        }
    }

    public static boolean hasTacticalAmmoBox(Player player) {
        for (int i = 0; i < player.getInventory().getContainerSize(); i++) {
            ItemStack s = player.getInventory().getItem(i);
            if (!s.isEmpty() && s.is(McWeaponMod.TACTICAL_AMMO_BOX)) {
                return true;
            }
        }
        return false;
    }

    // === 4. CORE FIRING & HITSCAN ENTITY-ONLY DAMAGE ===
    public void tryShoot(ServerLevel level, Player player, ItemStack stack) {
        long now = level.getGameTime();

        // Check if reload just finished
        CompoundTag tag = getTag(stack);
        long reloadEnd = tag.getLongOr("reloadEnd", 0L);
        if (reloadEnd > 0L) {
            if (now < reloadEnd) {
                return; // Still reloading
            } else {
                tag.remove("reloadStart");
                tag.remove("reloadEnd");
                tag.putInt("ammo", spec.magazineSize());
                saveTag(stack, tag);
            }
        }

        // Check fire rate interval
        long lastFire = LAST_FIRE_TICK.getOrDefault(player.getUUID(), -9999L);
        if (now - lastFire < spec.fireIntervalTicks()) {
            return;
        }

        int ammo = getAmmo(stack);
        if (ammo <= 0) {
            level.playSound(null, player.getX(), player.getY(), player.getZ(),
                SoundEvents.DISPENSER_FAIL, SoundSource.PLAYERS, 0.8f, 1.5f);
            startReload(level, player, stack);
            return;
        }

        // Consume 1 round & record fire tick
        LAST_FIRE_TICK.put(player.getUUID(), now);
        int remaining = ammo - 1;
        setAmmo(stack, remaining);

        if (spec.fireIntervalTicks() >= 8) {
            player.getCooldowns().addCooldown(stack, spec.fireIntervalTicks());
        }

        boolean scoped = isPlayerScopingWithGun(player);
        boolean hasAmmoBox = hasTacticalAmmoBox(player);
        float damageBonus = hasAmmoBox ? 1.15f : 1.0f;

        // Play custom + layered gunshot audio
        playGunshotSound(level, player);

        // Muzzle flash particles
        Vec3 eye = player.getEyePosition();
        Vec3 look = player.getLookAngle();
        Vec3 right = look.cross(new Vec3(0, 1, 0)).normalize();
        Vec3 muzzle = eye.add(look.scale(0.65)).add(right.scale(scoped ? 0.0 : 0.22)).add(0, -0.12, 0);
        if (!spec.silenced()) {
            level.sendParticles(ParticleTypes.SMOKE, muzzle.x, muzzle.y, muzzle.z, 2, 0.03, 0.03, 0.03, 0.01);
            if (spec.damage() >= 18.0f || spec.pellets() > 1) {
                level.sendParticles(ParticleTypes.FLAME, muzzle.x, muzzle.y, muzzle.z, 2, 0.02, 0.02, 0.02, 0.01);
            }
        }

        float spread = scoped ? spec.scopedSpread() : spec.hipSpread();
        boolean anyHit = false;
        boolean anyHeadshot = false;
        LivingEntity lastTargetHit = null;
        float totalDealt = 0.0f;

        for (int p = 0; p < spec.pellets(); p++) {
            Vec3 shotDir = applySpread(look, spread, level);
            ShotOutcome outcome = fireRay(level, player, eye, muzzle, shotDir, damageBonus);
            if (outcome.hitEntity != null) {
                anyHit = true;
                anyHeadshot |= outcome.headshot;
                lastTargetHit = outcome.hitEntity;
                totalDealt += outcome.damageDealt;
            }
        }

        if (anyHit && player instanceof ServerPlayer sp) {
            // Play hit confirmation sound to shooter
            sp.level().playSound(null, sp.getX(), sp.getY(), sp.getZ(),
                anyHeadshot ? SoundEvents.ARROW_HIT_PLAYER : SoundEvents.CROSSBOW_HIT,
                SoundSource.PLAYERS, 0.9f, anyHeadshot ? 1.25f : 1.0f);

            float remHp = Math.max(0.0f, lastTargetHit.getHealth());
            String headTag = anyHeadshot ? " §6§l[💥爆头暴击!]" : "";
            sp.sendOverlayMessage(Component.literal(
                "§c✦ 命中 " + lastTargetHit.getName().getString() +
                " §f(-" + String.format("%.1f", totalDealt) + "❤)" + headTag +
                " §7| 剩余生命: §a" + String.format("%.1f", remHp) + "❤" +
                " §7| 弹匣: §e" + remaining + "/" + spec.magazineSize()
            ));
        }

        // Auto-reload when magazine hits 0
        if (remaining <= 0) {
            startReload(level, player, stack);
        }
    }

    private record ShotOutcome(LivingEntity hitEntity, boolean headshot, float damageDealt) {}

    private record CandidateHit(LivingEntity entity, Vec3 hitPos, double distSqr) {}

    private ShotOutcome fireRay(ServerLevel level, Player shooter, Vec3 start, Vec3 muzzle, Vec3 dir, float damageBonus) {
        Vec3 maxEnd = start.add(dir.scale(spec.range()));

        // 1. Check world block collision (stops bullet at solid blocks, ZERO block damage!)
        BlockHitResult blockHit = level.clip(new ClipContext(
            start, maxEnd, ClipContext.Block.COLLIDER, ClipContext.Fluid.NONE, shooter
        ));

        Vec3 effectiveEnd = maxEnd;
        if (blockHit.getType() != HitResult.Type.MISS) {
            effectiveEnd = blockHit.getLocation();
            // Spawn non-destructive spark on block surface
            Vec3 sparkPos = effectiveEnd.subtract(dir.scale(0.05));
            level.sendParticles(ParticleTypes.CRIT, sparkPos.x, sparkPos.y, sparkPos.z, 2, 0.02, 0.02, 0.02, 0.02);
        }

        // 2. Find all LivingEntities along [start, effectiveEnd] (strictly excluding ArmorStand & non-living entities!)
        AABB searchBox = new AABB(start, effectiveEnd).inflate(1.25);
        List<Entity> candidates = level.getEntities(shooter, searchBox, e ->
            e instanceof LivingEntity &&
            !(e instanceof ArmorStand) &&
            e != shooter &&
            e.isAlive() &&
            !e.isSpectator() &&
            e.isPickable()
        );

        List<CandidateHit> hits = new ArrayList<>();
        for (Entity e : candidates) {
            LivingEntity living = (LivingEntity) e;
            AABB targetBox = living.getBoundingBox().inflate(0.24);
            if (targetBox.contains(start)) {
                hits.add(new CandidateHit(living, start, 0.0));
            } else {
                Optional<Vec3> clipHit = targetBox.clip(start, effectiveEnd);
                if (clipHit.isPresent()) {
                    Vec3 hp = clipHit.get();
                    double d2 = start.distanceToSqr(hp);
                    if (d2 <= start.distanceToSqr(effectiveEnd)) {
                        hits.add(new CandidateHit(living, hp, d2));
                    }
                }
            }
        }

        hits.sort(Comparator.comparingDouble(CandidateHit::distSqr));

        // Render bullet tracer up to first target or block
        Vec3 tracerEnd = (!hits.isEmpty() && spec.piercing() == 1) ? hits.get(0).hitPos() : effectiveEnd;
        spawnBulletTracer(level, muzzle, tracerEnd);

        if (hits.isEmpty()) {
            return new ShotOutcome(null, false, 0.0f);
        }

        int pierced = 0;
        LivingEntity primaryHit = null;
        boolean anyHead = false;
        float totalDamage = 0.0f;

        DamageSource dmgSource = level.damageSources().playerAttack(shooter);

        for (CandidateHit ch : hits) {
            if (pierced >= spec.piercing()) break;
            LivingEntity target = ch.entity();
            Vec3 hitPos = ch.hitPos();

            boolean isHeadshot = hitPos.y >= (target.getEyeY() - 0.34);
            float dmg = spec.damage() * damageBonus * (isHeadshot ? spec.headshotMultiplier() : 1.0f);
            // Slight falloff on subsequent pierced targets
            if (pierced > 0) {
                dmg *= Math.pow(0.8, pierced);
            }

            // Reset hurt invulnerability frames so high-ROF SMGs & multi-pellet shotguns deal full damage!
            target.setInvulnerableTime(0);
            boolean hurtOk = target.hurtServer(level, dmgSource, dmg);
            if (hurtOk) {
                // Subtle tactical knockback without launching mobs into orbit
                Vec3 kb = dir.scale(spec.damage() >= 25.0f ? 0.35 : 0.08);
                target.addDeltaMovement(new Vec3(kb.x, 0.02, kb.z));

                level.sendParticles(
                    isHeadshot ? ParticleTypes.ENCHANTED_HIT : ParticleTypes.DAMAGE_INDICATOR,
                    hitPos.x, hitPos.y, hitPos.z,
                    isHeadshot ? 8 : 3,
                    0.12, 0.12, 0.12, 0.08
                );

                primaryHit = target;
                anyHead |= isHeadshot;
                totalDamage += dmg;
                pierced++;
            }
        }

        return new ShotOutcome(primaryHit, anyHead, totalDamage);
    }

    private void spawnBulletTracer(ServerLevel level, Vec3 from, Vec3 to) {
        double dist = from.distanceTo(to);
        if (dist < 0.5) return;
        Vec3 dir = to.subtract(from).normalize();
        double step = spec.categoryId().equals("SNIPER") ? 1.8 : 3.2;
        double maxDraw = Math.min(dist, 90.0);
        for (double d = 0.8; d < maxDraw; d += step) {
            Vec3 pt = from.add(dir.scale(d));
            if (spec.categoryId().equals("SNIPER")) {
                level.sendParticles(ParticleTypes.CRIT, true, true, pt.x, pt.y, pt.z, 1, 0, 0, 0, 0);
            } else {
                level.sendParticles(BULLET_TRACER_GOLD, true, false, pt.x, pt.y, pt.z, 1, 0, 0, 0, 0);
            }
        }
    }

    private Vec3 applySpread(Vec3 look, float spread, ServerLevel level) {
        if (spread <= 0.0001f) return look;
        double rx = (level.getRandom().nextGaussian()) * spread;
        double ry = (level.getRandom().nextGaussian()) * spread;
        double rz = (level.getRandom().nextGaussian()) * spread;
        return look.add(rx, ry, rz).normalize();
    }

    private void playGunshotSound(ServerLevel level, Player shooter) {
        float pitch = 0.96f + level.getRandom().nextFloat() * 0.08f;
        float volume = spec.silenced() ? 0.8f : (spec.categoryId().equals("SNIPER") ? 2.2f : 1.4f);

        // Play custom synthesized .ogg gunshot sound
        if (this.customFireSound != null) {
            level.playSound(null, shooter.getX(), shooter.getY(), shooter.getZ(),
                this.customFireSound, SoundSource.PLAYERS, volume, pitch);
        }

        // Layer crisp vanilla acoustics so even un-synced clients hear punchy gunfire
        if (spec.silenced()) {
            level.playSound(null, shooter.getX(), shooter.getY(), shooter.getZ(),
                SoundEvents.SNOWBALL_THROW, SoundSource.PLAYERS, 0.7f, 0.6f);
            level.playSound(null, shooter.getX(), shooter.getY(), shooter.getZ(),
                SoundEvents.IRON_DOOR_CLOSE, SoundSource.PLAYERS, 0.45f, 1.9f);
        } else if (spec.categoryId().equals("SNIPER")) {
            level.playSound(null, shooter.getX(), shooter.getY(), shooter.getZ(),
                SoundEvents.FIREWORK_ROCKET_LARGE_BLAST, SoundSource.PLAYERS, 1.8f, 0.65f);
            level.playSound(null, shooter.getX(), shooter.getY(), shooter.getZ(),
                SoundEvents.GENERIC_EXPLODE.value(), SoundSource.PLAYERS, 0.7f, 1.55f);
        } else if (spec.categoryId().equals("SHOTGUN")) {
            level.playSound(null, shooter.getX(), shooter.getY(), shooter.getZ(),
                SoundEvents.GENERIC_EXPLODE.value(), SoundSource.PLAYERS, 0.85f, 1.35f);
            level.playSound(null, shooter.getX(), shooter.getY(), shooter.getZ(),
                SoundEvents.FIREWORK_ROCKET_BLAST, SoundSource.PLAYERS, 1.4f, 0.75f);
        } else if (spec.id().equals("desert_eagle") || spec.id().equals("ak47")) {
            level.playSound(null, shooter.getX(), shooter.getY(), shooter.getZ(),
                SoundEvents.FIREWORK_ROCKET_BLAST, SoundSource.PLAYERS, 1.3f, 0.85f);
        } else {
            level.playSound(null, shooter.getX(), shooter.getY(), shooter.getZ(),
                SoundEvents.FIREWORK_ROCKET_BLAST, SoundSource.PLAYERS, 0.9f, 1.35f);
        }
    }

    // === 5. LASER SIGHT RED DOT, SCOPE ZOOM & HUD TICK ===
    @Override
    public void inventoryTick(ItemStack stack, ServerLevel level, Entity entity, EquipmentSlot slot) {
        if (!(entity instanceof ServerPlayer player)) return;

        boolean held = (slot == EquipmentSlot.MAINHAND || slot == EquipmentSlot.OFFHAND);
        if (!held) return;

        long now = level.getGameTime();

        // Check reload completion
        CompoundTag tag = getTag(stack);
        long reloadEnd = tag.getLongOr("reloadEnd", 0L);
        if (reloadEnd > 0L && now >= reloadEnd) {
            tag.remove("reloadStart");
            tag.remove("reloadEnd");
            tag.putInt("ammo", spec.magazineSize());
            saveTag(stack, tag);
            level.playSound(null, player.getX(), player.getY(), player.getZ(),
                SoundEvents.IRON_DOOR_CLOSE, SoundSource.PLAYERS, 0.8f, 1.5f);
            player.sendOverlayMessage(Component.literal("§a✔ [" + spec.zhName() + "] 弹匣装填完毕! (" + spec.magazineSize() + "/" + spec.magazineSize() + ")"));
        }

        // Scope Zoom transition sounds & speed/FOV attribute sync
        boolean scoped = isPlayerScopingWithGun(player);
        boolean wasScoped = PREV_SCOPE_STATE.getOrDefault(player.getUUID(), false);
        if (scoped != wasScoped) {
            PREV_SCOPE_STATE.put(player.getUUID(), scoped);
            level.playSound(null, player.getX(), player.getY(), player.getZ(),
                scoped ? SoundEvents.SPYGLASS_USE : SoundEvents.SPYGLASS_STOP_USING,
                SoundSource.PLAYERS, 0.8f, scoped ? 1.15f : 0.95f);
        }
        applyScopeAttribute(player, scoped, spec.zoomLevel());

        // Render Laser Sight Red Dot & Beam every tick for mainhand gun
        if (slot == EquipmentSlot.MAINHAND || !(player.getMainHandItem().getItem() instanceof GunItem)) {
            renderLaserSightAndHud(level, player, stack, scoped, now);
        }
    }

    private void renderLaserSightAndHud(ServerLevel level, ServerPlayer player, ItemStack stack, boolean scoped, long now) {
        Vec3 eye = player.getEyePosition();
        Vec3 look = player.getLookAngle();
        double laserRange = Math.min(spec.range(), 100.0);
        Vec3 maxEnd = eye.add(look.scale(laserRange));

        BlockHitResult blockHit = level.clip(new ClipContext(
            eye, maxEnd, ClipContext.Block.COLLIDER, ClipContext.Fluid.NONE, player
        ));
        Vec3 laserEnd = (blockHit.getType() != HitResult.Type.MISS)
            ? blockHit.getLocation().subtract(look.scale(0.06))
            : maxEnd;
        double closestDistSqr = eye.distanceToSqr(laserEnd);

        // Check if laser is pointing at any LivingEntity
        AABB searchBox = new AABB(eye, laserEnd).inflate(1.0);
        List<Entity> entities = level.getEntities(player, searchBox, e ->
            e instanceof LivingEntity &&
            !(e instanceof ArmorStand) &&
            e != player &&
            e.isAlive() &&
            !e.isSpectator() &&
            e.isPickable()
        );

        LivingEntity lockedTarget = null;
        boolean lockedHeadshot = false;
        for (Entity e : entities) {
            LivingEntity living = (LivingEntity) e;
            Optional<Vec3> hitOpt = living.getBoundingBox().inflate(0.22).clip(eye, laserEnd);
            if (hitOpt.isPresent()) {
                double d2 = eye.distanceToSqr(hitOpt.get());
                if (d2 < closestDistSqr) {
                    closestDistSqr = d2;
                    laserEnd = hitOpt.get();
                    lockedTarget = living;
                    lockedHeadshot = laserEnd.y >= (living.getEyeY() - 0.34);
                }
            }
        }

        // 1. Spawn Bright Red Laser Dot at exact target point (visible up to 100+ blocks!)
        DustParticleOptions dotParticle = scoped ? LASER_DOT_SCOPED : LASER_DOT_BRIGHT;
        level.sendParticles(dotParticle, true, true,
            laserEnd.x, laserEnd.y, laserEnd.z,
            lockedTarget != null ? 3 : 2,
            0.01, 0.01, 0.01, 0.0);

        // 2. Spawn subtle tactical red laser beam from gun barrel towards target
        Vec3 right = look.cross(new Vec3(0, 1, 0)).normalize();
        Vec3 barrelStart = eye.add(look.scale(0.8)).add(right.scale(scoped ? 0.08 : 0.24)).add(0, -0.14, 0);
        double totalDist = Math.sqrt(closestDistSqr);
        double beamDrawDist = Math.min(totalDist, 24.0);
        if (beamDrawDist > 1.2) {
            Vec3 beamVec = laserEnd.subtract(barrelStart);
            double beamLen = beamVec.length();
            if (beamLen > 0.5) {
                Vec3 beamDir = beamVec.normalize();
                for (double d = 1.2; d < Math.min(beamLen, 22.0); d += 2.2) {
                    Vec3 bp = barrelStart.add(beamDir.scale(d));
                    level.sendParticles(LASER_BEAM_FINE, true, false, bp.x, bp.y, bp.z, 1, 0, 0, 0, 0);
                }
            }
        }

        // 3. Periodic Tactical HUD Overlay (every 4 ticks if not reloading)
        if (now % 4 == 0 && !isReloading(stack, now)) {
            int ammo = getAmmo(stack);
            String scopeBadge = scoped
                ? "§b[🔍开镜 " + String.format("%.1fx", spec.zoomLevel()) + "]"
                : "§7[腰射红点]";
            String targetBadge;
            if (lockedTarget != null) {
                String headHint = lockedHeadshot ? " §6[★爆头点]" : "";
                targetBadge = " §c| 🔴锁定: §f" + lockedTarget.getName().getString() +
                    " §c(" + String.format("%.1f", lockedTarget.getHealth()) + "❤ | " +
                    String.format("%.1fm", totalDist) + ")" + headHint;
            } else {
                targetBadge = " §8| 激光测距: " + String.format("%.1fm", totalDist);
            }

            player.sendOverlayMessage(Component.literal(
                "§6[" + spec.zhName() + "] §e弹匣: " + ammo + "/" + spec.magazineSize() + " " +
                scopeBadge + targetBadge
            ));
        }
    }

    public static void applyScopeAttribute(ServerPlayer player, boolean scoped, float zoomLevel) {
        AttributeInstance speedAttr = player.getAttribute(Attributes.MOVEMENT_SPEED);
        if (speedAttr == null) return;
        if (scoped) {
            // Negative speed modifier scales FOV zoom and steadies movement while aiming down sights
            double amount = -Mth.clamp(0.15 + (zoomLevel / 18.0), 0.20, 0.65);
            speedAttr.addOrUpdateTransientModifier(new AttributeModifier(
                SCOPE_SPEED_MODIFIER_ID, amount, AttributeModifier.Operation.ADD_MULTIPLIED_TOTAL
            ));
        } else {
            if (speedAttr.hasModifier(SCOPE_SPEED_MODIFIER_ID)) {
                speedAttr.removeModifier(SCOPE_SPEED_MODIFIER_ID);
            }
        }
    }

    // === 6. DURABILITY BAR FOR MAGAZINE & RELOAD PROGRESS ===
    @Override
    public boolean isBarVisible(ItemStack stack) {
        return true;
    }

    @Override
    public int getBarWidth(ItemStack stack) {
        CompoundTag tag = getTag(stack);
        long reloadStart = tag.getLongOr("reloadStart", 0L);
        long reloadEnd = tag.getLongOr("reloadEnd", 0L);
        if (reloadEnd > reloadStart) {
            // Show full bar or animated bar
            return 13;
        }
        int ammo = getAmmo(stack);
        return Math.round(13.0f * ammo / Math.max(1, spec.magazineSize()));
    }

    @Override
    public int getBarColor(ItemStack stack) {
        float ratio = (float) getAmmo(stack) / Math.max(1, spec.magazineSize());
        return Mth.hsvToRgb(Math.max(0.0F, ratio) / 3.0F, 1.0F, 1.0F);
    }

    // === 7. RICH WEAPON STATS TOOLTIP ===
    @Override
    public void appendHoverText(ItemStack stack, Item.TooltipContext context, TooltipDisplay display, Consumer<Component> tooltipAdder, TooltipFlag flag) {
        int ammo = getAmmo(stack);
        String dmgStr = spec.pellets() > 1
            ? String.format("%.1f × %d弹丸 (满伤 %.1f)", spec.damage(), spec.pellets(), spec.damage() * spec.pellets())
            : String.format("%.1f (爆头 %.1fx = %.1f)", spec.damage(), spec.headshotMultiplier(), spec.damage() * spec.headshotMultiplier());

        tooltipAdder.accept(Component.literal("§7类型: §b" + spec.zhCategory() + " §8| §7弹匣: §e" + ammo + "/" + spec.magazineSize()));
        tooltipAdder.accept(Component.literal("§7单发伤害: §c" + dmgStr));
        tooltipAdder.accept(Component.literal(String.format("§7射速: §a%.1f 发/秒 §8(理论秒伤 %.0f) §8| §7有效射程: §f%.0fm", spec.shotsPerSecond(), spec.theoreticalDps(), spec.range())));
        tooltipAdder.accept(Component.literal(String.format("§7瞄准系统: §c激光红点瞄准器 §7+ §b%.1fx 光学变焦倍镜", spec.zoomLevel())));
        tooltipAdder.accept(Component.literal("§a✔ 安全弹道: 仅对生物实体产生伤害，绝不破坏世界方块"));
        tooltipAdder.accept(Component.literal("§8操作: [按住右键]射击 | [按住Shift或左键]开镜放大 | [F键]换弹"));
    }
}
'''

mcweapon_mod_java = '''package com.mcweapon;

import com.mojang.brigadier.arguments.StringArgumentType;
import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.command.v2.CommandRegistrationCallback;
import net.fabricmc.fabric.api.creativetab.v1.CreativeModeTabEvents;
import net.fabricmc.fabric.api.creativetab.v1.FabricCreativeModeTab;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.fabricmc.fabric.api.event.player.AttackBlockCallback;
import net.fabricmc.fabric.api.event.player.AttackEntityCallback;
import net.minecraft.commands.Commands;
import net.minecraft.core.Registry;
import net.minecraft.core.component.DataComponents;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.Identifier;
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.decoration.ArmorStand;
import net.minecraft.world.item.CreativeModeTab;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Rarity;
import net.minecraft.world.item.component.UseEffects;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public class McWeaponMod implements ModInitializer {
    public static final String MOD_ID = "mcweapon";
    public static final Map<String, GunItem> GUN_ITEMS = new LinkedHashMap<>();
    public static final List<Item> ALL_ITEMS = new ArrayList<>();
    public static final Map<String, SoundEvent> SOUND_EVENTS = new LinkedHashMap<>();

    public static Item TACTICAL_AMMO_BOX;

    @Override
    public void onInitialize() {
        // 1. Register Custom Gunshot SoundEvents
        String[] soundKeys = {
            "sniper_heavy", "sniper_awp", "smg_fast", "smg_shot",
            "pistol_heavy", "pistol_shot", "silenced_shot", "rifle_heavy", "shotgun_blast"
        };
        for (String sk : soundKeys) {
            Identifier sid = Identifier.fromNamespaceAndPath(MOD_ID, "gun." + sk);
            SoundEvent se = SoundEvent.createVariableRangeEvent(sid);
            Registry.register(BuiltInRegistries.SOUND_EVENT, sid, se);
            SOUND_EVENTS.put(sk, se);
        }

        // 2. Register All 13 Iconic Firearms
        List<WeaponSpec> specs = List.of(
            // Snipers
            new WeaponSpec("awp", "AWP 极地狙击步枪", "AWP Sniper Rifle", "SNIPER", "狙击步枪", 38.0f, 1, 30, 10, 46, 120.0, 0.035f, 0.0005f, 8.0f, 1.8f, 2, false, "sniper_awp", Rarity.EPIC),
            new WeaponSpec("barrett_m82", "巴雷特 M82A1 重型反器材狙击枪", "Barrett M82A1 .50 BMG", "SNIPER", "反器材重狙", 55.0f, 1, 40, 10, 56, 140.0, 0.045f, 0.0005f, 10.0f, 1.8f, 4, false, "sniper_heavy", Rarity.EPIC),
            new WeaponSpec("kar98k", "Kar98k 经典毛瑟狙击步枪", "Karabiner 98k Sniper", "SNIPER", "栓动狙击枪", 28.0f, 1, 22, 5, 38, 105.0, 0.025f, 0.0008f, 6.0f, 2.0f, 2, false, "sniper_awp", Rarity.RARE),

            // SMGs
            new WeaponSpec("kriss_vector", "KRISS Vector 维克托短剑冲锋枪", "KRISS Vector .45 ACP", "SMG", "高射速冲锋枪", 5.5f, 1, 1, 33, 26, 48.0, 0.032f, 0.005f, 1.6f, 1.5f, 1, false, "smg_fast", Rarity.RARE),
            new WeaponSpec("mp5", "HK MP5A5 战术冲锋枪", "HK MP5A5 Tactical SMG", "SMG", "战术冲锋枪", 7.0f, 1, 2, 30, 28, 56.0, 0.024f, 0.004f, 2.0f, 1.5f, 1, false, "smg_shot", Rarity.RARE),
            new WeaponSpec("p90", "FN P90 突击冲锋枪", "FN P90 PDW", "SMG", "大弹匣冲锋枪", 6.5f, 1, 2, 50, 34, 58.0, 0.028f, 0.0045f, 2.0f, 1.5f, 2, false, "smg_shot", Rarity.RARE),
            new WeaponSpec("uzi", "Micro UZI 乌兹微型冲锋枪", "Micro UZI SMG", "SMG", "微型冲锋枪", 5.0f, 1, 1, 32, 24, 42.0, 0.038f, 0.007f, 1.5f, 1.4f, 1, false, "smg_fast", Rarity.UNCOMMON),

            // Pistols
            new WeaponSpec("desert_eagle", "沙漠之鹰 .50 AE 重型手枪", "Desert Eagle .50 AE", "PISTOL", "重型手枪", 19.0f, 1, 9, 7, 26, 68.0, 0.022f, 0.002f, 2.2f, 1.75f, 2, false, "pistol_heavy", Rarity.RARE),
            new WeaponSpec("glock_18", "格洛克 18C 全自动战术手枪", "Glock-18C Auto Pistol", "PISTOL", "全自动手枪", 6.0f, 1, 2, 20, 22, 46.0, 0.030f, 0.005f, 1.5f, 1.5f, 1, false, "pistol_shot", Rarity.UNCOMMON),
            new WeaponSpec("usp_s", "USP-S 消音特战手枪", "USP-S Tactical Silenced", "PISTOL", "消音手枪", 11.0f, 1, 5, 12, 22, 58.0, 0.015f, 0.0015f, 1.8f, 1.65f, 1, true, "silenced_shot", Rarity.RARE),

            // Assault Rifles & Shotgun
            new WeaponSpec("ak47", "AK-47 黄金卡拉什尼科夫步枪", "AK-47 Assault Rifle", "RIFLE", "突击步枪", 12.5f, 1, 3, 30, 34, 85.0, 0.028f, 0.003f, 3.0f, 1.65f, 2, false, "rifle_heavy", Rarity.RARE),
            new WeaponSpec("m4a1", "M4A1-S 消音战术卡宾步枪", "M4A1-S Tactical Carbine", "RIFLE", "战术步枪", 10.5f, 1, 2, 30, 30, 88.0, 0.018f, 0.002f, 3.0f, 1.6f, 1, true, "silenced_shot", Rarity.RARE),
            new WeaponSpec("spas_12", "SPAS-12 战术泵动霰弹枪", "Franchi SPAS-12 Shotgun", "SHOTGUN", "战术霰弹枪", 4.5f, 8, 16, 8, 36, 32.0, 0.068f, 0.022f, 1.6f, 1.4f, 1, false, "shotgun_blast", Rarity.RARE)
        );

        for (WeaponSpec spec : specs) {
            registerGun(spec);
        }

        // Register Tactical Ammo Box
        ResourceKey<Item> ammoKey = ResourceKey.create(Registries.ITEM, Identifier.fromNamespaceAndPath(MOD_ID, "tactical_ammo_box"));
        TACTICAL_AMMO_BOX = new Item(new Item.Properties().setId(ammoKey).stacksTo(1).rarity(Rarity.EPIC));
        Registry.register(BuiltInRegistries.ITEM, ammoKey, TACTICAL_AMMO_BOX);
        ALL_ITEMS.add(TACTICAL_AMMO_BOX);

        // 3. Creative Mode Tab
        ResourceKey<CreativeModeTab> tabKey = ResourceKey.create(
            Registries.CREATIVE_MODE_TAB,
            Identifier.fromNamespaceAndPath(MOD_ID, "main")
        );
        CreativeModeTab tab = FabricCreativeModeTab.builder()
            .title(Component.translatable("itemGroup.mcweapon.tab"))
            .icon(() -> new ItemStack(GUN_ITEMS.get("awp")))
            .build();
        Registry.register(BuiltInRegistries.CREATIVE_MODE_TAB, tabKey, tab);

        CreativeModeTabEvents.modifyOutputEvent(tabKey).register(output -> {
            for (Item item : ALL_ITEMS) {
                output.accept(item);
            }
        });

        CreativeModeTabEvents.modifyOutputEvent(
            ResourceKey.create(Registries.CREATIVE_MODE_TAB, Identifier.withDefaultNamespace("combat"))
        ).register(output -> {
            for (Item item : ALL_ITEMS) {
                output.accept(item);
            }
        });

        // 4. Prevent Block Breaking & Support Left-Click Scope Toggle
        AttackBlockCallback.EVENT.register((player, level, hand, pos, direction) -> {
            ItemStack stack = player.getItemInHand(hand);
            if (stack.getItem() instanceof GunItem gun) {
                if (level instanceof ServerLevel serverLevel) {
                    if (player.isShiftKeyDown() && gun.getAmmo(stack) < gun.getSpec().magazineSize()) {
                        gun.startReload(serverLevel, player, stack);
                    } else {
                        GunItem.toggleScopeLock(serverLevel, player, stack);
                    }
                }
                return InteractionResult.FAIL;
            }
            return InteractionResult.PASS;
        });

        // 5. Prevent Left-Click Breaking Non-Living Entities (ItemFrames, Paintings, ArmorStands, Boats, Minecarts)
        AttackEntityCallback.EVENT.register((player, level, hand, entity, hitResult) -> {
            ItemStack stack = player.getItemInHand(hand);
            if (stack.getItem() instanceof GunItem) {
                if (!(entity instanceof LivingEntity) || (entity instanceof ArmorStand)) {
                    return InteractionResult.FAIL;
                }
            }
            return InteractionResult.PASS;
        });

        // 6. Server Tick: Clean up scope speed attribute when not holding a gun + F-key quick reload detection
        ServerTickEvents.END_SERVER_TICK.register(server -> {
            for (ServerPlayer player : server.getPlayerList().getPlayers()) {
                ItemStack main = player.getMainHandItem();
                ItemStack off = player.getOffhandItem();

                // F-key quick reload: if player pressed F to swap partially used gun to offhand while mainhand is empty
                if (main.isEmpty() && off.getItem() instanceof GunItem offGun) {
                    long now = player.level().getGameTime();
                    if (!offGun.isReloading(off, now) && offGun.getAmmo(off) < offGun.getSpec().magazineSize()) {
                        player.setItemInHand(InteractionHand.MAIN_HAND, off.copy());
                        player.setItemInHand(InteractionHand.OFF_HAND, ItemStack.EMPTY);
                        ItemStack restoredMain = player.getMainHandItem();
                        if (player.level() instanceof ServerLevel sl) {
                            offGun.startReload(sl, player, restoredMain);
                        }
                        continue;
                    }
                }

                boolean holdingGun = (main.getItem() instanceof GunItem) || (off.getItem() instanceof GunItem);
                if (!holdingGun) {
                    GunItem.applyScopeAttribute(player, false, 1.0f);
                }
            }
        });

        // 7. Register /weapon command for easy testing & weapon kit access
        CommandRegistrationCallback.EVENT.register((dispatcher, registryAccess, environment) -> {
            dispatcher.register(Commands.literal("weapon")
                .executes(ctx -> {
                    ServerPlayer sp = ctx.getSource().getPlayerOrException();
                    sendWeaponHelp(sp);
                    return 1;
                })
                .then(Commands.literal("all")
                    .executes(ctx -> {
                        ServerPlayer sp = ctx.getSource().getPlayerOrException();
                        for (Item item : ALL_ITEMS) {
                            sp.getInventory().add(new ItemStack(item));
                        }
                        sp.sendSystemMessage(Component.literal("§a[MCWeapon] 已向您的背包发放全套 13 款热门现代枪械与战术弹药箱！"));
                        return 1;
                    }))
                .then(Commands.literal("scope")
                    .executes(ctx -> {
                        ServerPlayer sp = ctx.getSource().getPlayerOrException();
                        ItemStack main = sp.getMainHandItem();
                        if (main.getItem() instanceof GunItem && sp.level() instanceof ServerLevel sl) {
                            GunItem.toggleScopeLock(sl, sp, main);
                        }
                        return 1;
                    }))
                .then(Commands.literal("reload")
                    .executes(ctx -> {
                        ServerPlayer sp = ctx.getSource().getPlayerOrException();
                        ItemStack main = sp.getMainHandItem();
                        if (main.getItem() instanceof GunItem gun && sp.level() instanceof ServerLevel sl) {
                            gun.startReload(sl, sp, main);
                        }
                        return 1;
                    }))
                .then(Commands.literal("give")
                    .then(Commands.argument("model", StringArgumentType.word())
                        .executes(ctx -> {
                            ServerPlayer sp = ctx.getSource().getPlayerOrException();
                            String model = StringArgumentType.getString(ctx, "model").toLowerCase();
                            GunItem gun = GUN_ITEMS.get(model);
                            if (gun == null) {
                                sp.sendSystemMessage(Component.literal("§c未知枪械型号: " + model + "。可用型号: " + String.join(", ", GUN_ITEMS.keySet())));
                                return 0;
                            }
                            sp.getInventory().add(new ItemStack(gun));
                            sp.sendSystemMessage(Component.literal("§a[MCWeapon] 已发放: §e" + gun.getSpec().zhName()));
                            return 1;
                        })))
            );
        });
    }

    private static void sendWeaponHelp(ServerPlayer player) {
        player.sendSystemMessage(Component.literal("§6========== [MCWeapon 现代战术武器库] =========="));
        player.sendSystemMessage(Component.literal("§e• 狙击枪: §fawp (38伤害/8x镜), barrett_m82 (55伤害/10x镜/4穿), kar98k (28伤害/6x镜)"));
        player.sendSystemMessage(Component.literal("§e• 冲锋枪: §fkriss_vector (20发/秒), mp5 (10发/秒), p90 (50发大弹匣), uzi (20发/秒)"));
        player.sendSystemMessage(Component.literal("§e• 手枪: §fdesert_eagle (19伤害), glock_18 (全自动手枪), usp_s (消音高精)"));
        player.sendSystemMessage(Component.literal("§e• 步枪/霰弹: §fak47, m4a1, spas_12 (8弹丸霰弹)"));
        player.sendSystemMessage(Component.literal("§b• 快捷指令: §f/weapon all §7(领取全部武器) | §f/weapon give <型号> §7| §f/weapon scope §7(切换倍镜) | §f/weapon reload §7(换弹)"));
        player.sendSystemMessage(Component.literal("§a• 操作说明: §f[按住右键] 开火 | [按住Shift 或 左键方块] 开镜放大 | [按F键] 快速换弹"));
    }

    private static GunItem registerGun(WeaponSpec spec) {
        ResourceKey<Item> key = ResourceKey.create(Registries.ITEM, Identifier.fromNamespaceAndPath(MOD_ID, spec.id()));
        Item.Properties props = new Item.Properties()
            .setId(key)
            .stacksTo(1)
            .rarity(spec.rarity())
            .component(DataComponents.USE_EFFECTS, new UseEffects(true, false, 1.0f));
        GunItem item = new GunItem(spec, SOUND_EVENTS.get(spec.soundKey()), props);
        Registry.register(BuiltInRegistries.ITEM, key, item);
        GUN_ITEMS.put(spec.id(), item);
        ALL_ITEMS.add(item);
        return item;
    }
}
'''

with open(os.path.join(src_java_dir, 'WeaponSpec.java'), 'w', encoding='utf-8') as f:
    f.write(weapon_spec_java)
with open(os.path.join(src_java_dir, 'GunItem.java'), 'w', encoding='utf-8') as f:
    f.write(gun_item_java)
with open(os.path.join(src_java_dir, 'McWeaponMod.java'), 'w', encoding='utf-8') as f:
    f.write(mcweapon_mod_java)
with open(os.path.join(src_mixin_dir, 'PlayerScopeMixin.java'), 'w', encoding='utf-8') as f:
    f.write(player_scope_mixin_java)

# 8. Compile Java Sources
print("Compiling Java sources against Minecraft 26.3 & Fabric...")
jars = ['/opt/minecraft/versions/26.3/server-26.3.jar']
for p in glob.glob('/opt/minecraft/libraries/**/*.jar', recursive=True):
    jars.append(p)
for p in glob.glob('/opt/minecraft/.fabric/processedMods/*.jar'):
    jars.append(p)

cp = ':'.join(jars)
javac_cmd = [
    'javac',
    '-encoding', 'UTF-8',
    '-cp', cp,
    '-d', classes_dir,
    os.path.join(src_java_dir, 'WeaponSpec.java'),
    os.path.join(src_java_dir, 'GunItem.java'),
    os.path.join(src_java_dir, 'McWeaponMod.java'),
    os.path.join(src_mixin_dir, 'PlayerScopeMixin.java'),
]
res = subprocess.run(javac_cmd, capture_output=True, text=True)
if res.returncode != 0:
    print("Compilation failed!")
    print(res.stderr)
    exit(1)
print("Compilation succeeded!")

# 9. Package JAR
print("Packaging JAR...")
for root, dirs, files in os.walk(classes_dir):
    rel_root = os.path.relpath(root, classes_dir)
    target_root = os.path.join(BUILD_DIR, rel_root) if rel_root != '.' else BUILD_DIR
    for file in files:
        src_f = os.path.join(root, file)
        dst_f = os.path.join(target_root, file)
        os.makedirs(os.path.dirname(dst_f), exist_ok=True)
        os.replace(src_f, dst_f)

subprocess.run(['rm', '-rf', classes_dir, os.path.join(BUILD_DIR, 'src')])
subprocess.run(['jar', 'cvf', OUT_JAR, '-C', BUILD_DIR, '.'], stdout=subprocess.DEVNULL, check=True)
jar_size = os.path.getsize(OUT_JAR)
print(f"SUCCESS! Mod jar built at: {OUT_JAR} ({jar_size/1024:.1f} KB)")
