#!/usr/bin/env python3
# Furi Dynamic Music Mod
# Copyright (c) 2026 LeonKraim
# Licensed under the "Furi Dynamic Music Mod License".
# See the file "LICENSE.md" for the full license text.

"""Small, dependency-free pack editor for the Furi Dynamic Music BepInEx plugin.

It turns timed sections of one source track into standalone WAV cues. Furi's Unity
audio output is disabled, so packs use Windows' native WAV playback instead.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


# Derived from this installed build's Music_SoundBank.txt.
BOSSES = {
    "The Chain": {
        "play": "Play_Law_Music_Arena", "stop": "Stop_Law_Music_Arena", "restart": "Restart_Law",
        "states": ["Law_Phases.Law_Phase1", "Law_Phases.Law_Phase2", "Law_Phases.Law_Phase3", "Law_Phases.Law_Phase4", "Law_Phases.Law_Phase5", "Law_Phases.Law_Phase6", "Law_Phases.Law_Phase7"],
    },
    "The Strap": {
        "play": "Play_Nemesis_Fight", "stop": "Stop_Nemesis_Fight", "restart": "Restart_Nemesis",
        "states": ["BossMode.Nemesis_LongRange", "BossMode.Nemesis_CatAndMouse", "BossMode.Nemesis_CCM"],
    },
    "The Line": {
        "play": "Play_Wise_Fight", "stop": "Stop_Wise_Fight", "restart": "Restart_Wise",
        "states": ["Wise_Phases.Wise_Phase1", "Wise_Phases.Wise_Phase2", "Wise_Phases.Wise_Phase3", "Wise_Phases.Wise_Phase4"],
    },
    "The Song": {
        "play": "Play_Wing_Arena", "stop": "Stop_Wing_Arena", "restart": "Restart_Wing",
        "states": ["Wing_Phases.Phase01", "Wing_Phases.Phase02", "Wing_Phases.Phase03", "Wing_Phases.Phase04", "Wing_Phases.Phase05", "Wing_Phases.Phase06"],
    },
    "The Burst": {
        "play": "Play_Maze_Arena", "stop": "Stop_Maze_Arena", "restart": "Restart_Maze",
        "states": ["Maze_Arena.Phase1", "Maze_Arena.Phase2", "Maze_Arena.Phase3", "Maze_Arena.Phase4", "Maze_Arena.Phase5", "Maze_Arena.Phase6"],
    },
    "The Edge": {
        "play": "Play_Challenger_Arena", "stop": "Stop_Challenger_Arena", "restart": "Restart_Challenger",
        "states": ["Challenger_Phases.Phase01", "Challenger_Phases.Phase02", "Challenger_Phases.Phase03", "Challenger_Phases.Phase04"],
    },
    "The Hand": {
        "play": "Play_Father_Fight", "stop": "Stop_Father_Fight", "restart": "Restart_Father",
        "states": ["Father_Phases.Phase01", "Father_Phases.Phase02", "Father_Phases.Phase03", "Father_Phases.Phase04", "Father_Phases.Phase05"],
    },
    "The Beat": {
        "play": "Play_Horn_Arena", "stop": "Stop_Horn_Arena", "restart": "Restart_Horn",
        "states": ["Horn_Arena.Phase_01", "Horn_Arena.Phase02", "Horn_Arena.Phase03"],
    },
    "The Star": {
        "play": "Play_Scale_Arena", "stop": "Stop_Scale_Arena", "restart": "Restart_Scale",
        "states": ["Scale_Phases.Scale_Phase1", "Scale_Phases.Scale_Phase2", "Scale_Phases.Scale_Phase3", "Scale_Phases.Scale_Phase4", "Scale_Phases.Scale_Phase5", "Scale_Phases.Scale_Phase6", "Scale_Phases.Scale_Phase7"],
    },
    "The Fight": {
        "play": "Play_Avenger_Arena", "stop": "Stop_Avenger_Arena", "restart": "Restart_Avenger",
        "states": ["Avenger_Arena.Phase01", "Avenger_Arena.Phase02", "Avenger_Arena.Phase03", "Avenger_Arena.Phase04", "Avenger_Arena.Phase05", "Avenger_Arena.Phase06"],
    },
    "The One": {
        "play": "Play_MotherShip_Arena", "stop": "Stop_MotherShip_Arena", "restart": "",
        "states": ["MotherShip_Phases.MotherShip_Phase1", "MotherShip_Phases.MotherShip_Phase2", "MotherShip_Phases.MotherShip_Phase3", "MotherShip_Phases.MotherShip_Phase4", "MotherShip_Phases.Mothership_Phase5"],
    },
    "The Chain Round 2": {
        "play": "Play_Bernard_Arena", "stop": "Stop_Bernard_Arena", "restart": "Restart_Bernard",
        "states": ["Bernard_Arena.Phase_01", "Bernard_Arena.Phase_02", "Bernard_Arena.Phase_03", "Bernard_Arena.Phase_04", "Bernard_Arena.Phase_05", "Bernard_Arena.Phase_06", "Bernard_Arena.Phase_07", "Bernard_Arena.Phase_08", "Bernard_Arena.Phase_09"],
    },
}

# Wwise .txt summary bank that lists every sound event and state group the boss can fire.
# The editor parses these so the Trigger menu offers every attack sound and state, not just the basics.
BANK_FILES = {
    "The Chain": "Boss_Law_SoundBank.txt",
    "The Strap": "Boss_Nemesis_SoundBank.txt",
    "The Line": "Boss_Wise_SoundBank.txt",
    "The Song": "Boss_Wing_SoundBank.txt",
    "The Burst": "Boss_Maze_SoundBank.txt",
    "The Edge": "Boss_Challenger_SoundBank.txt",
    "The Hand": "Boss_Father_SoundBank.txt",
    "The Beat": "Boss_Horn_SoundBank.txt",
    "The Star": "Boss_Scale_SoundBank.txt",
    "The Fight": "Boss_Avenger_SoundBank.txt",
    "The One": "Boss_Mothership_SoundBank.txt",
    "The Chain Round 2": "Boss_Law_SoundBank.txt",
}

# Prefix used to filter each boss's phase/path states out of Music_SoundBank.txt.
BOSS_PREFIX = {
    "The Chain": "Law",
    "The Strap": "Nemesis",
    "The Line": "Wise",
    "The Song": "Wing",
    "The Burst": "Maze",
    "The Edge": "Challenger",
    "The Hand": "Father",
    "The Beat": "Horn",
    "The Star": "Scale",
    "The Fight": "Avenger",
    "The One": "MotherShip",
    "The Chain Round 2": "Bernard",
}

# Human explanations for the state groups found in the banks (decompiled from the boss code +
# official wiki). Anything not listed here falls back to a generic label.
KNOWN_STATE_DESCS = {
    "Law_Phases": {
        "Law_Phase1": "Phase 1 - tutorial: projectile waves, then a swordplay duel teaching parry/counter",
        "Law_Phase2": "Phase 2 - low danger: he waits for your charged shots, throws few projectiles",
        "Law_Phase3": "Phase 3 - first bullet-hell (danmaku) segment from the back of the arena; duel becomes area-of-effect",
        "Law_Phase4": "Phase 4 - combines phases 1-3; duel mixes melee and area-of-effect attacks",
        "Law_Phase5": "Phase 5 - large AoE attacks and the staff throw (boomerang); chasing shockwave in the duel",
        "Law_Phase6": "Phase 6 - faster reactions and teleports; invincible taunt leading to the charging QTE grab",
        "Law_Phase7": "Phase 7 (desperation) - invulnerable bullet-hell barrage, then a desperation duel before the kill",
    },
    "Law_Stance": {
        "Law_Stance1": "Stance tier 1 - base attack set. Stances gate which attack patterns the AI may use",
        "Law_Stance2": "Stance tier 2 - higher-intensity attack set",
        "Law_Stance3": "Stance tier 3 - highest-intensity attack set",
    },
    "Law_Path": {
        "Law_Path01": "Path segment 1 - music for walking to the arena (pre-fight), rarely relevant in battle",
        "Law_Path02": "Path segment 2 - pre-fight walk music",
        "Law_Path03": "Path segment 3 - pre-fight walk music",
        "Law_Path04": "Path segment 4 - pre-fight walk music",
    },
    "Mode": {
        "CCM": "Close Combat Mode - the melee duel segment starts (use this to switch music for the duels)",
        "ArenaMode": "Arena Mode - back to ranged combat (fires when the melee duel ends)",
        "Fury": "Fury mode - aggressive barrage state",
        "None": "No mode set",
    },
    "TensionMode": {
        "TensionOn": "Tension ON - intense attacking moment (music intensity switches)",
        "TensionOff": "Tension OFF - calm moment",
        "None": "No tension",
    },
}

# Explanations for The Chain's attack sounds (from the Boss_Law soundbank). Events not listed
# here are described generically from their Wwise category (Weapon/Projectiles/Impacts/Anims/Cutscenes).
KNOWN_EVENT_DESCS = {
    "Play_Law_Weapon_Boomerang_Prepa": "Staff throw wind-up (Phase 5)",
    "Play_Law_Weapon_Boomerang_Cast": "Staff thrown",
    "Play_Law_Weapon_Boomerang_Projectile": "Staff flying across the arena",
    "Play_Law_Weapon_Boomerang_Hit": "Staff hits you",
    "Play_Law_Weapon_Boomerang_End": "Staff returns",
    "Play_Law_Weapon_Grab_Prepa": "Grab/QTE attack wind-up (Phase 6)",
    "Play_Law_Weapon_Grab_Charge_Whoosh": "Grab charge swing",
    "Play_Law_Weapon_Grab_Catch": "Grab connects",
    "Play_Law_Weapon_GrabMpeFail": "Grab fails / you evaded it",
    "Play_Law_Weapon_AngularWave_Cast": "Shockwave (area-of-effect) cast",
    "Play_Law_Weapon_AngularWave_Projectile": "Shockwave travelling",
    "Play_Law_Weapon_AngularWave_Projectile_Hit": "Shockwave hits you",
    "Play_Law_Weapon_WideslashFront_Prepa": "Front slash wind-up (melee duel)",
    "Play_Law_Weapon_WideslashFront_Impact": "Front slash lands",
    "Play_Law_Weapon_WideslashFront_End": "Front slash recovery",
    "Play_Law_Weapon_WideslashRL_Prepa": "Side slash wind-up",
    "Play_Law_Weapon_WideslashRL_Whoosh1": "Side slash swing 1",
    "Play_Law_Weapon_WideslashRL_Whoosh2": "Side slash swing 2",
    "Play_Law_Weapon_SwipeSlash_Prepa": "Swipe slash wind-up",
    "Play_Law_Weapon_SwipeSlash_Cast": "Swipe slash swings",
    "Play_Law_Teleport_In": "Teleports in (Phases 4-6)",
    "Play_Law_Teleport_Out": "Teleports out",
    "Play_Law_Dash": "Dash move",
    "Play_Law_Jump_Decollage": "Jump take-off",
    "Play_Law_Jump_Reception": "Jump landing",
    "Play_Law_ForceField_Loop": "Invincible force field ON (Phase 6 taunt)",
    "Stop_Law_ForceField_Loop": "Force field OFF",
    "Play_Law_LigthningStrikeFlash": "Lightning strike flash",
    "Play_Law_Fury_Range": "Fury ranged barrage starts",
    "Stop_Law_Fury_Range": "Fury ranged barrage ends",
    "Play_Law_Moves_Whirl": "Whirl movement sound",
    "Play_Law_Moves_Quick": "Quick movement sound",
    "Play_Law_Change_Head": "Head-change animation",
    "Play_Law_Weapon_Range_Aiming_Cast": "Ranged aiming shot fired",
    "Play_Law_Weapon_Range_Aiming_Impact": "Ranged shot impact",
    "Play_Law_Weapon_Range_Aiming_Destroy": "Aiming orb shot down",
    "Play_Law_Weapon_Range_Mine_Cast": "Mine deployed",
    "Play_Law_Weapon_Range_Mine_Destroy": "Mine destroyed",
    "Play_Law_Weapon_Range_Simple_Destroy": "Simple bullet shot down",
    "Play_Law_Weapon_Range_ImpactMC": "Ranged attack hits you",
    "Play_Law_Weapon_Range_ImpactMC_Electric": "Electric ranged attack hits you",
    "Play_Law_Weapon_Range_Impact_Hurt": "Ranged attack hits you (hurt)",
    "Play_Law_Weapon_Melee_Parry": "Your parry connects",
    "Play_Law_Weapon_Melee_Impact_Received": "Boss takes a melee hit",
    "Play_Law_Weapon_Melee_ImpactMC": "Melee attack hits you",
    "Play_Law_Weapon_Melee_Whoosh_Air": "Melee swing in the air",
    "Play_Law_Weapon_Melee_Whoosh_Whirl": "Whirl swing",
    "Play_Law_Weapon_Melee_Whoosh_Fx": "Melee swing FX",
    "Play_Law_Bodyfall": "Boss falls to the ground",
    "Play_Law_Footsteps": "Footsteps",
    "Play_Law_Intro_Master": "Cinematic: fight intro",
    "Play_Law_Outro_Master": "Cinematic: fight outro",
    "Play_Game_Intro_Master": "Cinematic: game intro",
}

EVENT_CATEGORY_DESCS = {
    "Weapon": "Boss weapon sound",
    "Projectiles": "Projectile sound",
    "Impacts": "Hit impact sound",
    "Anims": "Movement/animation sound",
    "Cutscenes": "Cinematic event",
    "Ambience": "Environment ambience (rain, wind, lightning)",
    "Test": "Developer test event",
    "Other": "Uncategorised event",
}


def default_game_root():
    """The editor lives in <game root>/FuriMusicMod/, so the game root is two levels up."""
    here = Path(__file__).resolve()
    return str(here.parent.parent)


def event_category(path, name):
    if "ENV_Events" in path:
        return "Ambience"
    if "TEMP_TESTS" in path:
        return "Test"
    for category in ("Weapon", "Projectiles", "Impacts", "Anims", "Cutscenes"):
        if "\\" + category + "\\" in path:
            return category
    return "Other"


def state_meaning(group, state):
    if group in KNOWN_STATE_DESCS and state in KNOWN_STATE_DESCS[group]:
        return KNOWN_STATE_DESCS[group][state]
    if group.endswith("_Phases") or group.endswith("_Arena") or group == "BossMode":
        return "Combat segment begins: " + state
    if "_Path" in group or group.startswith("Path"):
        return "Path (pre-fight walk) segment: " + state
    return "State of '" + group + "'"


def read_bank_file(bank_path):
    """Parse a Wwise .txt bank summary. Returns (events, states, state_groups) where
    events = [(name, wwise_path), ...], states = [(group, name, wwise_path), ...]."""
    events, states, groups = [], [], []
    if not bank_path or not Path(bank_path).is_file():
        return events, states, groups
    section = None
    for raw in Path(bank_path).read_text(encoding="utf-8", errors="replace").splitlines():
        if raw.startswith("Event\t"):
            section = "event"; continue
        if raw.startswith("State Group\t"):
            section = "group"; continue
        if raw.startswith("State\t"):
            section = "state"; continue
        if raw.startswith("Custom State") or raw.startswith("Game Parameter") or raw.startswith("Audio Bus") or raw.startswith("Switch"):
            section = None; continue
        if not raw.startswith("\t"):
            continue
        parts = raw.split("\t")
        if len(parts) < 3 or not parts[1].isdigit():
            continue
        name = parts[2].strip()
        if not name:
            continue
        path = parts[5].strip() if len(parts) > 5 else ""
        if section == "event":
            events.append((name, path))
        elif section == "state":
            group = parts[3].strip() if len(parts) > 3 else ""
            states.append((group, name, path))
        elif section == "group":
            groups.append((name, path))
    return events, states, groups


def safe_name(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_-]+", "_", value.strip())
    return value.strip("_") or "cue"


class Editor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Furi Dynamic Music Pack Editor")
        self.minsize(1000, 640)
        self.project_path = None
        self.cues = []
        self._bank_cache = {}
        self._trigger_docs = {}

        self.pack_name = tk.StringVar(value="My Furi Music Pack")
        self.source_file = tk.StringVar()
        self.game_root = tk.StringVar(value=default_game_root())
        self.boss = tk.StringVar(value=next(iter(BOSSES)))
        self.ffmpeg = tk.StringVar(value=shutil.which("ffmpeg") or "ffmpeg")
        self.trigger = tk.StringVar()
        self.cue_id = tk.StringVar()
        self.start = tk.StringVar(value="0")
        self.end = tk.StringVar(value="30")
        self.bpm = tk.StringVar(value="120")
        self.beats = tk.StringVar(value="4")
        self.loop = tk.BooleanVar(value=True)
        self.transition = tk.StringVar(value="next_bar")
        self.block_original = tk.BooleanVar(value=True)
        self.intro_start = tk.StringVar(value="")
        self.intro_end = tk.StringVar(value="")
        self.fade_in = tk.StringVar(value="2")

        self._build_ui()
        self._populate_triggers()

    def _build_ui(self):
        top = ttk.Frame(self, padding=10)
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(1, weight=1)
        top.columnconfigure(3, weight=1)
        self._entry(top, 0, "Pack name", self.pack_name)
        self._entry(top, 0, "Source track", self.source_file, button=self._pick_source, column=2)
        ttk.Label(top, text="Boss").grid(row=1, column=0, sticky="w", padx=(0, 6), pady=4)
        boss_box = ttk.Combobox(top, textvariable=self.boss, values=list(BOSSES), state="readonly")
        boss_box.grid(row=1, column=1, sticky="ew", pady=4)
        boss_box.bind("<<ComboboxSelected>>", lambda _event: self._populate_triggers())
        self._entry(top, 1, "ffmpeg path", self.ffmpeg, button=self._pick_ffmpeg, column=2)
        self._entry(top, 2, "Game folder (auto-detected)", self.game_root, button=self._pick_game_root, column=2)

        guide = ttk.Label(self, justify="left", anchor="w", wraplength=980,
                          text="Start here: choose your boss and source song, then add one cue for each moment you want music for. "
                               "The Trigger menu lists the boss's fight-start/retry/stop music events, every phase state (state:...), "
                               "combat modes (melee duel vs ranged), stances and tension states, plus every attack sound (event:...) "
                               "so you can react to specific moments. Start/End choose the piece of the source song; "
                               "BPM and Beats/bar let transitions land on rhythm; Loop repeats a phase; Transition chooses when the next cue takes over. "
                               "Fill in Intro start/end to play that part exactly once with a fade-in when the fight starts, "
                               "then the rest of the song (from Intro end onward) loops forever.")
        guide.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 8))

        edit = ttk.LabelFrame(self, text="Cue (one source-track section per game event or phase)", padding=10)
        edit.grid(row=2, column=0, sticky="ew", padx=10)
        for column in range(8):
            edit.columnconfigure(column, weight=1 if column in (1, 3) else 0)
        self._labelled_combo(edit, 0, "Trigger", self.trigger, [])
        self._labelled_entry(edit, 0, "Cue id", self.cue_id, column=2)
        self._labelled_entry(edit, 0, "Start (s)", self.start, column=4)
        self._labelled_entry(edit, 0, "End (s)", self.end, column=6)
        self._labelled_entry(edit, 2, "BPM", self.bpm)
        self._labelled_entry(edit, 2, "Beats/bar", self.beats, column=2)
        ttk.Checkbutton(edit, text="Loop this exported cue", variable=self.loop).grid(row=3, column=4, columnspan=2, sticky="w", pady=(0, 4))
        ttk.Label(edit, text="Transition (when it switches)").grid(row=2, column=6, sticky="w")
        ttk.Combobox(edit, textvariable=self.transition, state="readonly", values=["immediate", "next_beat", "next_bar"]).grid(row=3, column=6, columnspan=2, sticky="ew", pady=(0, 4))
        self._labelled_entry(edit, 4, "Intro start (s)", self.intro_start)
        self._labelled_entry(edit, 4, "Intro end (s)", self.intro_end, column=2)
        self._labelled_entry(edit, 4, "Fade-in (s)", self.fade_in, column=4)
        ttk.Checkbutton(edit, text="Block original sound", variable=self.block_original).grid(row=5, column=6, columnspan=2, sticky="w", pady=(0, 4))
        buttons = ttk.Frame(edit)
        ttk.Label(edit, text="Intro start/end play that part once (with a fade-in) when the fight starts, then the rest of the song (from Intro end onward) loops forever. "
                             "Leave them empty to loop only the Start/End section. Tip: use next_bar when phase music shares the same tempo; use immediate for intros or endings.", foreground="#555555").grid(row=6, column=0, columnspan=8, sticky="w", pady=(2, 0))
        buttons.grid(row=7, column=0, columnspan=8, sticky="e", pady=(5, 0))
        ttk.Button(buttons, text="Add cue", command=self._add_cue).pack(side="left", padx=4)
        ttk.Button(buttons, text="Update selected", command=self._update_cue).pack(side="left", padx=4)
        ttk.Button(buttons, text="Remove selected", command=self._remove_cue).pack(side="left", padx=4)

        table_frame = ttk.Frame(self, padding=10)
        table_frame.grid(row=3, column=0, sticky="nsew")
        self.rowconfigure(3, weight=1)
        self.columnconfigure(0, weight=1)
        columns = ("trigger", "cue", "start", "end", "loop", "bpm", "transition", "intro", "orig")
        self.table = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
        for column, heading, width in [
            ("trigger", "Game trigger", 260), ("cue", "Cue", 130), ("start", "Start", 60), ("end", "End", 60),
            ("loop", "Loop", 50), ("bpm", "BPM", 50), ("transition", "Transition", 90), ("intro", "Intro", 80), ("orig", "Orig", 55),
        ]:
            self.table.heading(column, text=heading)
            self.table.column(column, width=width, anchor="center" if column != "trigger" else "w")
        self.table.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(table_frame, command=self.table.yview)
        scrollbar.pack(side="right", fill="y")
        self.table.configure(yscrollcommand=scrollbar.set)
        self.table.bind("<<TreeviewSelect>>", self._select_cue)

        bottom = ttk.Frame(self, padding=10)
        bottom.grid(row=4, column=0, sticky="ew")
        ttk.Button(bottom, text="New project", command=self._new_project).pack(side="left", padx=4)
        ttk.Button(bottom, text="Open project", command=self._open_project).pack(side="left", padx=4)
        ttk.Button(bottom, text="Save project", command=self._save_project).pack(side="left", padx=4)
        ttk.Button(bottom, text="Trigger reference / help", command=self._show_cue_map).pack(side="left", padx=4)
        ttk.Button(bottom, text="Build pack", command=self._build_pack).pack(side="right", padx=4)
        ttk.Label(bottom, text="Build exports a ready-to-share pack of standalone .wav files. ffmpeg is required.").pack(side="right", padx=12)

    def _show_cue_map(self):
        window = tk.Toplevel(self)
        window.title("Furi trigger reference — " + self.boss.get())
        window.geometry("1180x720")
        window.minsize(800, 420)
        window.grid_rowconfigure(1, weight=1)
        window.grid_columnconfigure(0, weight=1)
        header = ttk.Label(window, justify="left", anchor="w", wraplength=1100,
                           text="A trigger is a signal Furi sends through its audio system. You do not invent these names: pick one from the Trigger menu. "
                                "Three kinds exist: 'event:' (a sound/music event fired), 'state:' (a state switch, e.g. phase change or combat mode), "
                                "and 'eventid:' (a raw numeric event id). Every trigger below is one your selected boss actually sends during the fight. "
                                "The table lists every trigger from his soundbank with what it means in-game. "
                                "Repeated triggers (e.g. an attack used many times) re-fire the cue each time; if the same cue is already playing it simply continues.")
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 0))
        columns = ("trigger", "meaning", "details")
        tree = ttk.Treeview(window, columns=columns, show="headings")
        for column, heading, width in [("trigger", "Game trigger", 360), ("meaning", "What it means in-game", 460), ("details", "Details", 330)]:
            tree.heading(column, text=heading)
            tree.column(column, width=width, anchor="w", stretch=True)
        boss = BOSSES[self.boss.get()]
        tree.insert("", "end", values=("event:" + boss["play"], "Fight starts — the boss music event", "Keep 'Block original sound' ON for this one"))
        if boss["restart"]:
            tree.insert("", "end", values=("event:" + boss["restart"], "Retry / restart of the fight", "Music event"))
        tree.insert("", "end", values=("event:" + boss["stop"], "Fight ends — music stops", "Stop binding added automatically at build"))
        for trigger in sorted(self._trigger_docs):
            meaning, details = self._trigger_docs[trigger]
            kind = "state" if trigger.startswith("state:") else "event"
            tree.insert("", "end", values=(trigger, meaning, details + (" | " + kind)))
        yscroll = ttk.Scrollbar(window, command=tree.yview)
        hscroll = ttk.Scrollbar(window, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=yscroll.set, xscrollcommand=hscroll.set)
        tree.grid(row=1, column=0, sticky="nsew", padx=(12, 0))
        yscroll.grid(row=1, column=1, sticky="ns")
        hscroll.grid(row=2, column=0, sticky="ew", padx=(12, 0))
        footer = ttk.Label(window, justify="left", anchor="w", wraplength=1100, text=
                  "Field glossary: Cue id is your own short name. Start/End are seconds in the source track. "
                  "Loop should be enabled for a repeating phase. BPM is beats per minute; Beats/bar is usually 4. "
                  "Immediate switches now, next_beat waits for the next beat, and next_bar waits for the next bar. "
                  "Intro start/end (optional): a part played exactly once when the fight starts with a fade-in of Fade-in seconds; "
                  "the rest of the song (from Intro end to the end of the source) then loops forever. Leave empty to loop only the Start/End section. "
                  "Block original sound: for music events keep it ON (stops the original track). "
                  "For attack sounds (events like Play_..._Weapon_..., states, tension, mode) set it OFF, otherwise that attack's sound gets silenced. "
                  "States do not block anything either way. The editor exports each timed section as its own WAV so loops repeat cleanly.",
                  foreground="#555555")
        footer.grid(row=3, column=0, sticky="ew", padx=12, pady=(4, 12))

        def _resize(_event=None):
            width = window.winfo_width()
            if width > 100:
                header.configure(wraplength=width - 24)
                footer.configure(wraplength=width - 24)

        window.bind("<Configure>", _resize)

    def _entry(self, parent, row, label, variable, button=None, column=0):
        ttk.Label(parent, text=label).grid(row=row, column=column, sticky="w", padx=(0, 6), pady=4)
        ttk.Entry(parent, textvariable=variable).grid(row=row, column=column + 1, sticky="ew", pady=4)
        if button:
            ttk.Button(parent, text="Browse", command=button).grid(row=row, column=column + 2, padx=(6, 0), pady=4)

    def _labelled_entry(self, parent, row, label, variable, column=0):
        ttk.Label(parent, text=label).grid(row=row, column=column, sticky="w")
        ttk.Entry(parent, textvariable=variable).grid(row=row + 1, column=column, columnspan=2, sticky="ew", padx=(0, 12), pady=(0, 4))

    def _labelled_combo(self, parent, row, label, variable, values, column=0):
        ttk.Label(parent, text=label).grid(row=row, column=column, sticky="w")
        self.trigger_box = ttk.Combobox(parent, textvariable=variable, values=values, state="readonly")
        self.trigger_box.grid(row=row + 1, column=column, columnspan=2, sticky="ew", padx=(0, 12), pady=(0, 4))

    def _pick_source(self):
        selected = filedialog.askopenfilename(filetypes=[("Audio", "*.mp3 *.ogg *.wav *.aif *.aiff"), ("All files", "*.*")])
        if selected:
            self.source_file.set(selected)

    def _pick_ffmpeg(self):
        selected = filedialog.askopenfilename(filetypes=[("ffmpeg executable", "ffmpeg.exe"), ("All files", "*.*")])
        if selected:
            self.ffmpeg.set(selected)

    def _pick_game_root(self):
        selected = filedialog.askdirectory(title="Choose the Furi game folder")
        if selected:
            self.game_root.set(selected)
            self._populate_triggers()

    def _bank_events_and_states(self):
        bank_name = BANK_FILES.get(self.boss.get())
        if not bank_name:
            return [], [], []
        bank_path = Path(self.game_root.get()) / "Furi_Data" / "StreamingAssets" / "Audio" / "GeneratedSoundBanks" / "Windows" / bank_name
        music_path = Path(self.game_root.get()) / "Furi_Data" / "StreamingAssets" / "Audio" / "GeneratedSoundBanks" / "Windows" / "Music_SoundBank.txt"
        try:
            stamp = bank_path.stat().st_mtime_ns
        except OSError:
            return [], [], []
        try:
            music_stamp = music_path.stat().st_mtime_ns
        except OSError:
            music_stamp = 0
        cached = self._bank_cache.get(bank_name)
        if cached is not None and cached[0] == stamp and cached[1] == music_stamp:
            return cached[2]
        events, states, groups = read_bank_file(str(bank_path))
        prefix = BOSS_PREFIX.get(self.boss.get(), "")
        if music_stamp:
            _m_events, m_states, m_groups = read_bank_file(str(music_path))
            merged = {(group, state) for group, state, _path in states}
            music_groups = set()
            for group_name, group_path in m_groups:
                if group_name == "Mode":
                    music_groups.add(group_name)
                elif prefix and (("\\" + prefix + "_States\\") in group_path or ("\\" + prefix + "\\") in group_path):
                    music_groups.add(group_name)
            for group, state, _path in m_states:
                if group in music_groups:
                    merged.add((group, state))
            states = sorted((group, state, "") for group, state in merged)
        result = (events, states, groups)
        self._bank_cache[bank_name] = (stamp, music_stamp, result)
        return result

    def _populate_triggers(self):
        boss = BOSSES[self.boss.get()]
        values = ["event:" + boss["play"]]
        if boss["restart"]:
            values.append("event:" + boss["restart"])
        self._trigger_docs = {
            "event:" + boss["play"]: ("Fight starts", "Music play event. Keep 'Block original sound' ON so the original track is silenced."),
            "event:" + boss["stop"]: ("Fight ends / music stop", "A stop binding for this is added automatically when building."),
        }
        if boss["restart"]:
            self._trigger_docs["event:" + boss["restart"]] = ("Retry / restart", "Fired when the fight is retried.")
        events, states, _groups = self._bank_events_and_states()
        states_by_group = {}
        for group, state, path in states:
            states_by_group.setdefault(group, []).append((state, path))
        if not states_by_group:
            for full in boss["states"]:
                if "." in full:
                    group, state = full.split(".", 1)
                    states_by_group.setdefault(group, []).append((state, ""))
        for group in sorted(states_by_group):
            for state, path in states_by_group[group]:
                trigger = "state:" + group + "." + state
                values.append(trigger)
                meaning = state_meaning(group, state)
                self._trigger_docs[trigger] = (meaning, group + " | " + path if path else group)
        for name, path in sorted(events):
            trigger = "event:" + name
            values.append(trigger)
            category = event_category(path, name)
            meaning = KNOWN_EVENT_DESCS.get(name) or EVENT_CATEGORY_DESCS.get(category, EVENT_CATEGORY_DESCS["Other"])
            self._trigger_docs[trigger] = (meaning, category + " | " + path if path else category)
        self.trigger_box["values"] = values
        self.trigger.set(values[0])
        self.trigger_box.bind("<<ComboboxSelected>>", self._on_trigger_selected)

    def _on_trigger_selected(self, _event=None):
        trigger = self.trigger.get()
        boss = BOSSES[self.boss.get()]
        music_names = {boss["play"], boss.get("restart", ""), boss.get("stop", "")}
        if trigger.startswith("event:") and trigger[6:] in music_names:
            self.block_original.set(True)
        else:
            self.block_original.set(False)

    def _read_fields(self):
        try:
            start, end = float(self.start.get()), float(self.end.get())
            bpm, beats = float(self.bpm.get()), int(self.beats.get())
        except ValueError:
            raise ValueError("Start/end/BPM must be numbers and beats per bar must be an integer.")
        if not self.trigger.get() or not self.cue_id.get().strip():
            raise ValueError("Choose a trigger and provide a cue id.")
        if start < 0 or end <= start or bpm <= 0 or beats < 1:
            raise ValueError("Use end > start, BPM > 0, and at least one beat per bar.")
        intro = None
        intro_s, intro_e = self.intro_start.get().strip(), self.intro_end.get().strip()
        if intro_s or intro_e:
            if not intro_s or not intro_e:
                raise ValueError("Fill in both intro start and intro end, or leave both empty for no intro.")
            try:
                intro_start, intro_end, fade = float(intro_s), float(intro_e), float(self.fade_in.get())
            except ValueError:
                raise ValueError("Intro start/end and fade-in must be numbers.")
            if intro_start < 0 or intro_end <= intro_start or fade < 0:
                raise ValueError("Use intro end > intro start, and fade-in >= 0.")
            intro = {"start": intro_start, "end": intro_end, "fade": fade}
        return {
            "trigger": self.trigger.get(), "cue": safe_name(self.cue_id.get()), "start": start, "end": end,
            "loop": self.loop.get(), "bpm": bpm, "beats_per_bar": beats, "transition": self.transition.get(),
            "block_original": self.block_original.get(),
            "intro": intro,
        }

    def _add_cue(self):
        try:
            cue = self._read_fields()
        except ValueError as error:
            messagebox.showerror("Invalid cue", str(error)); return
        if any(item["trigger"] == cue["trigger"] for item in self.cues):
            messagebox.showerror("Duplicate trigger", "Each game trigger can have one cue. Select it and update it instead."); return
        if any(item["cue"] == cue["cue"] for item in self.cues):
            messagebox.showerror("Duplicate cue id", "Cue ids must be unique."); return
        self.cues.append(cue)
        self._refresh_table()

    def _selected_index(self):
        selected = self.table.selection()
        return int(selected[0]) if selected else None

    def _update_cue(self):
        index = self._selected_index()
        if index is None:
            messagebox.showinfo("Select a cue", "Select a cue in the table first."); return
        try:
            self.cues[index] = self._read_fields()
        except ValueError as error:
            messagebox.showerror("Invalid cue", str(error)); return
        self._refresh_table()

    def _remove_cue(self):
        index = self._selected_index()
        if index is not None:
            self.cues.pop(index); self._refresh_table()

    def _select_cue(self, _event):
        index = self._selected_index()
        if index is None: return
        cue = self.cues[index]
        self.trigger.set(cue["trigger"]); self.cue_id.set(cue["cue"])
        self.start.set(str(cue["start"])); self.end.set(str(cue["end"]))
        self.bpm.set(str(cue["bpm"])); self.beats.set(str(cue["beats_per_bar"]))
        self.loop.set(cue["loop"]); self.transition.set(cue["transition"])
        self.block_original.set(cue.get("block_original", True))
        intro = cue.get("intro")
        if intro:
            self.intro_start.set(str(intro.get("start", 0))); self.intro_end.set(str(intro.get("end", 0))); self.fade_in.set(str(intro.get("fade", 0)))
        else:
            self.intro_start.set(""); self.intro_end.set(""); self.fade_in.set("")

    def _refresh_table(self):
        self.table.delete(*self.table.get_children())
        for index, cue in enumerate(self.cues):
            self.table.insert("", "end", iid=str(index), values=(cue["trigger"], cue["cue"], cue["start"], cue["end"], "yes" if cue["loop"] else "no", cue["bpm"], cue["transition"], "once->loop" if cue.get("intro") else "no", "stop" if cue.get("block_original", True) else "keep"))

    def _project_data(self):
        return {"version": 1, "name": self.pack_name.get(), "source_file": self.source_file.get(), "boss": self.boss.get(), "cues": self.cues}

    def _new_project(self):
        self.project_path = None; self.cues = []; self.pack_name.set("My Furi Music Pack"); self.source_file.set(""); self.intro_start.set(""); self.intro_end.set(""); self._refresh_table()

    def _open_project(self):
        selected = filedialog.askopenfilename(filetypes=[("Furi music project", "*.furi-music.json"), ("JSON", "*.json")])
        if not selected: return
        try:
            with open(selected, "r", encoding="utf-8") as handle: data = json.load(handle)
            if data.get("version") != 1: raise ValueError("This is not a version 1 Furi music project.")
            self.project_path = Path(selected); self.pack_name.set(data["name"]); self.source_file.set(data["source_file"])
            self.boss.set(data["boss"]); self._populate_triggers(); self.cues = data.get("cues", []); self._refresh_table()
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
            messagebox.showerror("Could not open project", str(error))

    def _save_project(self):
        if self.project_path is None:
            selected = filedialog.asksaveasfilename(defaultextension=".furi-music.json", filetypes=[("Furi music project", "*.furi-music.json")])
            if not selected: return
            self.project_path = Path(selected)
        try:
            self.project_path.write_text(json.dumps(self._project_data(), indent=2), encoding="utf-8")
            self.title("Furi Dynamic Music Pack Editor — " + self.project_path.name)
        except OSError as error:
            messagebox.showerror("Could not save project", str(error))

    def _build_pack(self):
        if not self.cues:
            messagebox.showerror("No cues", "Add at least one cue."); return
        source = Path(self.source_file.get())
        ffmpeg = self.ffmpeg.get()
        if not source.is_file():
            messagebox.showerror("Missing source track", "Choose an existing source MP3, Ogg, WAV, or AIFF file."); return
        if not (Path(ffmpeg).is_file() or shutil.which(ffmpeg)):
            messagebox.showerror("ffmpeg not found", "Install ffmpeg or select its executable. The editor uses it to make precise standalone WAV cues."); return
        destination = filedialog.askdirectory(title="Choose the BepInEx packs folder (or any empty destination)")
        if not destination: return
        pack_dir = Path(destination) / safe_name(self.pack_name.get())
        if Path(destination).name == safe_name(self.pack_name.get()):
            pack_dir = Path(destination)
        if pack_dir.exists() and not messagebox.askyesno("Replace pack", f"{pack_dir} already exists. Replace its generated music and manifest?"):
            return
        try:
            music_dir = pack_dir / "music"; music_dir.mkdir(parents=True, exist_ok=True)
            manifest_cues, bindings = [], []
            for cue in self.cues:
                output = music_dir / (cue["cue"] + ".wav")
                intro = cue.get("intro")
                if intro:
                    start, duration = intro["end"], None
                else:
                    start, duration = cue["start"], cue["end"] - cue["start"]
                command = [ffmpeg, "-y", "-i", str(source), "-ss", str(start)]
                if duration is not None:
                    command += ["-t", str(duration)]
                command += ["-vn", "-c:a", "pcm_s16le", str(output)]
                completed = subprocess.run(command, capture_output=True, text=True)
                if completed.returncode != 0:
                    raise RuntimeError("ffmpeg could not export " + cue["cue"] + ":\n" + completed.stderr[-1000:])
                manifest_cue = {"id": cue["cue"], "file": "music/" + output.name, "loop": cue["loop"], "start_seconds": 0.0, "bpm": cue["bpm"], "beats_per_bar": cue["beats_per_bar"], "gain_db": 0.0}
                if intro:
                    intro_out = music_dir / (cue["cue"] + ".intro.wav")
                    command = [ffmpeg, "-y", "-i", str(source), "-ss", str(intro["start"]), "-t", str(intro["end"] - intro["start"]), "-vn", "-c:a", "pcm_s16le"]
                    if intro["fade"] > 0:
                        command += ["-af", "afade=t=in:st=0:d=" + str(intro["fade"])]
                    command.append(str(intro_out))
                    completed = subprocess.run(command, capture_output=True, text=True)
                    if completed.returncode != 0:
                        raise RuntimeError("ffmpeg could not export intro for " + cue["cue"] + ":\n" + completed.stderr[-1000:])
                    manifest_cue["intro_file"] = "music/" + intro_out.name
                manifest_cues.append(manifest_cue)
                bindings.append({"trigger": cue["trigger"], "cue": cue["cue"], "transition": cue["transition"], "fade_seconds": 0.03, "block_original": bool(cue.get("block_original", True))})
            boss = BOSSES[self.boss.get()]
            bindings.append({"trigger": "event:" + boss["stop"], "action": "stop", "fade_seconds": 0.15, "block_original": True})
            manifest = {"schema_version": 1, "name": self.pack_name.get(), "gain_db": 0.0, "cues": manifest_cues, "bindings": bindings}
            (pack_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            messagebox.showinfo("Pack built", f"Built {len(self.cues)} cues in:\n{pack_dir}\n\nSet Active pack = {pack_dir.name} in the BepInEx config.")
        except (OSError, RuntimeError) as error:
            messagebox.showerror("Could not build pack", str(error))


if __name__ == "__main__":
    try:
        Editor().mainloop()
    except tk.TclError as error:
        print("The editor needs Python with Tkinter: " + str(error), file=sys.stderr)
        sys.exit(1)
