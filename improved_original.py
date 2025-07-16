import json
import os
import sys
import glob
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import datetime

LOG_FILE_DIR = "/storage/emulated/0/charts"
LOG_FILE_NAME = os.path.join(LOG_FILE_DIR, "conversion_log.txt")

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

def write_to_log(message):
    """Mejorado: Logging con timestamps y mejor manejo de errores"""
    try:
        os.makedirs(LOG_FILE_DIR, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE_NAME, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {message}\n")
    except Exception as e:
        print(f"Error writing to log: {e}")

def sort_by_time(obj):
    return obj['t'] if isinstance(obj, dict) else obj[0]

def calculate_crochet(bpm):
    if bpm == 0:
        return 0
    return 60000.0 / bpm

def load_json(path):
    """Mejorado: Mejor validación y manejo de errores"""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError(f"El archivo {path} no contiene un objeto JSON válido")
            return data
    except json.JSONDecodeError as e:
        raise ValueError(f"Error de formato JSON en {path}: {e}")
    except FileNotFoundError:
        raise FileNotFoundError(f"Archivo no encontrado: {path}")
    except Exception as e:
        raise Exception(f"Error inesperado al cargar {path}: {e}")

def save_json(obj, path):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=4, ensure_ascii=False)
    except Exception as e:
        write_to_log(f"Error saving JSON to {path}: {e}")
        raise

def adjust_scroll_speed(speed, from_format, to_format):
    """NUEVO: Calibración de velocidad de scroll entre formatos"""
    try:
        speed = float(speed)
    except (ValueError, TypeError):
        speed = 1.5
        write_to_log(f"WARNING: Invalid scroll speed, defaulting to 1.5")
    
    # Calibración basada en las diferencias observadas entre motores
    if from_format == "psych" and to_format == "vslice":
        # Psych Engine tiende a tener velocidades más altas
        adjusted = max(0.1, speed - 0.5)
        write_to_log(f"Scroll speed adjusted: {speed} -> {adjusted} (Psych to VSlice)")
        return adjusted
    elif from_format == "vslice" and to_format == "psych":
        # Compensar para Psych Engine
        adjusted = speed + 0.5
        write_to_log(f"Scroll speed adjusted: {speed} -> {adjusted} (VSlice to Psych)")
        return adjusted
    
    return speed

def transform_note_data(note_data, must_hit_section, format_direction):
    """NUEVO: Transformación correcta de datos de notas entre formatos"""
    original_data = note_data
    
    if format_direction == "vslice_to_psych":
        # En VSlice: 0-3 = lado izquierdo, 4-7 = lado derecho
        # En Psych: depende de mustHitSection
        # Si mustHitSection=false, BF está en el lado izquierdo (0-3)
        if not must_hit_section:
            if note_data < 4:  # Nota originalmente para BF (lado izquierdo)
                note_data = note_data + 4  # Mover al lado derecho
            elif note_data >= 4:  # Nota originalmente para oponente (lado derecho)
                note_data = note_data - 4  # Mover al lado izquierdo
    elif format_direction == "psych_to_vslice":
        # La transformación inversa se maneja en la lógica de secciones
        pass
    
    if original_data != note_data:
        write_to_log(f"Note data transformed: {original_data} -> {note_data} (mustHit: {must_hit_section})")
    
    return note_data

def recursive_find_charts(root, mode="vslice2psych"):
    """Mejorado: Mejor manejo de errores y logging"""
    pairs = []
    song_groups = {}
    common_difficulties = ["easy", "normal", "hard", "insane", "expert", "hardest", "master", "mad"]

    write_to_log(f"Scanning directory: {root} in mode: {mode}")
    
    try:
        file_count = 0
        for dirpath, _, filenames in os.walk(root):
            file_count += len(filenames)
            
            if mode == "vslice2psych":
                chart_candidates = {f.replace("-chart.json", "").replace("-chart-", ""): f for f in filenames if "-chart" in f and f.endswith(".json")}
                meta_candidates = {f.replace("-metadata.json", "").replace("-metadata-", ""): f for f in filenames if "-metadata" in f and f.endswith(".json")}

                for chart_key, chart_file in chart_candidates.items():
                    if chart_key in meta_candidates:
                        meta_file = meta_candidates[chart_key]
                        pairs.append((os.path.join(dirpath, chart_file), os.path.join(dirpath, meta_file), dirpath, chart_file, meta_file))
                        write_to_log(f"Found VSlice pair: {chart_file} + {meta_file}")
                        
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
        
        write_to_log(f"Scanned {file_count} files total")
        
    except Exception as e:
        write_to_log(f"Error scanning directory {root}: {e}")
        raise
    
    if mode == "psych2vslice":
        result = [(sg_data["dirpath"], sg_data["song_id"], sg_data["difficulties"]) for sg_data in song_groups.values()]
        write_to_log(f"Found {len(result)} Psych song groups")
        return result
    
    write_to_log(f"Found {len(pairs)} VSlice chart pairs")
    return pairs

def get_section_must_hits(focus_camera_events, time_changes, base_bpm, last_note_time):
    """Mejorado: Lógica más robusta para determinar mustHitSection"""
    section_must_hits = []
    
    if not focus_camera_events:
        write_to_log("No focus camera events found, defaulting to mustHit=True")
        return [True]
    
    time = 0
    focus_idx = 0
    tc_idx = 0
    bpm = base_bpm
    max_focus_time = focus_camera_events[-1]['t'] if focus_camera_events else 0
    
    write_to_log(f"Processing {len(focus_camera_events)} focus camera events")
    
    section_count = 0
    while time < max_focus_time + (calculate_crochet(bpm) * SECTION_BEATS):
        # Actualizar BPM si es necesario
        while tc_idx < len(time_changes) and time >= time_changes[tc_idx]['t']:
            old_bpm = bpm
            bpm = time_changes[tc_idx]['bpm']
            write_to_log(f"BPM change at {time}ms: {old_bpm} -> {bpm}")
            tc_idx += 1
            
        # Obtener evento de focus camera actual
        while focus_idx + 1 < len(focus_camera_events) and time >= focus_camera_events[focus_idx + 1]['t']:
            focus_idx += 1
            
        fc_event = focus_camera_events[focus_idx]
        
        # Extraer valor de carácter con mejor lógica
        char_val = None
        v = fc_event.get('v')
        if isinstance(v, dict) and 'char' in v:
            char_val = v['char']
        elif not isinstance(v, dict) and v is not None:
            char_val = v
            
        # char 0 = BF (mustHit=True), char 1 = opponent (mustHit=False)
        must_hit = (str(char_val) == "0") if char_val is not None else True
        section_must_hits.append(must_hit)
        
        if section_count < 5:  # Log primeras secciones para debug
            write_to_log(f"Section {section_count}: time={time}, char={char_val}, mustHit={must_hit}")
        
        section_time = calculate_crochet(bpm) * SECTION_BEATS
        time += section_time
        section_count += 1
    
    write_to_log(f"Generated {len(section_must_hits)} section mustHit values")
    return section_must_hits if section_must_hits else [True]

def create_base_sections(time_changes, base_bpm, last_note_time, section_must_hits):
    """Mejorado: Mejor manejo de BPM y validación"""
    base_sections = []
    section_times = []
    bpm = base_bpm
    last_bpm = base_bpm
    time = 0
    tc_idx = 0
    section_index = 0
    
    # Asegurar que tenemos suficientes secciones para cubrir todas las notas
    end_time = last_note_time + (calculate_crochet(base_bpm) * SECTION_BEATS) + 1000
    write_to_log(f"Creating sections up to {end_time}ms (last note: {last_note_time}ms)")
    
    while time < end_time:
        # Actualizar BPM si hay un cambio en este momento
        while tc_idx < len(time_changes) and time >= time_changes[tc_idx]['t']:
            bpm = time_changes[tc_idx]['bpm']
            tc_idx += 1
        
        # Obtener mustHitSection para esta sección
        must_hit = True  # Default
        if section_index < len(section_must_hits):
            must_hit = section_must_hits[section_index]
        elif section_must_hits:
            must_hit = section_must_hits[-1]  # Usar el último valor
        
        sec = {
            "sectionNotes": [],
            "sectionBeats": SECTION_BEATS,
            "mustHitSection": must_hit,
        }
        
        # Agregar cambio de BPM si es necesario (con tolerancia)
        if abs(last_bpm - bpm) > 0.01:
            sec["changeBPM"] = True
            sec["bpm"] = bpm
            write_to_log(f"Section {section_index}: BPM change to {bpm}")
            
        last_bpm = bpm
        base_sections.append(sec)
        section_times.append(time)
        
        section_time = calculate_crochet(bpm) * SECTION_BEATS
        time += section_time
        section_index += 1
    
    write_to_log(f"Created {len(base_sections)} base sections")
    return base_sections, section_times

def format_event_for_psych(event):
    """Mejorado: Mejor manejo de eventos con validación"""
    event_name = str(event.get('e', 'UnknownEvent'))
    v = event.get('v', {})
    value1 = ""
    value2 = ""

    # Log eventos complejos para debug
    if event_name not in ['FocusCamera'] or (isinstance(v, dict) and len(v) > 1):
        write_to_log(f"Processing complex event: {event_name}, v={v}")

    if event_name == "FocusCamera" and isinstance(v, dict):
        value1 = str(v.get('char', ''))
        params = []
        # Solo incluir parámetros no predeterminados
        for param in ['x', 'y', 'duration', 'ease']:
            val = v.get(param)
            if val is not None and str(val) != "" and str(val) != "0":
                if param == 'duration' and str(val) == "4":
                    continue  # Skip default duration
                if param == 'ease' and str(val).upper() == "CLASSIC":
                    continue  # Skip default ease
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
        force = v.get('force', None)
        if force is not None:
            value2 = anim + "|" + str(force)
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
        
    elif event_name == "SetHealthIcon" and isinstance(v, dict):
        value1 = str(v.get('char', ''))
        params = []
        for param in ['id', 'scale', 'flipX', 'isPixel', 'offsetX', 'offsetY']:
            val = v.get(param)
            if val is not None and str(val) != "":
                params.append(str(val))
        value2 = "|".join(params)
        
    elif event_name == "Set Property" and isinstance(v, dict):
        value1 = str(v.get('property', ''))
        value2 = str(v.get('value', ''))
        
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
    """Mejorado: Mejor detección con tolerancia ajustable"""
    if event.get('e') != 'FocusCamera':
        return False
        
    t = float(event.get('t', -1))
    v = event.get('v', {})
    
    # Parsear valores del evento
    if not isinstance(v, dict):
        char = v if isinstance(v, (int, str)) else None
        x = y = 0
        duration = 4
        ease = "CLASSIC"
    else:
        char = v.get('char')
        try:
            x = float(v.get('x', 0))
        except (ValueError, TypeError):
            x = 0
        try:
            y = float(v.get('y', 0))
        except (ValueError, TypeError):
            y = 0
        try:
            duration = float(v.get('duration', 4))
        except (ValueError, TypeError):
            duration = 4
        ease = str(v.get('ease', "CLASSIC")).strip().upper()
    
    # Verificar si es un focus camera de sección básico (valores predeterminados)
    is_basic = (abs(x) < 0.001 and abs(y) < 0.001 and 
                abs(duration - 4) < 0.001 and ease == "CLASSIC" and 
                char in (0, 1, "0", "1"))
    
    if not is_basic:
        return False
    
    # Verificar si el timing coincide con algún inicio de sección
    for i, st in enumerate(section_times):
        if abs(t - st) < tolerance:
            write_to_log(f"Detected section focus camera at {t}ms (section {i}, diff: {abs(t - st):.1f}ms)")
            return True
    
    return False

def vslice_to_psych(vslice_chart, vslice_metadata):
    """Mejorado: Mejor validación y manejo de errores"""
    write_to_log("=== Starting VSlice to Psych conversion ===")
    
    try:
        # Validar entrada
        if not isinstance(vslice_chart, dict) or not isinstance(vslice_metadata, dict):
            raise ValueError("Invalid chart or metadata format")
        
        difficulties = vslice_metadata.get('playData', {}).get('difficulties', [])
        if not difficulties:
            difficulties = ['normal']
            write_to_log("WARNING: No difficulties found in VSlice metadata. Defaulting to ['normal'].")
        
        write_to_log(f"Processing difficulties: {difficulties}")
        
        time_changes = sorted(vslice_metadata.get('timeChanges', []), key=lambda t: t.get('t', 0))
        base_bpm = time_changes[0].get('bpm', 120) if time_changes else 120
        write_to_log(f"Base BPM: {base_bpm}, Time changes: {len(time_changes)}")
        
        stage = vslice_metadata.get('playData', {}).get('stage', 'mainStage')
        stage = STAGE_TO_PSYCH.get(stage, stage)
        
        notes_map = {}
        last_note_time = 0
        total_notes = 0
        
        for diff in difficulties:
            notes = vslice_chart.get('notes', {}).get(diff, [])
            notes = sorted(notes, key=sort_by_time)
            notes_map[diff] = notes
            total_notes += len(notes)
            if notes:
                last_note_time = max(last_note_time, notes[-1]['t'])
        
        write_to_log(f"Total notes across all difficulties: {total_notes}, last note: {last_note_time}ms")
        
        all_events = sorted(vslice_chart.get('events', []), key=sort_by_time)
        focus_camera_events = [
            e for e in all_events if e.get('e') == 'FocusCamera' and (
                e.get('v') in (0, 1, "0", "1") or (isinstance(e.get('v'), dict) and 'char' in e['v'])
            )
        ]
        write_to_log(f"Found {len(focus_camera_events)} focus camera events out of {len(all_events)} total events")
        
        section_must_hits = get_section_must_hits(focus_camera_events, time_changes, base_bpm, last_note_time)
        base_sections, section_times = create_base_sections(time_changes, base_bpm, last_note_time, section_must_hits)

        # Procesar eventos del archivo
        file_events = []
        skipped_events = 0
        
        for e in all_events:
            if e.get('e') == 'FocusCamera':
                if is_section_focus_camera(e, section_times, tolerance=100.0):
                    skipped_events += 1
                    continue
            
            event_fields = format_event_for_psych(e)
            file_events.append([e.get('t', 0), [event_fields]])
        
        file_events.sort(key=lambda ev: ev[0])
        write_to_log(f"Processed {len(file_events)} events (skipped {skipped_events} section focus cameras)")

        # Generar charts de Psych para cada dificultad
        psych_charts = {}
        for diff in difficulties:
            scroll_speed = vslice_chart.get('scrollSpeed', {}).get(diff, vslice_chart.get('scrollSpeed', {}).get('default', 1.5))
            
            # Aplicar calibración de velocidad
            scroll_speed = adjust_scroll_speed(scroll_speed, "vslice", "psych")
            
            notes = notes_map.get(diff, [])
            section_data = [dict(section, sectionNotes=[]) for section in base_sections]
            
            note_sec = 0
            processed_notes = 0
            
            for note in notes:
                # Encontrar la sección correcta para esta nota
                while note_sec + 1 < len(section_times) and section_times[note_sec + 1] <= note['t']:
                    note_sec += 1
                
                # Obtener mustHitSection para transformación
                must_hit = section_data[note_sec]["mustHitSection"] if 0 <= note_sec < len(section_data) else True
                
                # Transformar datos de nota
                transformed_data = transform_note_data(note.get('d', 0), must_hit, "vslice_to_psych")
                
                psych_note = [
                    note.get('t', 0),
                    transformed_data,
                    note.get('l', 0)
                ]
                
                if note.get('k') and note['k'] not in ("", "normal"):
                    psych_note.append(note['k'])
                
                if 0 <= note_sec < len(section_data):
                    section_data[note_sec]["sectionNotes"].append(psych_note)
                    processed_notes += 1
            
            write_to_log(f"Difficulty '{diff}': {processed_notes} notes processed")
            
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
                "generatedBy": "Chart_Converter By Jere (Enhanced)"
            }
            psych_charts[diff] = {"song": song_meta}
        
        write_to_log(f"=== VSlice to Psych conversion completed successfully ===")
        return psych_charts
        
    except Exception as e:
        write_to_log(f"ERROR in vslice_to_psych: {e}")
        raise

def psych_to_vslice(psych_chart, difficulty_name=None):
    """Mejorado: Mejor validación y procesamiento"""
    write_to_log("=== Starting Psych to VSlice conversion ===")
    
    try:
        if not isinstance(psych_chart, dict) or 'song' not in psych_chart:
            raise ValueError("Invalid Psych Engine chart format")
        
        songData = psych_chart.get('song', {})
        
        events = []
        notes = []
        timeChanges = []
        
        time = 0
        bpm = songData.get('bpm', 120)
        timeChanges.append({'t': 0, 'bpm': bpm})
        write_to_log(f"Initial BPM: {bpm}")
        
        # Determinar focus camera inicial
        first_section_must_hit = True
        if songData.get('notes') and len(songData['notes']) > 0:
            first_section_must_hit = songData['notes'][0].get('mustHitSection', True)
        
        lastMustHit = first_section_must_hit
        events.append({'t': 0, 'e': 'FocusCamera', 'v': {'char': 0 if lastMustHit else 1}})
        
        section_count = 0
        note_count = 0
        
        if songData.get('notes'):
            for section in songData['notes']:
                if section.get('sectionNotes'):
                    for note in section['sectionNotes']:
                        # Aplicar transformación de nota (inversa)
                        transformed_data = transform_note_data(note[1], section.get('mustHitSection', True), "psych_to_vslice")
                        
                        vsliceNote = {'t': note[0], 'd': transformed_data}
                        if len(note) > 2 and note[2] > 0:
                            vsliceNote['l'] = note[2]
                        if len(note) > 3 and note[3]:
                            vsliceNote['k'] = note[3]
                        notes.append(vsliceNote)
                        note_count += 1
                
                section_duration = calculate_crochet(bpm) * SECTION_BEATS
                if section.get('changeBPM') and 'bpm' in section:
                    old_bpm = bpm
                    bpm = section['bpm']
                    timeChanges.append({'t': time, 'bpm': bpm})
                    write_to_log(f"BPM change at {time}ms: {old_bpm} -> {bpm}")
                
                current_must_hit = section.get('mustHitSection', True)
                if lastMustHit != current_must_hit:
                    events.append({'t': time, 'e': 'FocusCamera', 'v': {'char': 0 if current_must_hit else 1}})
                    lastMustHit = current_must_hit
                
                time += section_duration
                section_count += 1
        
        write_to_log(f"Processed {section_count} sections with {note_count} notes")
        
        # Procesar eventos personalizados
        custom_events = 0
        if songData.get('events'):
            for event in songData['events']:
                event_time = event[0]
                if len(event) > 1 and isinstance(event[1], list):
                    for subevent_data in event[1]:
                        event_name = subevent_data[0] if len(subevent_data) > 0 else 'Unknown'
                        value1 = subevent_data[1] if len(subevent_data) > 1 else ''
                        value2 = subevent_data[2] if len(subevent_data) > 2 else ''
                        
                        # Procesamiento mejorado de eventos
                        ev = {'t': event_time, 'e': event_name}
                        
                        if event_name == "FocusCamera" and value1 in ('0', '1', 0, 1):
                            ev['v'] = {'char': int(value1)}
                        elif event_name == "ZoomCamera":
                            zoom_val = 1.0
                            try:
                                zoom_val = float(value1) if value1 else 1.0
                            except ValueError:
                                zoom_val = 1.0
                            ev['v'] = {'zoom': zoom_val}
                            
                            if value2:
                                params = value2.split('|')
                                try:
                                    if len(params) > 0 and params[0]:
                                        ev['v']['duration'] = float(params[0])
                                    if len(params) > 1 and params[1]:
                                        ev['v']['mode'] = params[1]
                                    if len(params) > 2 and params[2]:
                                        ev['v']['ease'] = params[2]
                                except ValueError:
                                    pass
                        else:
                            ev['v'] = {'value1': value1, 'value2': value2}
                        
                        events.append(ev)
                        custom_events += 1
        
        write_to_log(f"Processed {custom_events} custom events")
        
        events.sort(key=sort_by_time)
        notes.sort(key=sort_by_time)
        
        composer = songData.get('artist', songData.get('composer', 'Unknown Artist'))
        charter = songData.get('charter', 'Unknown Charter')
        
        if difficulty_name:
            diffs = [difficulty_name]
        else:
            diffs = ['normal']
            write_to_log("WARNING: No specific difficulty provided for Psych to VSlice conversion. Defaulting to ['normal'].")
        
        # Aplicar calibración de velocidad
        original_speed = songData.get('speed', 1.5)
        adjusted_speed = adjust_scroll_speed(original_speed, "psych", "vslice")
        
        scrollSpeed = {diff: adjusted_speed for diff in diffs}
        notesMap = {diff: notes for diff in diffs}
        
        stage = songData.get('stage', 'mainStage')
        stage = STAGE_TO_VSLICE.get(stage, stage)
        
        chart = {
            'scrollSpeed': scrollSpeed,
            'events': events,
            'notes': notesMap,
            'generatedBy': songData.get('generatedBy', 'Psych Engine Chart Editor V-Slice Exporter'),
            'version': '2.0.0'
        }
        
        metadata = {
            'songName': songData.get('song', 'Unknown Song'),
            'artist': composer,
            'charter': charter,
            'playData': {
                'difficulties': diffs,
                'characters': {
                    'player': songData.get('player1', 'bf'),
                    'girlfriend': songData.get('gfVersion', ''),
                    'opponent': songData.get('player2', 'dad')
                },
                'noteStyle': 'funkin',
                'stage': stage
            },
            'timeFormat': 'ms',
            'timeChanges': timeChanges,
            'generatedBy': songData.get('generatedBy', 'Psych Engine Chart Editor V-Slice Exporter'),
            'version': '2.2.3'
        }
        
        write_to_log("=== Psych to VSlice conversion completed successfully ===")
        return {'chart': chart, 'metadata': metadata}
        
    except Exception as e:
        write_to_log(f"ERROR in psych_to_vslice: {e}")
        raise

# Mantener la clase GUI original pero con mejores mensajes de error
class ConverterGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.tk.call('tk', 'scaling', 1.3)
        self.title("FNF Chart Converter - VSlice ⬌ Psych Engine (Mejorado)")
        self.configure(bg="#23232b")
        self.geometry("700x420")
        self.resizable(False, False)
        self.operation = tk.StringVar(value="vslice2psych")
        self.chart_file = tk.StringVar()
        self.meta_file = tk.StringVar()
        self.psych_file = tk.StringVar()
        self.difficulty = tk.StringVar()
        self.outdir = tk.StringVar(value=os.getcwd())
        self.batch_folder = tk.StringVar()
        self.status_msg = tk.StringVar()
        self.style = ttk.Style(self)
        self.style.theme_use('clam')
        self.style.configure('TFrame', background='#23232b')
        self.style.configure('TLabel', background='#23232b', foreground='#e0e0e0', font=("Segoe UI", 12))
        self.style.configure('TButton', font=("Segoe UI", 11, "bold"), padding=5, background='#5e7d82')
        self.style.map('TButton', background=[('active', '#7a9b9f')])
        self.style.configure('TRadiobutton', background='#23232b', foreground='#e0e0e0', font=("Segoe UI", 11))
        self.style.configure('TEntry', fieldbackground='#24263d', foreground='#f0f0f0', font=("Segoe UI", 11), borderwidth=0)
        self.create_widgets()
        self.update_mode()

    def create_widgets(self):
        frm = ttk.Frame(self, padding=(18, 10, 18, 10), style='TFrame')
        frm.pack(fill="both", expand=True, padx=10, pady=10)
        ttk.Label(frm, text="FNF Chart Converter (Mejorado)", font=("Segoe UI", 18, "bold"), background="#23232b", foreground="#f9c74f").grid(row=0, column=0, columnspan=4, pady=(0, 16), sticky="ew")
        ttk.Label(frm, text="Modo de conversión:", font=("Segoe UI", 12, "bold")).grid(row=1, column=0, sticky="w", pady=(0, 6))
        rb1 = ttk.Radiobutton(frm, text="VSlice → Psych", variable=self.operation, value="vslice2psych", command=self.update_mode)
        rb2 = ttk.Radiobutton(frm, text="Psych → VSlice", variable=self.operation, value="psych2vslice", command=self.update_mode)
        rb3 = ttk.Radiobutton(frm, text="Batch VSlice → Psych (carpetas)", variable=self.operation, value="batch-vslice2psych", command=self.update_mode)
        rb4 = ttk.Radiobutton(frm, text="Batch Psych → VSlice (carpetas)", variable=self.operation, value="batch-psych2vslice", command=self.update_mode)
        rb1.grid(row=1, column=1, sticky="w", padx=4)
        rb2.grid(row=1, column=2, sticky="w", padx=4)
        rb3.grid(row=2, column=1, sticky="w", padx=4, pady=(0, 12))
        rb4.grid(row=2, column=2, sticky="w", padx=4, pady=(0, 12))
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
        ttk.Label(frm, text="Carpeta salida:").grid(row=9, column=0, sticky="w", pady=(12, 3))
        out_ent = ttk.Entry(frm, textvariable=self.outdir, width=38)
        out_ent.grid(row=9, column=1, padx=5, columnspan=2, sticky="ew")
        ttk.Button(frm, text="Buscar...", command=self.browse_outdir).grid(row=9, column=3, sticky="w")
        self.convert_btn = ttk.Button(frm, text="Convertir", command=self.convert, style='TButton')
        self.convert_btn.grid(row=11, column=0, columnspan=4, pady=18, ipadx=10, sticky="ew")
        self.status = ttk.Label(self, textvariable=self.status_msg, foreground="#00ff55", font=("Segoe UI", 12, "italic"), background="#23232b")
        self.status.pack(side="bottom", fill="x", pady=(2, 8), padx=14, anchor="s")
        frm.grid_columnconfigure(1, weight=1)
        frm.grid_columnconfigure(2, weight=1)

    def update_mode(self):
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
        else:
            self.lbl_batch.grid(row=row_start, column=0, sticky="w", pady=4)
            self.ent_batch.grid(row=row_start, column=1, columnspan=2, padx=5, pady=2, sticky="ew")
            self.btn_batch.grid(row=row_start, column=3, sticky="w")

    def browse_chart(self):
        fname = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if fname:
            self.chart_file.set(fname)

    def browse_meta(self):
        fname = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if fname:
            self.meta_file.set(fname)

    def browse_psych(self):
        fname = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if fname:
            self.psych_file.set(fname)

    def browse_outdir(self):
        dirname = filedialog.askdirectory()
        if dirname:
            self.outdir.set(dirname)

    def browse_batch(self):
        dirname = filedialog.askdirectory()
        if dirname:
            self.batch_folder.set(dirname)

    def convert(self):
        """Mejorado: Mejor manejo de errores y retroalimentación"""
        try:
            op = self.operation.get()
            outdir = self.outdir.get()
            if not outdir:
                messagebox.showerror("Error", "Por favor, selecciona una carpeta de salida.")
                return
            
            write_to_log(f"Starting conversion: {op}")
            self.status_msg.set("Procesando, por favor espera...")
            self.update_idletasks()
            
            if op == "vslice2psych":
                if not self.chart_file.get() or not self.meta_file.get():
                    messagebox.showerror("Error", "Debes seleccionar ambos archivos: chart.json y metadata.json")
                    return
                vslice_chart = load_json(self.chart_file.get())
                vslice_metadata = load_json(self.meta_file.get())
                psych_charts = vslice_to_psych(vslice_chart, vslice_metadata)
                count = 0
                for diff, chart_data in psych_charts.items():
                    out_path = os.path.join(outdir, f"psych_{diff}.json")
                    save_json(chart_data, out_path)
                    count += 1
                self.status_msg.set(f"¡Conversión exitosa! Se crearon {count} archivos Psych en '{outdir}'. Revisa '{LOG_FILE_NAME}' para detalles.")
                
            elif op == "psych2vslice":
                if not self.psych_file.get():
                    messagebox.showerror("Error", "Debes seleccionar un archivo Psych Engine chart.json")
                    return
                psych_chart = load_json(self.psych_file.get())
                diff_override = self.difficulty.get().strip() if self.difficulty.get() else None
                vslice_pack = psych_to_vslice(psych_chart, diff_override)
                save_json(vslice_pack['chart'], os.path.join(outdir, "chart.json"))
                save_json(vslice_pack['metadata'], os.path.join(outdir, "metadata.json"))
                self.status_msg.set(f"¡Exportación exitosa! chart.json y metadata.json generados en '{outdir}'. Revisa '{LOG_FILE_NAME}' para detalles.")
                
            elif op == "batch-vslice2psych":
                folder = self.batch_folder.get()
                if not folder or not os.path.isdir(folder):
                    messagebox.showerror("Error", "Selecciona una carpeta raíz de entrada válida para el batch.")
                    return
                chart_pairs = recursive_find_charts(folder, "vslice2psych")
                if not chart_pairs:
                    messagebox.showinfo("Información", f"No se encontraron pares '-chart*.json' y '-metadata*.json' en '{folder}'.")
                    self.status_msg.set("Batch terminado: No se encontraron charts para convertir.")
                    return
                batch_count = 0
                errors = 0
                for chart_path, meta_path, song_dir, chart_fn, meta_fn in chart_pairs:
                    try:
                        vslice_chart = load_json(chart_path)
                        vslice_metadata = load_json(meta_path)
                        psych_charts = vslice_to_psych(vslice_chart, vslice_metadata)

                        current_chart_base = ""
                        if "-chart-" in chart_fn:
                            current_chart_base = chart_fn.split("-chart-")[0] + "-" + chart_fn.split("-chart-")[1].replace(".json", "")
                        elif "-chart.json" in chart_fn:
                            current_chart_base = chart_fn.replace("-chart.json", "")
                        else:
                            current_chart_base = os.path.splitext(chart_fn)[0]
                            if "-chart" in current_chart_base:
                                current_chart_base = current_chart_base.rsplit("-chart", 1)[0]
                        
                        if current_chart_base.lower().endswith("spookymod"):
                            current_chart_base = current_chart_base[:-len("spookymod")] + "(spookymix)"
                            current_chart_base = current_chart_base.strip('-')

                        current_chart_base = current_chart_base.strip('-')

                        song_parent = os.path.dirname(song_dir)
                        rel_parent = os.path.relpath(song_parent, folder)

                        if rel_parent == ".":
                            out_folder = os.path.join(outdir, current_chart_base)
                        else:
                            out_folder = os.path.join(outdir, rel_parent, current_chart_base)

                        os.makedirs(out_folder, exist_ok=True)

                        for diff, chart_data in psych_charts.items():
                            json_file = f"{current_chart_base}-{diff}.json"
                            out_path = os.path.join(out_folder, json_file)
                            save_json(chart_data, out_path)
                            batch_count += 1
                        self.status_msg.set(f"Batch VSlice→Psych: {batch_count} archivos generados...")
                        self.update_idletasks()
                    except Exception as inner_e:
                        errors += 1
                        log_message = f"ERROR: Falló el procesamiento de VSlice a Psych para '{chart_path}' y '{meta_path}'. Error: {inner_e}"
                        write_to_log(log_message)
                        continue
                
                final_msg = f"Batch terminado: {batch_count} archivos generados"
                if errors > 0:
                    final_msg += f" ({errors} errores)"
                final_msg += f" en '{outdir}'. Revisa '{LOG_FILE_NAME}' para detalles."
                self.status_msg.set(final_msg)
                
            elif op == "batch-psych2vslice":
                folder = self.batch_folder.get()
                if not folder or not os.path.isdir(folder):
                    messagebox.showerror("Error", "Por favor, selecciona una carpeta raíz de entrada válida para el batch.")
                    return
                song_groups_to_convert = recursive_find_charts(folder, "psych2vslice")
                if not song_groups_to_convert:
                    messagebox.showinfo("Información", f"No se encontraron archivos JSON de Psych Engine en '{folder}'.")
                    self.status_msg.set("Batch terminado: No se encontraron charts para convertir.")
                    return

                batch_count = 0
                errors = 0
                for song_dir, song_id, difficulties_map in song_groups_to_convert:
                    try:
                        common_difficulties_order = ["easy", "normal", "hard", "insane", "expert", "hardest", "master", "mad"]
                        sorted_difficulties = sorted(difficulties_map.keys(), 
                                                     key=lambda x: (common_difficulties_order.index(x) if x in common_difficulties_order else len(common_difficulties_order)),
                                                     reverse=False)

                        if not sorted_difficulties:
                            write_to_log(f"WARNING: No difficulties found for song group {song_id} at {song_dir}")
                            continue

                        primary_psych_path = difficulties_map[sorted_difficulties[0]]
                        primary_psych_chart = load_json(primary_psych_path)
                        initial_vslice_pack = psych_to_vslice(primary_psych_chart, difficulty_name=sorted_difficulties[0])
                        
                        consolidated_vslice_chart = initial_vslice_pack['chart']
                        consolidated_vslice_metadata = initial_vslice_pack['metadata']

                        consolidated_vslice_chart['notes'] = {}
                        consolidated_vslice_chart['scrollSpeed'] = {}
                        consolidated_vslice_metadata['playData']['difficulties'] = []

                        for difficulty in sorted_difficulties:
                            psych_path = difficulties_map[difficulty]
                            psych_chart = load_json(psych_path)
                            temp_vslice_pack = psych_to_vslice(psych_chart, difficulty_name=difficulty)
                            consolidated_vslice_chart['notes'][difficulty] = temp_vslice_pack['chart']['notes'][difficulty]
                            consolidated_vslice_chart['scrollSpeed'][difficulty] = temp_vslice_pack['chart']['scrollSpeed'][difficulty]
                            if difficulty not in consolidated_vslice_metadata['playData']['difficulties']:
                                consolidated_vslice_metadata['playData']['difficulties'].append(difficulty)
                        
                        consolidated_vslice_metadata['playData']['difficulties'].sort(key=lambda x: (common_difficulties_order.index(x) if x in common_difficulties_order else len(common_difficulties_order)))

                        rel_path_from_input = os.path.relpath(song_dir, folder)
                        out_song_folder = os.path.join(outdir, rel_path_from_input, song_id)
                        os.makedirs(out_song_folder, exist_ok=True)
                        
                        vslice_chart_filename = f"{song_id}-chart.json"
                        vslice_metadata_filename = f"{song_id}-metadata.json"

                        save_json(consolidated_vslice_chart, os.path.join(out_song_folder, vslice_chart_filename))
                        save_json(consolidated_vslice_metadata, os.path.join(out_song_folder, vslice_metadata_filename))
                        
                        batch_count += 1
                        self.status_msg.set(f"Batch Psych→VSlice: {batch_count} canciones convertidas...")
                        self.update_idletasks()

                    except Exception as inner_e:
                        errors += 1
                        log_message = f"ERROR: Falló el procesamiento de Psych a VSlice para la canción '{song_id}' ({song_dir}). Error: {inner_e}"
                        write_to_log(log_message)
                        continue
                
                final_msg = f"Batch terminado: {batch_count} canciones convertidas"
                if errors > 0:
                    final_msg += f" ({errors} errores)"
                final_msg += f" en '{outdir}'. Revisa '{LOG_FILE_NAME}' para detalles."
                self.status_msg.set(final_msg)
                
        except (FileNotFoundError, ValueError) as e:
            messagebox.showerror("Error de Archivo/Formato", str(e))
            self.status_msg.set("Error en la conversión.")
            write_to_log(f"Conversion error: {e}")
        except Exception as e:
            messagebox.showerror("Error durante la conversión", f"Ocurrió un error inesperado: {e}")
            self.status_msg.set("Error en la conversión.")
            write_to_log(f"Unexpected error: {e}")
        finally:
            self.update_idletasks()

if __name__ == "__main__":
    try:
        write_to_log("=== Application started ===")
        app = ConverterGUI()
        app.mainloop()
    except Exception as e:
        write_to_log(f"Application startup error: {e}")
        print(f"Error starting application: {e}")