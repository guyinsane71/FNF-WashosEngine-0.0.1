import json
import os
import sys
import glob
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import datetime

# Configuration
LOG_FILE_DIR = "/storage/emulated/0/charts"
LOG_FILE_NAME = os.path.join(LOG_FILE_DIR, "conversion_log.txt")

# Stage mappings
STAGE_TO_PSYCH = {
    "mainStage": "stage",
    "spookyMansion": "spooky", 
    "phillyTrain": "philly",
    "limoRide": "limo",
    "mallXmas": "mall",
    "tankmanBattlefield": "tank"
}
STAGE_TO_VSLICE = {v: k for k, v in STAGE_TO_PSYCH.items()}
SECTION_BEATS = 4

# Chart Templates
VSLICE_CHART_TEMPLATE = {
    "version": "2.0.0",
    "scrollSpeed": {},
    "events": [],
    "notes": {},
    "generatedBy": "Chart_Converter By Jere (Enhanced)"
}

VSLICE_METADATA_TEMPLATE = {
    "songName": "",
    "artist": "",
    "charter": "",
    "playData": {
        "difficulties": [],
        "characters": {
            "player": "bf",
            "girlfriend": "",
            "opponent": "dad"
        },
        "noteStyle": "funkin",
        "stage": "mainStage"
    },
    "timeFormat": "ms",
    "timeChanges": [],
    "generatedBy": "Chart_Converter By Jere (Enhanced)",
    "version": "2.2.3"
}

PSYCH_CHART_TEMPLATE = {
    "song": {
        "song": "",
        "bpm": 120,
        "needsVoices": True,
        "player1": "bf",
        "player2": "dad",
        "gfVersion": "",
        "speed": 1.5,
        "notes": [],
        "events": [],
        "stage": "mainStage",
        "format": "psych_v1_convert",
        "artist": "",
        "charter": "",
        "generatedBy": "Chart_Converter By Jere (Enhanced)"
    }
}

# Event Templates
EVENT_TEMPLATES = {
    "FocusCamera": {"char": None, "x": 0, "y": 0, "duration": 4, "ease": "CLASSIC"},
    "ZoomCamera": {"zoom": 1.0, "duration": 4, "ease": "CLASSIC", "mode": ""},
    "SetCameraBop": {"rate": 4, "intensity": 1},
    "PlayAnimation": {"target": "", "anim": "", "force": True},
    "ScrollSpeed": {"scroll": 1.0, "duration": 4, "ease": "linear"},
    "SetHealthIcon": {"char": "", "id": "", "scale": 1, "flipX": False}
}

# Custom Exceptions
class ChartConversionError(Exception):
    pass

class InvalidChartFormatError(ChartConversionError):
    pass

class MissingMetadataError(ChartConversionError):
    pass

# Utility Functions
def write_to_log(message):
    """Enhanced logging with timestamps"""
    os.makedirs(LOG_FILE_DIR, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE_NAME, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")

def deep_copy_template(template):
    """Create a deep copy of template to avoid reference issues"""
    return json.loads(json.dumps(template))

def sort_by_time(obj):
    return obj['t'] if isinstance(obj, dict) else obj[0]

def calculate_crochet(bpm):
    if bpm == 0:
        return 0
    return 60000.0 / bpm

def load_json(path):
    """Enhanced JSON loading with validation"""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                raise InvalidChartFormatError(f"Invalid JSON format in {path}")
            return data
    except json.JSONDecodeError as e:
        raise InvalidChartFormatError(f"JSON decode error in {path}: {e}")
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {path}")

def save_json(obj, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=4, ensure_ascii=False)

def validate_event(event_type, event_data):
    """Validate and enhance event data using templates"""
    if event_type in EVENT_TEMPLATES:
        template = EVENT_TEMPLATES[event_type]
        if not isinstance(event_data, dict):
            event_data = {}
        
        # Fill missing values with defaults
        for key, default_value in template.items():
            if key not in event_data:
                event_data[key] = default_value
    return event_data

def adjust_scroll_speed(speed, from_format, to_format):
    """Calibrate scroll speed between different chart formats"""
    try:
        speed = float(speed)
    except (ValueError, TypeError):
        speed = 1.5
    
    if from_format == "psych" and to_format == "vslice":
        # Psych Engine tends to have higher scroll speeds
        return max(0.1, speed * 0.8)
    elif from_format == "vslice" and to_format == "psych":
        # Adjust for Psych Engine's different scaling
        return speed * 1.25
    return speed

def transform_note_data(note_data, must_hit_section, format_direction):
    """Transform note data lanes between formats with proper mapping"""
    data = note_data
    
    if format_direction == "vslice_to_psych":
        # VSlice to Psych: Handle mustHitSection logic
        # In Psych: 0-3 = left side, 4-7 = right side
        # mustHitSection determines which side BF is on
        if not must_hit_section:
            # If not mustHitSection, BF is on left (0-3), opponent on right (4-7)
            if data < 4:  # Note originally for left side (BF)
                data = data + 4  # Move to right side
            elif data >= 4:  # Note originally for right side (opponent)
                data = data - 4  # Move to left side
    elif format_direction == "psych_to_vslice":
        # Psych to VSlice: Direct mapping, handled by mustHitSection in sections
        pass
    
    return data

def recursive_find_charts(root, mode="vslice2psych"):
    """Enhanced chart finding with better error handling"""
    pairs = []
    song_groups = {}
    common_difficulties = ["easy", "normal", "hard", "insane", "expert", "hardest", "master", "mad"]

    try:
        for dirpath, _, filenames in os.walk(root):
            if mode == "vslice2psych":
                chart_candidates = {}
                meta_candidates = {}
                
                for f in filenames:
                    if "-chart" in f and f.endswith(".json"):
                        key = f.replace("-chart.json", "").replace("-chart-", "")
                        chart_candidates[key] = f
                    elif "-metadata" in f and f.endswith(".json"):
                        key = f.replace("-metadata.json", "").replace("-metadata-", "")
                        meta_candidates[key] = f

                for chart_key, chart_file in chart_candidates.items():
                    if chart_key in meta_candidates:
                        meta_file = meta_candidates[chart_key]
                        pairs.append((
                            os.path.join(dirpath, chart_file),
                            os.path.join(dirpath, meta_file),
                            dirpath, chart_file, meta_file
                        ))
                        
            elif mode == "psych2vslice":
                for fname in filenames:
                    if fname.endswith(".json"):
                        base_name = os.path.splitext(fname)[0]
                        parts = base_name.split('-')
                        
                        inferred_difficulty = "normal"
                        song_id_from_filename = base_name

                        if len(parts) > 1 and parts[-1].lower() in common_difficulties:
                            inferred_difficulty = parts[-1].lower()
                            song_id_from_filename = "-".join(parts[:-1])
                        
                        group_key = os.path.join(dirpath, song_id_from_filename)
                        
                        if group_key not in song_groups:
                            song_groups[group_key] = {
                                "dirpath": dirpath,
                                "song_id": song_id_from_filename,
                                "difficulties": {}
                            }
                        song_groups[group_key]["difficulties"][inferred_difficulty] = os.path.join(dirpath, fname)
    except Exception as e:
        write_to_log(f"Error scanning directory {root}: {e}")
        
    if mode == "psych2vslice":
        return [(sg_data["dirpath"], sg_data["song_id"], sg_data["difficulties"]) 
                for sg_data in song_groups.values()]
    
    return pairs

def get_section_must_hits(focus_camera_events, time_changes, base_bpm, last_note_time):
    """Enhanced section must-hit calculation with better accuracy"""
    section_must_hits = []
    
    if not focus_camera_events:
        return [True]  # Default to mustHit if no focus events
    
    time = 0
    focus_idx = 0
    tc_idx = 0
    bpm = base_bpm
    max_focus_time = focus_camera_events[-1]['t'] if focus_camera_events else 0
    
    while time < max_focus_time + (calculate_crochet(bpm) * SECTION_BEATS):
        # Update BPM if needed
        while tc_idx < len(time_changes) and time >= time_changes[tc_idx]['t']:
            bpm = time_changes[tc_idx]['bpm']
            tc_idx += 1
            
        # Get current focus camera event
        while focus_idx + 1 < len(focus_camera_events) and time >= focus_camera_events[focus_idx + 1]['t']:
            focus_idx += 1
            
        fc_event = focus_camera_events[focus_idx]
        
        # Enhanced character value extraction
        char_val = None
        v = fc_event.get('v', {})
        if isinstance(v, dict) and 'char' in v:
            char_val = v['char']
        elif not isinstance(v, dict) and v is not None:
            char_val = v
            
        must_hit = (str(char_val) == "0") if char_val is not None else True
        section_must_hits.append(must_hit)
        
        section_time = calculate_crochet(bpm) * SECTION_BEATS
        time += section_time
    
    return section_must_hits if section_must_hits else [True]

def create_base_sections(time_changes, base_bpm, last_note_time, section_must_hits):
    """Enhanced section creation with better BPM handling"""
    base_sections = []
    section_times = []
    bpm = base_bpm
    last_bpm = base_bpm
    time = 0
    tc_idx = 0
    section_index = 0
    
    # Ensure we have enough sections to cover all notes plus buffer
    end_time = last_note_time + (calculate_crochet(base_bpm) * SECTION_BEATS) + 1000
    
    while time < end_time:
        # Update BPM if there's a time change at this point
        while tc_idx < len(time_changes) and time >= time_changes[tc_idx]['t']:
            bpm = time_changes[tc_idx]['bpm']
            tc_idx += 1
        
        # Create section with proper mustHitSection value
        must_hit = (section_must_hits[section_index] 
                   if section_index < len(section_must_hits) 
                   else section_must_hits[-1] if section_must_hits else True)
        
        sec = {
            "sectionNotes": [],
            "sectionBeats": SECTION_BEATS,
            "mustHitSection": must_hit,
        }
        
        # Add BPM change if needed
        if abs(last_bpm - bpm) > 0.001:  # Use epsilon for float comparison
            sec["changeBPM"] = True
            sec["bpm"] = bpm
            
        last_bpm = bpm
        base_sections.append(sec)
        section_times.append(time)
        
        section_time = calculate_crochet(bpm) * SECTION_BEATS
        time += section_time
        section_index += 1
    
    return base_sections, section_times

def format_event_for_psych(event):
    """Enhanced event formatting with better parameter handling"""
    event_name = str(event.get('e', 'UnknownEvent'))
    v = event.get('v', {})
    
    # Validate event data
    v = validate_event(event_name, v)
    
    value1 = ""
    value2 = ""

    if event_name == "FocusCamera" and isinstance(v, dict):
        value1 = str(v.get('char', ''))
        params = []
        for param in ['x', 'y', 'duration', 'ease']:
            val = v.get(param)
            if val is not None and str(val) != "" and str(val) != "0":
                params.append(str(val))
        value2 = "|".join(params) if params else ""
        
    elif event_name == "ZoomCamera" and isinstance(v, dict):
        value1 = str(v.get('zoom', ''))
        params = []
        for param in ['duration', 'mode', 'ease']:
            val = v.get(param)
            if val is not None and str(val) != "":
                params.append(str(val))
        value2 = "|".join(params)
        
    elif event_name == "SetCameraBop" and isinstance(v, dict):
        value1 = str(v.get('rate', ''))
        value2 = str(v.get('intensity', ''))
        
    elif event_name == "PlayAnimation" and isinstance(v, dict):
        value1 = str(v.get('target', ''))
        anim = str(v.get('anim', ''))
        force = v.get('force')
        if force is not None:
            value2 = f"{anim}|{str(force)}"
        else:
            value2 = anim
            
    elif event_name in ("Change Scroll Speed", "ScrollSpeed") and isinstance(v, dict):
        value1 = str(v.get('scroll', v.get('speed', '')))
        params = []
        for param in ['duration', 'ease', 'strumline', 'absolute']:
            val = v.get(param)
            if val is not None and str(val) != "":
                params.append(str(val))
        value2 = "|".join(params)
        
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

def is_section_focus_camera(event, section_times, tolerance=100.0):
    """Enhanced section focus camera detection with better tolerance"""
    if event.get('e') != 'FocusCamera':
        return False
        
    t = float(event.get('t', -1))
    v = event.get('v', {})
    
    # Parse event values
    if not isinstance(v, dict):
        char = v if isinstance(v, (int, str)) else None
        x = y = 0
        duration = 4
        ease = "CLASSIC"
    else:
        char = v.get('char')
        try:
            x = float(v.get('x', 0))
            y = float(v.get('y', 0))
            duration = float(v.get('duration', 4))
        except (ValueError, TypeError):
            x = y = 0
            duration = 4
        ease = str(v.get('ease', "CLASSIC")).strip().upper()
    
    # Check if it's a basic section focus camera (default values)
    is_basic = (abs(x) < 0.001 and abs(y) < 0.001 and 
                abs(duration - 4) < 0.001 and ease == "CLASSIC" and 
                char in (0, 1, "0", "1"))
    
    if not is_basic:
        return False
    
    # Check if timing matches any section start
    for st in section_times:
        if abs(t - st) < tolerance:
            return True
    
    return False

def vslice_to_psych(vslice_chart, vslice_metadata):
    """Enhanced VSlice to Psych conversion with better error handling"""
    try:
        # Validate input data
        if not isinstance(vslice_chart, dict) or not isinstance(vslice_metadata, dict):
            raise InvalidChartFormatError("Invalid chart or metadata format")
        
        # Extract difficulties with fallback
        difficulties = vslice_metadata.get('playData', {}).get('difficulties', [])
        if not difficulties:
            difficulties = ['normal']
            write_to_log("WARNING: No difficulties found in VSlice metadata. Defaulting to ['normal'].")
        
        # Process time changes
        time_changes = sorted(vslice_metadata.get('timeChanges', []), key=lambda t: t.get('t', 0))
        base_bpm = time_changes[0].get('bpm', 120) if time_changes else 120
        
        # Get stage mapping
        stage = vslice_metadata.get('playData', {}).get('stage', 'mainStage')
        stage = STAGE_TO_PSYCH.get(stage, stage)
        
        # Process notes for each difficulty
        notes_map = {}
        last_note_time = 0
        
        for diff in difficulties:
            notes = vslice_chart.get('notes', {}).get(diff, [])
            notes = sorted(notes, key=sort_by_time)
            notes_map[diff] = notes
            if notes:
                last_note_time = max(last_note_time, notes[-1]['t'])
        
        # Process events
        all_events = sorted(vslice_chart.get('events', []), key=sort_by_time)
        focus_camera_events = [
            e for e in all_events 
            if e.get('e') == 'FocusCamera' and (
                e.get('v') in (0, 1, "0", "1") or 
                (isinstance(e.get('v'), dict) and 'char' in e['v'])
            )
        ]
        
        # Generate sections
        section_must_hits = get_section_must_hits(focus_camera_events, time_changes, base_bpm, last_note_time)
        base_sections, section_times = create_base_sections(time_changes, base_bpm, last_note_time, section_must_hits)
        
        write_to_log(f"Generated {len(base_sections)} sections for conversion")
        write_to_log(f"Section times: {[round(st, 2) for st in section_times[:10]]}{'...' if len(section_times) > 10 else ''}")
        
        # Process file events
        file_events = []
        for e in all_events:
            if e.get('e') == 'FocusCamera':
                if is_section_focus_camera(e, section_times, tolerance=100.0):
                    write_to_log(f"SKIP section focus: t={e.get('t')}, v={e.get('v')}")
                    continue
                else:
                    write_to_log(f"KEEP custom focus: t={e.get('t')}, v={e.get('v')}")
            
            event_fields = format_event_for_psych(e)
            file_events.append([e.get('t', 0), [event_fields]])
        
        file_events.sort(key=lambda ev: ev[0])
        
        # Generate Psych charts for each difficulty
        psych_charts = {}
        for diff in difficulties:
            # Create chart from template
            chart_data = deep_copy_template(PSYCH_CHART_TEMPLATE)
            
            # Get scroll speed with calibration
            scroll_speed = vslice_chart.get('scrollSpeed', {}).get(
                diff, vslice_chart.get('scrollSpeed', {}).get('default', 1.5)
            )
            scroll_speed = adjust_scroll_speed(scroll_speed, "vslice", "psych")
            
            # Process notes
            notes = notes_map.get(diff, [])
            section_data = [dict(section, sectionNotes=[]) for section in base_sections]
            
            note_sec = 0
            for note in notes:
                # Find correct section for this note
                while (note_sec + 1 < len(section_times) and 
                       section_times[note_sec + 1] <= note['t']):
                    note_sec += 1
                
                # Transform note data
                must_hit = (section_data[note_sec]["mustHitSection"] 
                           if 0 <= note_sec < len(section_data) else True)
                
                transformed_data = transform_note_data(
                    note.get('d', 0), must_hit, "vslice_to_psych"
                )
                
                psych_note = [
                    note.get('t', 0),
                    transformed_data,
                    note.get('l', 0)
                ]
                
                # Add note type if present
                if note.get('k') and note['k'] not in ("", "normal"):
                    psych_note.append(note['k'])
                
                if 0 <= note_sec < len(section_data):
                    section_data[note_sec]["sectionNotes"].append(psych_note)
            
            # Set chart metadata
            characters = vslice_metadata.get('playData', {}).get('characters', {})
            chart_data["song"].update({
                "song": vslice_metadata.get('songName', 'Unknown Song'),
                "notes": section_data,
                "events": file_events,
                "bpm": base_bpm,
                "speed": scroll_speed,
                "player1": characters.get('player', 'bf'),
                "player2": characters.get('opponent', 'dad'),
                "gfVersion": characters.get('girlfriend', ''),
                "stage": stage,
                "artist": vslice_metadata.get('artist', 'Unknown Artist'),
                "charter": vslice_metadata.get('charter', 'Unknown Charter')
            })
            
            psych_charts[diff] = chart_data
        
        write_to_log(f"Successfully converted VSlice chart with {len(difficulties)} difficulties")
        return psych_charts
        
    except Exception as e:
        write_to_log(f"Error in vslice_to_psych conversion: {e}")
        raise ChartConversionError(f"VSlice to Psych conversion failed: {e}")

def psych_to_vslice(psych_chart, difficulty_name=None):
    """Enhanced Psych to VSlice conversion with better data handling"""
    try:
        # Validate input
        if not isinstance(psych_chart, dict) or 'song' not in psych_chart:
            raise InvalidChartFormatError("Invalid Psych Engine chart format")
        
        songData = psych_chart['song']
        
        # Initialize output structures
        events = []
        notes = []
        timeChanges = []
        
        # Process time changes and sections
        time = 0
        bpm = songData.get('bpm', 120)
        timeChanges.append({'t': 0, 'bpm': bpm})
        
        # Determine initial focus camera
        first_section_must_hit = True
        if songData.get('notes') and len(songData['notes']) > 0:
            first_section_must_hit = songData['notes'][0].get('mustHitSection', True)
        
        lastMustHit = first_section_must_hit
        events.append({
            't': 0, 
            'e': 'FocusCamera', 
            'v': {'char': 0 if lastMustHit else 1}
        })
        
        # Process sections
        if songData.get('notes'):
            for section in songData['notes']:
                # Process section notes
                if section.get('sectionNotes'):
                    for note in section['sectionNotes']:
                        vsliceNote = {
                            't': note[0],
                            'd': transform_note_data(note[1], section.get('mustHitSection', True), "psych_to_vslice")
                        }
                        
                        # Add sustain length if present
                        if len(note) > 2 and note[2] > 0:
                            vsliceNote['l'] = note[2]
                        
                        # Add note type if present
                        if len(note) > 3 and note[3]:
                            vsliceNote['k'] = note[3]
                        
                        notes.append(vsliceNote)
                
                # Handle BPM changes
                section_duration = calculate_crochet(bpm) * SECTION_BEATS
                if section.get('changeBPM') and 'bpm' in section:
                    bpm = section['bpm']
                    timeChanges.append({'t': time, 'bpm': bpm})
                
                # Handle mustHitSection changes
                current_must_hit = section.get('mustHitSection', True)
                if lastMustHit != current_must_hit:
                    events.append({
                        't': time, 
                        'e': 'FocusCamera', 
                        'v': {'char': 0 if current_must_hit else 1}
                    })
                    lastMustHit = current_must_hit
                
                time += section_duration
        
        # Process custom events
        if songData.get('events'):
            for event in songData['events']:
                event_time = event[0]
                if len(event) > 1 and isinstance(event[1], list):
                    for subevent_data in event[1]:
                        event_name = subevent_data[0] if len(subevent_data) > 0 else 'Unknown'
                        value1 = subevent_data[1] if len(subevent_data) > 1 else ''
                        value2 = subevent_data[2] if len(subevent_data) > 2 else ''
                        
                        # Enhanced event processing
                        ev = {'t': event_time, 'e': event_name}
                        
                        # Create appropriate event structure based on type
                        if event_name == "FocusCamera" and value1 in ('0', '1', 0, 1):
                            ev['v'] = {'char': int(value1)}
                        elif event_name == "ZoomCamera":
                            ev['v'] = {'zoom': float(value1) if value1 else 1.0}
                            if value2:
                                params = value2.split('|')
                                if len(params) > 0 and params[0]:
                                    ev['v']['duration'] = float(params[0])
                                if len(params) > 1 and params[1]:
                                    ev['v']['mode'] = params[1]
                                if len(params) > 2 and params[2]:
                                    ev['v']['ease'] = params[2]
                        else:
                            ev['v'] = {'value1': value1, 'value2': value2}
                        
                        events.append(ev)
        
        # Sort and organize data
        events.sort(key=sort_by_time)
        notes.sort(key=sort_by_time)
        
        # Determine difficulty and create structures
        if difficulty_name:
            diffs = [difficulty_name]
        else:
            diffs = ['normal']
            write_to_log("WARNING: No specific difficulty provided for Psych to VSlice conversion. Defaulting to ['normal'].")
        
        # Adjust scroll speed
        original_speed = songData.get('speed', 1.5)
        adjusted_speed = adjust_scroll_speed(original_speed, "psych", "vslice")
        
        scrollSpeed = {diff: adjusted_speed for diff in diffs}
        notesMap = {diff: notes for diff in diffs}
        
        # Map stage
        stage = songData.get('stage', 'mainStage')
        stage = STAGE_TO_VSLICE.get(stage, stage)
        
        # Create chart and metadata from templates
        chart = deep_copy_template(VSLICE_CHART_TEMPLATE)
        chart.update({
            'scrollSpeed': scrollSpeed,
            'events': events,
            'notes': notesMap,
            'generatedBy': songData.get('generatedBy', 'Psych Engine Chart Editor V-Slice Exporter')
        })
        
        metadata = deep_copy_template(VSLICE_METADATA_TEMPLATE)
        metadata.update({
            'songName': songData.get('song', 'Unknown Song'),
            'artist': songData.get('artist', songData.get('composer', 'Unknown Artist')),
            'charter': songData.get('charter', 'Unknown Charter'),
            'timeChanges': timeChanges,
            'generatedBy': songData.get('generatedBy', 'Psych Engine Chart Editor V-Slice Exporter')
        })
        
        # Update playData
        metadata['playData'].update({
            'difficulties': diffs,
            'characters': {
                'player': songData.get('player1', 'bf'),
                'girlfriend': songData.get('gfVersion', ''),
                'opponent': songData.get('player2', 'dad')
            },
            'stage': stage
        })
        
        write_to_log(f"Successfully converted Psych chart to VSlice format")
        return {'chart': chart, 'metadata': metadata}
        
    except Exception as e:
        write_to_log(f"Error in psych_to_vslice conversion: {e}")
        raise ChartConversionError(f"Psych to VSlice conversion failed: {e}")

# The GUI class would remain largely the same, but with enhanced error handling
class ConverterGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.tk.call('tk', 'scaling', 1.3)
        self.title("FNF Chart Converter - VSlice ⬌ Psych Engine (Enhanced)")
        self.configure(bg="#23232b")
        self.geometry("750x450")
        self.resizable(False, False)
        
        # Variables
        self.operation = tk.StringVar(value="vslice2psych")
        self.chart_file = tk.StringVar()
        self.meta_file = tk.StringVar()
        self.psych_file = tk.StringVar()
        self.difficulty = tk.StringVar()
        self.outdir = tk.StringVar(value=os.getcwd())
        self.batch_folder = tk.StringVar()
        self.status_msg = tk.StringVar()
        
        # Enhanced styling
        self.style = ttk.Style(self)
        self.style.theme_use('clam')
        self.configure_styles()
        
        self.create_widgets()
        self.update_mode()

    def configure_styles(self):
        """Enhanced styling configuration"""
        self.style.configure('TFrame', background='#23232b')
        self.style.configure('TLabel', background='#23232b', foreground='#e0e0e0', font=("Segoe UI", 12))
        self.style.configure('Title.TLabel', background='#23232b', foreground='#f9c74f', font=("Segoe UI", 18, "bold"))
        self.style.configure('TButton', font=("Segoe UI", 11, "bold"), padding=5, background='#5e7d82')
        self.style.map('TButton', background=[('active', '#7a9b9f')])
        self.style.configure('TRadiobutton', background='#23232b', foreground='#e0e0e0', font=("Segoe UI", 11))
        self.style.configure('TEntry', fieldbackground='#24263d', foreground='#f0f0f0', font=("Segoe UI", 11), borderwidth=0)

    def create_widgets(self):
        """Create GUI widgets with enhanced layout"""
        frm = ttk.Frame(self, padding=(18, 10, 18, 10), style='TFrame')
        frm.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Title
        ttk.Label(frm, text="FNF Chart Converter (Enhanced)", style='Title.TLabel').grid(
            row=0, column=0, columnspan=4, pady=(0, 16), sticky="ew"
        )
        
        # Mode selection
        ttk.Label(frm, text="Modo de conversión:", font=("Segoe UI", 12, "bold")).grid(
            row=1, column=0, sticky="w", pady=(0, 6)
        )
        
        rb1 = ttk.Radiobutton(frm, text="VSlice → Psych", variable=self.operation, 
                             value="vslice2psych", command=self.update_mode)
        rb2 = ttk.Radiobutton(frm, text="Psych → VSlice", variable=self.operation, 
                             value="psych2vslice", command=self.update_mode)
        rb3 = ttk.Radiobutton(frm, text="Batch VSlice → Psych", variable=self.operation, 
                             value="batch-vslice2psych", command=self.update_mode)
        rb4 = ttk.Radiobutton(frm, text="Batch Psych → VSlice", variable=self.operation, 
                             value="batch-psych2vslice", command=self.update_mode)
        
        rb1.grid(row=1, column=1, sticky="w", padx=4)
        rb2.grid(row=1, column=2, sticky="w", padx=4)
        rb3.grid(row=2, column=1, sticky="w", padx=4, pady=(0, 12))
        rb4.grid(row=2, column=2, sticky="w", padx=4, pady=(0, 12))
        
        # File selection widgets (to be shown/hidden based on mode)
        self.lbl_chart = ttk.Label(frm, text="VSlice Chart (.json):")
        self.ent_chart = ttk.Entry(frm, textvariable=self.chart_file, width=38)
        self.btn_chart = ttk.Button(frm, text="Buscar...", command=self.browse_chart)
        
        self.lbl_meta = ttk.Label(frm, text="VSlice Metadata (.json):")
        self.ent_meta = ttk.Entry(frm, textvariable=self.meta_file, width=38)
        self.btn_meta = ttk.Button(frm, text="Buscar...", command=self.browse_meta)
        
        self.lbl_psych = ttk.Label(frm, text="Psych Chart (.json):")
        self.ent_psych = ttk.Entry(frm, textvariable=self.psych_file, width=38)
        self.btn_psych = ttk.Button(frm, text="Buscar...", command=self.browse_psych)
        
        self.lbl_diff = ttk.Label(frm, text="Dificultad (opcional):")
        self.ent_diff = ttk.Entry(frm, textvariable=self.difficulty, width=18)
        
        self.lbl_batch = ttk.Label(frm, text="Carpeta raíz de charts:")
        self.ent_batch = ttk.Entry(frm, textvariable=self.batch_folder, width=38)
        self.btn_batch = ttk.Button(frm, text="Buscar...", command=self.browse_batch)
        
        # Output directory
        ttk.Label(frm, text="Carpeta salida:").grid(row=9, column=0, sticky="w", pady=(12, 3))
        out_ent = ttk.Entry(frm, textvariable=self.outdir, width=38)
        out_ent.grid(row=9, column=1, padx=5, columnspan=2, sticky="ew")
        ttk.Button(frm, text="Buscar...", command=self.browse_outdir).grid(row=9, column=3, sticky="w")
        
        # Convert button
        self.convert_btn = ttk.Button(frm, text="Convertir", command=self.convert, style='TButton')
        self.convert_btn.grid(row=11, column=0, columnspan=4, pady=18, ipadx=10, sticky="ew")
        
        # Status label
        self.status = ttk.Label(self, textvariable=self.status_msg, foreground="#00ff55", 
                               font=("Segoe UI", 12, "italic"), background="#23232b")
        self.status.pack(side="bottom", fill="x", pady=(2, 8), padx=14, anchor="s")
        
        # Configure grid weights
        frm.grid_columnconfigure(1, weight=1)
        frm.grid_columnconfigure(2, weight=1)

    def update_mode(self):
        """Update widget visibility based on selected mode"""
        # Hide all mode-specific widgets
        for w in [
            self.lbl_chart, self.ent_chart, self.btn_chart,
            self.lbl_meta, self.ent_meta, self.btn_meta,
            self.lbl_psych, self.ent_psych, self.btn_psych,
            self.lbl_diff, self.ent_diff,
            self.lbl_batch, self.ent_batch, self.btn_batch
        ]:
            w.grid_remove()
        
        op = self.operation.get()
        row_start = 4
        
        if op == "vslice2psych":
            self.lbl_chart.grid(row=row_start, column=0, sticky="w", pady=4)
            self.ent_chart.grid(row=row_start, column=1, columnspan=2, padx=5, pady=2, sticky="ew")
            self.btn_chart.grid(row=row_start, column=3, sticky="w")
            row_start += 1
            
            self.lbl_meta.grid(row=row_start, column=0, sticky="w", pady=4)
            self.ent_meta.grid(row=row_start, column=1, columnspan=2, padx=5, pady=2, sticky="ew")
            self.btn_meta.grid(row=row_start, column=3, sticky="w")
            
        elif op == "psych2vslice":
            self.lbl_psych.grid(row=row_start, column=0, sticky="w", pady=4)
            self.ent_psych.grid(row=row_start, column=1, columnspan=2, padx=5, pady=2, sticky="ew")
            self.btn_psych.grid(row=row_start, column=3, sticky="w")
            row_start += 1
            
            self.lbl_diff.grid(row=row_start, column=0, sticky="w", pady=4)
            self.ent_diff.grid(row=row_start, column=1, columnspan=2, padx=5, pady=2, sticky="ew")
            
        else:  # Batch modes
            self.lbl_batch.grid(row=row_start, column=0, sticky="w", pady=4)
            self.ent_batch.grid(row=row_start, column=1, columnspan=2, padx=5, pady=2, sticky="ew")
            self.btn_batch.grid(row=row_start, column=3, sticky="w")

    def browse_chart(self):
        fname = filedialog.askopenfilename(
            title="Seleccionar VSlice Chart",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if fname:
            self.chart_file.set(fname)

    def browse_meta(self):
        fname = filedialog.askopenfilename(
            title="Seleccionar VSlice Metadata", 
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if fname:
            self.meta_file.set(fname)

    def browse_psych(self):
        fname = filedialog.askopenfilename(
            title="Seleccionar Psych Chart",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if fname:
            self.psych_file.set(fname)

    def browse_outdir(self):
        dirname = filedialog.askdirectory(title="Seleccionar carpeta de salida")
        if dirname:
            self.outdir.set(dirname)

    def browse_batch(self):
        dirname = filedialog.askdirectory(title="Seleccionar carpeta raíz de charts")
        if dirname:
            self.batch_folder.set(dirname)

    def convert(self):
        """Enhanced conversion with better error handling and user feedback"""
        try:
            op = self.operation.get()
            outdir = self.outdir.get()
            
            if not outdir:
                messagebox.showerror("Error", "Por favor, selecciona una carpeta de salida.")
                return
            
            self.status_msg.set("Procesando, por favor espera...")
            self.update_idletasks()
            
            if op == "vslice2psych":
                self.convert_vslice_to_psych(outdir)
            elif op == "psych2vslice":
                self.convert_psych_to_vslice(outdir)
            elif op == "batch-vslice2psych":
                self.batch_convert_vslice_to_psych(outdir)
            elif op == "batch-psych2vslice":
                self.batch_convert_psych_to_vslice(outdir)
                
        except (FileNotFoundError, InvalidChartFormatError, MissingMetadataError) as e:
            messagebox.showerror("Error de Conversión", str(e))
            self.status_msg.set("Error en la conversión.")
            write_to_log(f"Conversion error: {e}")
        except Exception as e:
            messagebox.showerror("Error Inesperado", f"Ocurrió un error inesperado: {e}")
            self.status_msg.set("Error inesperado.")
            write_to_log(f"Unexpected error: {e}")
        finally:
            self.update_idletasks()

    def convert_vslice_to_psych(self, outdir):
        """Convert single VSlice chart to Psych format"""
        if not self.chart_file.get() or not self.meta_file.get():
            raise MissingMetadataError("Debes seleccionar ambos archivos: chart.json y metadata.json")
        
        vslice_chart = load_json(self.chart_file.get())
        vslice_metadata = load_json(self.meta_file.get())
        psych_charts = vslice_to_psych(vslice_chart, vslice_metadata)
        
        count = 0
        for diff, chart_data in psych_charts.items():
            out_path = os.path.join(outdir, f"psych_{diff}.json")
            save_json(chart_data, out_path)
            count += 1
        
        self.status_msg.set(
            f"¡Conversión exitosa! Se crearon {count} archivos Psych en '{outdir}'. "
            f"Revisa '{LOG_FILE_NAME}' para detalles."
        )

    def convert_psych_to_vslice(self, outdir):
        """Convert single Psych chart to VSlice format"""
        if not self.psych_file.get():
            raise MissingMetadataError("Debes seleccionar un archivo Psych Engine chart.json")
        
        psych_chart = load_json(self.psych_file.get())
        diff_override = self.difficulty.get().strip() if self.difficulty.get() else None
        vslice_pack = psych_to_vslice(psych_chart, diff_override)
        
        save_json(vslice_pack['chart'], os.path.join(outdir, "chart.json"))
        save_json(vslice_pack['metadata'], os.path.join(outdir, "metadata.json"))
        
        self.status_msg.set(
            f"¡Exportación exitosa! chart.json y metadata.json generados en '{outdir}'. "
            f"Revisa '{LOG_FILE_NAME}' para detalles."
        )

    def batch_convert_vslice_to_psych(self, outdir):
        """Batch convert VSlice charts to Psych format"""
        folder = self.batch_folder.get()
        if not folder or not os.path.isdir(folder):
            raise FileNotFoundError("Selecciona una carpeta raíz de entrada válida para el batch.")
        
        chart_pairs = recursive_find_charts(folder, "vslice2psych")
        if not chart_pairs:
            messagebox.showinfo("Información", f"No se encontraron pares de charts VSlice en '{folder}'.")
            self.status_msg.set("Batch terminado: No se encontraron charts para convertir.")
            return
        
        batch_count = 0
        errors = 0
        
        for chart_path, meta_path, song_dir, chart_fn, meta_fn in chart_pairs:
            try:
                vslice_chart = load_json(chart_path)
                vslice_metadata = load_json(meta_path)
                psych_charts = vslice_to_psych(vslice_chart, vslice_metadata)

                # Generate output folder name
                current_chart_base = self.extract_chart_base_name(chart_fn)
                song_parent = os.path.dirname(song_dir)
                rel_parent = os.path.relpath(song_parent, folder)
                
                if rel_parent == ".":
                    out_folder = os.path.join(outdir, current_chart_base)
                else:
                    out_folder = os.path.join(outdir, rel_parent, current_chart_base)
                
                os.makedirs(out_folder, exist_ok=True)

                # Save converted charts
                for diff, chart_data in psych_charts.items():
                    json_file = f"{current_chart_base}-{diff}.json"
                    out_path = os.path.join(out_folder, json_file)
                    save_json(chart_data, out_path)
                    batch_count += 1
                
                self.status_msg.set(f"Batch VSlice→Psych: {batch_count} archivos generados...")
                self.update_idletasks()
                
            except Exception as inner_e:
                errors += 1
                log_message = f"ERROR: Falló conversión VSlice→Psych para '{os.path.basename(song_dir)}': {inner_e}"
                write_to_log(log_message)
                continue
        
        final_msg = f"Batch terminado: {batch_count} archivos generados"
        if errors > 0:
            final_msg += f" ({errors} errores)"
        final_msg += f" en '{outdir}'. Revisa '{LOG_FILE_NAME}' para detalles."
        self.status_msg.set(final_msg)

    def batch_convert_psych_to_vslice(self, outdir):
        """Batch convert Psych charts to VSlice format"""
        folder = self.batch_folder.get()
        if not folder or not os.path.isdir(folder):
            raise FileNotFoundError("Selecciona una carpeta raíz de entrada válida para el batch.")
        
        song_groups = recursive_find_charts(folder, "psych2vslice")
        if not song_groups:
            messagebox.showinfo("Información", f"No se encontraron charts Psych en '{folder}'.")
            self.status_msg.set("Batch terminado: No se encontraron charts para convertir.")
            return
        
        batch_count = 0
        errors = 0
        common_difficulties_order = ["easy", "normal", "hard", "insane", "expert", "hardest", "master", "mad"]
        
        for song_dir, song_id, difficulties_map in song_groups:
            try:
                # Sort difficulties
                sorted_difficulties = sorted(
                    difficulties_map.keys(),
                    key=lambda x: (common_difficulties_order.index(x) 
                                  if x in common_difficulties_order 
                                  else len(common_difficulties_order))
                )
                
                if not sorted_difficulties:
                    write_to_log(f"WARNING: No difficulties found for {song_id}")
                    continue
                
                # Convert primary chart
                primary_psych_path = difficulties_map[sorted_difficulties[0]]
                primary_psych_chart = load_json(primary_psych_path)
                initial_vslice_pack = psych_to_vslice(primary_psych_chart, sorted_difficulties[0])
                
                consolidated_chart = initial_vslice_pack['chart']
                consolidated_metadata = initial_vslice_pack['metadata']
                
                # Clear and rebuild for all difficulties
                consolidated_chart['notes'] = {}
                consolidated_chart['scrollSpeed'] = {}
                consolidated_metadata['playData']['difficulties'] = []
                
                # Process all difficulties
                for difficulty in sorted_difficulties:
                    psych_path = difficulties_map[difficulty]
                    psych_chart = load_json(psych_path)
                    temp_vslice_pack = psych_to_vslice(psych_chart, difficulty)
                    
                    consolidated_chart['notes'][difficulty] = temp_vslice_pack['chart']['notes'][difficulty]
                    consolidated_chart['scrollSpeed'][difficulty] = temp_vslice_pack['chart']['scrollSpeed'][difficulty]
                    
                    if difficulty not in consolidated_metadata['playData']['difficulties']:
                        consolidated_metadata['playData']['difficulties'].append(difficulty)
                
                # Sort difficulties in metadata
                consolidated_metadata['playData']['difficulties'].sort(
                    key=lambda x: (common_difficulties_order.index(x) 
                                  if x in common_difficulties_order 
                                  else len(common_difficulties_order))
                )
                
                # Create output directory
                rel_path = os.path.relpath(song_dir, folder)
                out_song_folder = os.path.join(outdir, rel_path, song_id)
                os.makedirs(out_song_folder, exist_ok=True)
                
                # Save files
                chart_filename = f"{song_id}-chart.json"
                metadata_filename = f"{song_id}-metadata.json"
                
                save_json(consolidated_chart, os.path.join(out_song_folder, chart_filename))
                save_json(consolidated_metadata, os.path.join(out_song_folder, metadata_filename))
                
                batch_count += 1
                self.status_msg.set(f"Batch Psych→VSlice: {batch_count} canciones convertidas...")
                self.update_idletasks()
                
            except Exception as inner_e:
                errors += 1
                log_message = f"ERROR: Falló conversión Psych→VSlice para '{song_id}': {inner_e}"
                write_to_log(log_message)
                continue
        
        final_msg = f"Batch terminado: {batch_count} canciones convertidas"
        if errors > 0:
            final_msg += f" ({errors} errores)"
        final_msg += f" en '{outdir}'. Revisa '{LOG_FILE_NAME}' para detalles."
        self.status_msg.set(final_msg)

    def extract_chart_base_name(self, chart_fn):
        """Extract base name from chart filename with enhanced logic"""
        current_chart_base = ""
        if "-chart-" in chart_fn:
            parts = chart_fn.split("-chart-")
            current_chart_base = f"{parts[0]}-{parts[1].replace('.json', '')}"
        elif "-chart.json" in chart_fn:
            current_chart_base = chart_fn.replace("-chart.json", "")
        else:
            current_chart_base = os.path.splitext(chart_fn)[0]
            if "-chart" in current_chart_base:
                current_chart_base = current_chart_base.rsplit("-chart", 1)[0]
        
        # Handle special cases
        if current_chart_base.lower().endswith("spookymod"):
            current_chart_base = current_chart_base[:-len("spookymod")] + "(spookymix)"
        
        return current_chart_base.strip('-')

if __name__ == "__main__":
    try:
        app = ConverterGUI()
        app.mainloop()
    except Exception as e:
        write_to_log(f"Application startup error: {e}")
        print(f"Error starting application: {e}")