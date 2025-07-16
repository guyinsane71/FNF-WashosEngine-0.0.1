import json
import os
import copy
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import List, Dict, Any, Tuple

# =============================================================================
# CONSTANTS & TEMPLATES
# =============================================================================

LOG_FILE_DIR = "/storage/emulated/0/charts"
LOG_FILE_NAME = os.path.join(LOG_FILE_DIR, "conversion_log.txt")

SECTION_BEATS = 4  # How many beats per section in FNF

# Mapping between Psych Engine stage codenames and VSlice stage codenames
STAGE_TO_PSYCH = {
    "mainStage": "stage",
    "spookyMansion": "spooky",
    "phillyTrain": "philly",
    "limoRide": "limo",
    "mallXmas": "mall",
    "tankmanBattlefield": "tank"
}
STAGE_TO_VSLICE = {v: k for k, v in STAGE_TO_PSYCH.items()}

# -----------------------------------------------------------------------------
#   VSlice JSON Templates (Chart & Metadata)
# -----------------------------------------------------------------------------

# NOTE: We keep them as deep-copy-able dicts so we can modify safely per song

VSLICE_CHART_TEMPLATE: Dict[str, Any] = {
    "version": "2.0.0",
    "scrollSpeed": {"default": 1.5},  # will be overwritten per difficulty
    "events": [],
    "notes": {},
    "generatedBy": "Chart_Converter"
}

VSLICE_METADATA_TEMPLATE: Dict[str, Any] = {
    "timeFormat": "ms",
    "artist": "Unknown Artist",
    "charter": "Unknown Charter",
    "playData": {
        "album": "",
        "previewStart": 0,
        "previewEnd": 0,
        "stage": "mainStage",
        "characters": {
            "player": "bf",
            "girlfriend": "",
            "opponent": "dad"
        },
        "songVariations": [],
        "difficulties": [],
        "noteStyle": "funkin"
    },
    "songName": "Unknown Song",
    "timeChanges": [],
    "generatedBy": "Chart_Converter",
    "looped": False,
    "version": "2.2.3"
}

# =============================================================================
#  UTILS
# =============================================================================

def write_to_log(message: str):
    """Append a line to the conversion log file (Android-style storage path)."""
    os.makedirs(LOG_FILE_DIR, exist_ok=True)
    with open(LOG_FILE_NAME, "a", encoding="utf-8") as f:
        f.write(message + "\n")


def sort_by_time(obj):
    return obj['t'] if isinstance(obj, dict) else obj[0]


def calculate_crochet(bpm: float) -> float:
    return 0 if bpm == 0 else 60000.0 / bpm


def load_json(path: str):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(obj: Any, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=4, ensure_ascii=False)

# =============================================================================
#  CONVERSION HELPERS
# =============================================================================


def _apply_lane_swap(data: int) -> int:
    """Swap lanes 0-3 <> 4-7. Helper used when mustHitSection is False."""
    if data < 4:
        return data + 4
    else:
        return data - 4


# -----------------------------------------------------------------------------
#  VSlice  →  Psych Engine
# -----------------------------------------------------------------------------

def format_event_for_psych(event: Dict[str, Any]) -> List[str]:
    """Convert a VSlice event dict to Psych Engine [name, v1, v2] format."""
    event_name = str(event.get('e', 'UnknownEvent'))
    v = event.get('v')
    value1 = ""
    value2 = ""

    if event_name == "FocusCamera" and isinstance(v, dict):
        value1 = str(v.get('char', ''))
        params = []
        for param in ['x', 'y', 'duration', 'ease']:
            if param in v and v[param] != "":
                params.append(str(v[param]))
        value2 = "|".join(params)

    elif event_name == "ZoomCamera" and isinstance(v, dict):
        # Enhanced: include duration, mode, ease
        value1 = str(v.get('zoom', ''))
        params = []
        for param in ['duration', 'mode', 'ease']:
            if param in v and v[param] != "":
                params.append(str(v[param]))
        value2 = "|".join(params)

    elif event_name == "SetCameraBop" and isinstance(v, dict):
        value1 = str(v.get('rate', ''))
        value2 = str(v.get('intensity', ''))

    elif event_name == "PlayAnimation" and isinstance(v, dict):
        value1 = str(v.get('target', ''))
        anim = str(v.get('anim', ''))
        force = v.get('force', None)
        if force is not None:
            value2 = anim + "|" + str(force)
        else:
            value2 = anim

    elif event_name in ("Change Scroll Speed", "ScrollSpeed") and isinstance(v, dict):
        value1 = str(v.get('scroll', v.get('speed', '')))
        params = []
        for param in ['duration', 'ease', 'strumline', 'absolute']:
            if param in v and v[param] != "":
                params.append(str(v[param]))
        value2 = "|".join(params)

    elif event_name == "SetHealthIcon" and isinstance(v, dict):
        value1 = str(v.get('char', ''))
        params = []
        for param in ['id', 'scale', 'flipX', 'isPixel', 'offsetX', 'offsetY']:
            if param in v and v[param] != "":
                params.append(str(v[param]))
        value2 = "|".join(params)

    elif event_name == "Set Property" and isinstance(v, dict):
        value1 = str(v.get('property', ''))
        value2 = str(v.get('value', ''))

    # Generic fall-backs ------------------------------------------------------
    elif isinstance(v, dict):
        keys = list(v.keys())
        if len(keys) > 0:
            value1 = str(v[keys[0]])
        if len(keys) > 1:
            value2 = str(v[keys[1]])
    elif isinstance(v, list):
        if len(v) > 0:
            value1 = str(v[0])
        if len(v) > 1:
            value2 = str(v[1])
    elif v is not None:
        value1 = str(v)

    return [event_name, value1, value2]

# =============================================================================
#  Psych  →  VSlice (includes lane normalization & default scrollSpeed key)
# =============================================================================


def psych_to_vslice(psych_chart: Dict[str, Any], difficulty_name: str = None) -> Dict[str, Dict]:
    """Convert a single Psych Engine chart (one difficulty) to VSlice format."""
    songData = psych_chart.get('song', {})

    events: List[Dict[str, Any]] = []
    notes: List[Dict[str, Any]] = []
    timeChanges: List[Dict[str, Any]] = []

    # -- BPM / Time signature handling ---------------------------------------
    bpm = songData.get('bpm', 120)
    timeChanges.append({'t': 0, 'bpm': bpm})

    # -- Section traversal ----------------------------------------------------
    time = 0
    first_section_must_hit = True
    if songData.get('notes') and len(songData['notes']) > 0:
        first_section_must_hit = songData['notes'][0].get('mustHitSection', True)
    lastMustHit = first_section_must_hit

    # Initial FocusCamera so player strumline is correct
    events.append({'t': 0, 'e': 'FocusCamera', 'v': {'char': 0 if lastMustHit else 1}})

    if songData.get('notes'):
        for section in songData['notes']:
            current_must_hit = section.get('mustHitSection', True)

            # NOTE SWAP --------------------------------------------------------
            if section.get('sectionNotes'):
                for note in section['sectionNotes']:
                    data = note[1]
                    if not current_must_hit:
                        data = _apply_lane_swap(data)

                    vsliceNote = {'t': note[0], 'd': data}
                    if len(note) > 2 and note[2] > 0:
                        vsliceNote['l'] = note[2]
                    if len(note) > 3 and note[3]:
                        vsliceNote['k'] = note[3]
                    notes.append(vsliceNote)

            # BPM change / FocusCamera events ---------------------------------
            section_duration = calculate_crochet(bpm) * SECTION_BEATS

            if section.get('changeBPM') and 'bpm' in section:
                bpm = section['bpm']
                timeChanges.append({'t': time, 'bpm': bpm})

            if lastMustHit != current_must_hit:
                events.append({'t': time, 'e': 'FocusCamera', 'v': {'char': 0 if current_must_hit else 1}})
                lastMustHit = current_must_hit

            time += section_duration

    # -- Additional loose events from Psych chart ----------------------------
    if songData.get('events'):
        for event in songData['events']:
            event_time = event[0]
            if len(event) > 1 and isinstance(event[1], list):
                for subevent_data in event[1]:
                    event_name = subevent_data[0] if len(subevent_data) > 0 else 'Unknown'
                    value1 = subevent_data[1] if len(subevent_data) > 1 else ''
                    value2 = subevent_data[2] if len(subevent_data) > 2 else ''
                    ev = {'t': event_time, 'e': event_name, 'v': {'value1': value1, 'value2': value2}}
                    events.append(ev)

    # Sort lists by time ------------------------------------------------------
    events.sort(key=sort_by_time)
    notes.sort(key=sort_by_time)

    # -- Build chart & metadata ----------------------------------------------
    composer = songData.get('artist', songData.get('composer', 'Unknown Artist'))
    charter = songData.get('charter', 'Unknown Charter')

    if difficulty_name:
        diffs = [difficulty_name]
    else:
        diffs = ['normal']
        write_to_log("WARNING: No specific difficulty provided for Psych to VSlice conversion. Defaulting to ['normal'].")

    base_speed = songData.get('speed', 1.5)
    scrollSpeed = {diff: base_speed for diff in diffs}
    scrollSpeed['default'] = base_speed  # ensure default key exists

    notesMap = {diff: notes for diff in diffs}

    stage = songData.get('stage', 'mainStage')
    stage = STAGE_TO_VSLICE.get(stage, stage)

    chart = copy.deepcopy(VSLICE_CHART_TEMPLATE)
    chart['scrollSpeed'] = scrollSpeed
    chart['events'] = events
    chart['notes'] = notesMap
    chart['generatedBy'] = songData.get('generatedBy', 'Psych Engine Chart Editor V-Slice Exporter')

    metadata = copy.deepcopy(VSLICE_METADATA_TEMPLATE)
    metadata['songName'] = songData.get('song', 'Unknown Song')
    metadata['artist'] = composer
    metadata['charter'] = charter
    metadata['playData']['difficulties'] = diffs
    metadata['playData']['characters']['player'] = songData.get('player1', 'bf')
    metadata['playData']['characters']['girlfriend'] = songData.get('gfVersion', '')
    metadata['playData']['characters']['opponent'] = songData.get('player2', 'dad')
    metadata['playData']['stage'] = stage
    metadata['timeChanges'] = timeChanges
    metadata['generatedBy'] = songData.get('generatedBy', 'Psych Engine Chart Editor V-Slice Exporter')

    return {'chart': chart, 'metadata': metadata}

# =============================================================================
#  VSlice  →  Psych (includes lane normalization & improved scrollSpeed read)
# =============================================================================


def get_section_must_hits(
    focus_camera_events: List[Dict[str, Any]],
    time_changes: List[Dict[str, Any]],
    base_bpm: float,
    last_note_time: float
) -> List[bool]:
    """Compute mustHitSection Flag for each section time."""
    section_must_hits = []
    if focus_camera_events:
        time = 0
        focus_idx = 0
        tc_idx = 0
        bpm = base_bpm
        max_focus_time = focus_camera_events[-1]['t'] if focus_camera_events else 0
        while time < max_focus_time + (calculate_crochet(bpm) * SECTION_BEATS):
            while tc_idx < len(time_changes) and time >= time_changes[tc_idx]['t']:
                bpm = time_changes[tc_idx]['bpm']
                tc_idx += 1
            while focus_idx + 1 < len(focus_camera_events) and time >= focus_camera_events[focus_idx + 1]['t']:
                focus_idx += 1
            fc_event = focus_camera_events[focus_idx]
            char_val = None
            if isinstance(fc_event.get('v'), dict) and 'char' in fc_event['v']:
                char_val = fc_event['v']['char']
            elif not isinstance(fc_event.get('v'), dict) and fc_event.get('v') is not None:
                char_val = fc_event.get('v')
            must_hit = (str(char_val) == "0") if char_val is not None else False
            section_must_hits.append(must_hit)
            section_time = calculate_crochet(bpm) * SECTION_BEATS
            time += section_time
    if not section_must_hits:
        section_must_hits = [True]
    return section_must_hits


def create_base_sections(time_changes: List[Dict[str, Any]], base_bpm: float, last_note_time: float, section_must_hits: List[bool]):
    base_sections: List[Dict[str, Any]] = []
    section_times: List[float] = []
    bpm = base_bpm
    last_bpm = base_bpm
    time = 0
    tc_idx = 0
    section_index = 0

    while time < last_note_time + (calculate_crochet(bpm) * SECTION_BEATS) + 20:
        while tc_idx < len(time_changes) and time >= time_changes[tc_idx]['t']:
            bpm = time_changes[tc_idx]['bpm']
            tc_idx += 1
        sec = {
            "sectionNotes": [],
            "sectionBeats": SECTION_BEATS,
            "mustHitSection": section_must_hits[section_index] if section_index < len(section_must_hits) else section_must_hits[-1],
        }
        if last_bpm != bpm:
            sec["changeBPM"] = True
            sec["bpm"] = bpm
        last_bpm = bpm
        base_sections.append(sec)
        section_times.append(time)
        section_time = calculate_crochet(bpm) * SECTION_BEATS
        time += section_time
        section_index += 1
    return base_sections, section_times


def vslice_to_psych(vslice_chart: Dict[str, Any], vslice_metadata: Dict[str, Any]) -> Dict[str, Dict]:
    """Convert a full VSlice package (chart+metadata) to Psych charts per difficulty."""
    difficulties = vslice_metadata.get('playData', {}).get('difficulties', [])
    if not difficulties:
        difficulties = ['normal']
        write_to_log("WARNING: No difficulties found in VSlice metadata. Defaulting to ['normal'].")

    time_changes = sorted(vslice_metadata.get('timeChanges', []), key=lambda t: t.get('t', 0))
    base_bpm = time_changes[0].get('bpm', 120) if time_changes else 120

    stage = vslice_metadata.get('playData', {}).get('stage', 'mainStage')
    stage = STAGE_TO_PSYCH.get(stage, stage)

    notes_map: Dict[str, List[Dict[str, Any]]] = {}
    last_note_time = 0
    for diff in difficulties:
        notes = vslice_chart.get('notes', {}).get(diff, [])
        notes = sorted(notes, key=sort_by_time)
        notes_map[diff] = notes
        if notes:
            last_note_time = max(last_note_time, notes[-1]['t'])

    all_events = sorted(vslice_chart.get('events', []), key=sort_by_time)

    focus_camera_events = [
        e for e in all_events if e.get('e') == 'FocusCamera' and (
            e.get('v') == 0 or e.get('v') == 1 or (isinstance(e.get('v'), dict) and 'char' in e['v'])
        )
    ]

    section_must_hits = get_section_must_hits(focus_camera_events, time_changes, base_bpm, last_note_time)
    base_sections, section_times = create_base_sections(time_changes, base_bpm, last_note_time, section_must_hits)

    # Prepare file-wide events -------------------------------------------------
    file_events: List[List[Any]] = []
    for e in all_events:
        if e.get('e') == 'FocusCamera' and _is_section_focus_camera(e, section_times, tolerance=1.0):
            continue  # Skip auto-generated camera swaps
        event_fields = format_event_for_psych(e)
        file_events.append([e.get('t', 0), [event_fields]])
    file_events.sort(key=lambda ev: ev[0])

    # -- Build Psych charts per difficulty ------------------------------------
    psych_charts: Dict[str, Dict] = {}
    for diff in difficulties:
        scroll_speed = vslice_chart.get('scrollSpeed', {}).get(diff, vslice_chart.get('scrollSpeed', {}).get('default', 1.5))
        notes = notes_map.get(diff, [])
        section_data = [dict(section, sectionNotes=[]) for section in base_sections]
        note_sec = 0
        for note in notes:
            while note_sec + 1 < len(section_times) and section_times[note_sec + 1] <= note['t']:
                note_sec += 1

            current_must_hit = section_data[note_sec]['mustHitSection'] if 0 <= note_sec < len(section_data) else True
            data = note.get('d', 0)
            if not current_must_hit:
                data = _apply_lane_swap(data)

            psych_note: List[Any] = [
                note.get('t', 0),
                data,
                note.get('l', 0)
            ]
            if note.get('k') and note['k'] not in ("", "normal"):
                psych_note.append(note['k'])

            if 0 <= note_sec < len(section_data):
                section_data[note_sec]["sectionNotes"].append(psych_note)

        characters = vslice_metadata.get('playData', {}).get('characters', {})
        player1 = characters.get('player', 'bf')
        player2 = characters.get('opponent', 'dad')
        gfVersion = characters.get('girlfriend', '')

        song_meta = {
            "song": vslice_metadata.get('songName', 'Unknown Song'),
            "notes": section_data,
            "events": file_events,
            "bpm": base_bpm,
            "needsVoices": True,
            "speed": scroll_speed,
            "offset": 0,
            "player1": player1,
            "player2": player2,
            "gfVersion": gfVersion,
            "stage": stage,
            "format": "psych_v1_convert",
            "artist": vslice_metadata.get('artist', 'Unknown Artist'),
            "charter": vslice_metadata.get('charter', 'Unknown Charter'),
            "generatedBy": "Chart_Converter By Jere"
        }
        psych_charts[diff] = {"song": song_meta}

    return psych_charts


# -----------------------------------------------------------------------------
#  Helper to detect section-camera events to drop when converting -------------
# -----------------------------------------------------------------------------

def _is_section_focus_camera(event: Dict[str, Any], section_times: List[float], tolerance: float = 1.0) -> bool:
    """Return True if a FocusCamera event coincides with the start of a section."""
    if event.get('e') != 'FocusCamera':
        return False
    t = float(event.get('t', -1))
    for st in section_times:
        if abs(t - st) < tolerance:
            return True
    return False

# =============================================================================
#  Minimal CLI to quickly test conversion without the full GUI ---------------
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="FNF Chart Converter (VSlice ⬌ Psych)")
    sub = parser.add_subparsers(dest="mode", required=True)

    vs2p = sub.add_parser("vslice2psych", help="Convert VSlice chart+metadata to Psych")
    vs2p.add_argument("chart", help="VSlice chart.json path")
    vs2p.add_argument("metadata", help="VSlice metadata.json path")
    vs2p.add_argument("outdir", help="Output directory")

    p2vs = sub.add_parser("psych2vslice", help="Convert Psych chart to VSlice")
    p2vs.add_argument("psych", help="Psych chart.json path")
    p2vs.add_argument("outdir", help="Output directory")
    p2vs.add_argument("--diff", help="Override difficulty name", default=None)

    args = parser.parse_args()

    if args.mode == "vslice2psych":
        vs_chart = load_json(args.chart)
        vs_meta = load_json(args.metadata)
        res = vslice_to_psych(vs_chart, vs_meta)
        os.makedirs(args.outdir, exist_ok=True)
        for diff, data in res.items():
            save_json(data, os.path.join(args.outdir, f"{diff}.json"))
        print(f"Converted {len(res)} difficulty(ies) → {args.outdir}")

    elif args.mode == "psych2vslice":
        psy_chart = load_json(args.psych)
        pack = psych_to_vslice(psy_chart, difficulty_name=args.diff)
        os.makedirs(args.outdir, exist_ok=True)
        save_json(pack['chart'], os.path.join(args.outdir, "chart.json"))
        save_json(pack['metadata'], os.path.join(args.outdir, "metadata.json"))
        print(f"Exported VSlice chart+metadata → {args.outdir}")