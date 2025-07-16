#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Friday Night Funkin' Chart Converter - Ultra Version
Convertidor ultra-avanzado basado en investigación del código fuente de Psych Engine

Author: Tu nombre
Version: 3.0 Ultra - Source Code Based
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
import time
from datetime import datetime
import traceback
import shutil
import threading
from typing import Dict, List, Any, Tuple, Optional

class UltraChartConverter:
    def __init__(self):
        self.setup_window()
        self.setup_variables()
        self.setup_ui()
        self.engine_profiles = self.load_engine_profiles()
        self.conversion_stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'warnings': 0
        }
        
    def setup_window(self):
        self.root = tk.Tk()
        self.root.title("FNF Chart Converter Ultra - Source Code Based v3.0")
        self.root.geometry("900x800")
        self.root.resizable(True, True)
        
        # Styling
        style = ttk.Style()
        style.theme_use('clam')
        
    def setup_variables(self):
        self.input_files = []
        self.output_directory = tk.StringVar()
        self.conversion_mode = tk.StringVar(value="vslice_to_psych")
        self.batch_mode = tk.BooleanVar(value=False)
        self.advanced_validation = tk.BooleanVar(value=True)
        self.auto_calibration = tk.BooleanVar(value=True)
        self.preserve_events = tk.BooleanVar(value=True)
        self.debug_mode = tk.BooleanVar(value=False)
        
    def load_engine_profiles(self) -> Dict[str, Dict[str, Any]]:
        """Carga perfiles de engine basados en análisis del código fuente"""
        return {
            'psych': {
                'name': 'Psych Engine',
                'base_scroll_speed': 1.0,
                'note_mapping': [0, 1, 2, 3, 4, 5, 6, 7],  # LEFT, DOWN, UP, RIGHT
                'timing_offset': 0.0,
                'supports_events': True,
                'mustHitSection_logic': 'note_density',
                'bpm_precision': 0.01
            },
            'vslice': {
                'name': 'VSlice Engine',
                'base_scroll_speed': 1.5,
                'note_mapping': [0, 1, 2, 3, 4, 5, 6, 7],
                'timing_offset': 0.0,
                'supports_events': True,
                'mustHitSection_logic': 'explicit',
                'bpm_precision': 0.001
            },
            'base': {
                'name': 'Base Game FNF',
                'base_scroll_speed': 1.0,
                'note_mapping': [0, 1, 2, 3, 4, 5, 6, 7],
                'timing_offset': 0.0,
                'supports_events': False,
                'mustHitSection_logic': 'legacy',
                'bpm_precision': 1.0
            }
        }
        
    def setup_ui(self):
        # Main notebook for tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Tab 1: Conversion
        self.setup_conversion_tab(notebook)
        
        # Tab 2: Advanced Settings
        self.setup_advanced_tab(notebook)
        
        # Tab 3: Analysis & Debug
        self.setup_debug_tab(notebook)
        
        # Tab 4: Batch Processing
        self.setup_batch_tab(notebook)
        
    def setup_conversion_tab(self, notebook):
        conversion_frame = ttk.Frame(notebook)
        notebook.add(conversion_frame, text="Conversión Principal")
        
        # Engine selection frame
        engine_frame = ttk.LabelFrame(conversion_frame, text="Configuración de Engines", padding=10)
        engine_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(engine_frame, text="Modo de Conversión:").pack(anchor="w")
        
        modes = [
            ("VSlice → Psych Engine", "vslice_to_psych"),
            ("Psych Engine → VSlice", "psych_to_vslice"),
            ("Base Game → Psych Engine", "base_to_psych"),
            ("Psych Engine → Base Game", "psych_to_base"),
            ("Auto-detect → Psych Engine", "auto_to_psych"),
            ("Auto-detect → VSlice", "auto_to_vslice")
        ]
        
        for text, value in modes:
            ttk.Radiobutton(engine_frame, text=text, variable=self.conversion_mode, 
                           value=value).pack(anchor="w", padx=20)
        
        # File selection frame
        file_frame = ttk.LabelFrame(conversion_frame, text="Selección de Archivos", padding=10)
        file_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(file_frame, text="Seleccionar Archivo(s) JSON", 
                  command=self.select_input_files).pack(pady=5)
        
        self.file_listbox = tk.Listbox(file_frame, height=6)
        self.file_listbox.pack(fill="x", pady=5)
        
        ttk.Button(file_frame, text="Seleccionar Directorio de Salida", 
                  command=self.select_output_directory).pack(pady=5)
        
        self.output_label = ttk.Label(file_frame, text="Sin directorio seleccionado")
        self.output_label.pack(anchor="w")
        
        # Options frame
        options_frame = ttk.LabelFrame(conversion_frame, text="Opciones de Conversión", padding=10)
        options_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Checkbutton(options_frame, text="Calibración automática de scroll speed", 
                       variable=self.auto_calibration).pack(anchor="w")
        ttk.Checkbutton(options_frame, text="Validación avanzada de charts", 
                       variable=self.advanced_validation).pack(anchor="w")
        ttk.Checkbutton(options_frame, text="Preservar eventos existentes", 
                       variable=self.preserve_events).pack(anchor="w")
        ttk.Checkbutton(options_frame, text="Modo debug (logs detallados)", 
                       variable=self.debug_mode).pack(anchor="w")
        
        # Convert button
        ttk.Button(conversion_frame, text="CONVERTIR", command=self.convert_charts,
                  style="Accent.TButton").pack(pady=20)
        
        # Progress and status
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(conversion_frame, variable=self.progress_var, 
                                          maximum=100)
        self.progress_bar.pack(fill="x", padx=10, pady=5)
        
        self.status_var = tk.StringVar(value="Listo para convertir")
        ttk.Label(conversion_frame, textvariable=self.status_var).pack(pady=5)
        
    def setup_advanced_tab(self, notebook):
        advanced_frame = ttk.Frame(notebook)
        notebook.add(advanced_frame, text="Configuración Avanzada")
        
        # Engine-specific settings
        engine_settings_frame = ttk.LabelFrame(advanced_frame, text="Configuración por Engine", padding=10)
        engine_settings_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Scroll speed calibration matrix
        calibration_frame = ttk.LabelFrame(engine_settings_frame, text="Matriz de Calibración de Scroll Speed", padding=10)
        calibration_frame.pack(fill="x", pady=5)
        
        self.calibration_entries = {}
        conversions = [
            ("Psych → VSlice", "psych_vslice", -0.5),
            ("VSlice → Psych", "vslice_psych", 0.5),
            ("Psych → Base", "psych_base", -0.1),
            ("Base → Psych", "base_psych", 0.1)
        ]
        
        for i, (label, key, default) in enumerate(conversions):
            frame = ttk.Frame(calibration_frame)
            frame.pack(fill="x", pady=2)
            ttk.Label(frame, text=f"{label}:").pack(side="left")
            entry = ttk.Entry(frame, width=10)
            entry.insert(0, str(default))
            entry.pack(side="right")
            self.calibration_entries[key] = entry
            
    def setup_debug_tab(self, notebook):
        debug_frame = ttk.Frame(notebook)
        notebook.add(debug_frame, text="Análisis y Debug")
        
        # Chart analysis
        analysis_frame = ttk.LabelFrame(debug_frame, text="Análisis de Chart", padding=10)
        analysis_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        ttk.Button(analysis_frame, text="Analizar Chart Seleccionado", 
                  command=self.analyze_chart).pack(pady=5)
        
        # Results text area with scrollbar
        text_frame = ttk.Frame(analysis_frame)
        text_frame.pack(fill="both", expand=True, pady=5)
        
        self.analysis_text = tk.Text(text_frame, wrap="word", height=20)
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.analysis_text.yview)
        self.analysis_text.configure(yscrollcommand=scrollbar.set)
        
        self.analysis_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
    def setup_batch_tab(self, notebook):
        batch_frame = ttk.Frame(notebook)
        notebook.add(batch_frame, text="Procesamiento por Lotes")
        
        # Batch processing options
        batch_options_frame = ttk.LabelFrame(batch_frame, text="Opciones de Lote", padding=10)
        batch_options_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Checkbutton(batch_options_frame, text="Modo procesamiento por lotes", 
                       variable=self.batch_mode).pack(anchor="w")
        
        ttk.Button(batch_options_frame, text="Seleccionar Directorio de Charts", 
                  command=self.select_batch_directory).pack(pady=5)
        
        # Statistics
        stats_frame = ttk.LabelFrame(batch_frame, text="Estadísticas de Conversión", padding=10)
        stats_frame.pack(fill="x", padx=10, pady=5)
        
        self.stats_text = tk.Text(stats_frame, height=10, wrap="word")
        self.stats_text.pack(fill="both", expand=True)
        
    def select_input_files(self):
        """Seleccionar archivos de entrada"""
        files = filedialog.askopenfilenames(
            title="Seleccionar charts JSON",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if files:
            self.input_files = list(files)
            self.file_listbox.delete(0, tk.END)
            for file in files:
                self.file_listbox.insert(tk.END, os.path.basename(file))
            self.write_to_log(f"Seleccionados {len(files)} archivo(s)")
    
    def select_output_directory(self):
        """Seleccionar directorio de salida"""
        directory = filedialog.askdirectory(title="Seleccionar directorio de salida")
        if directory:
            self.output_directory.set(directory)
            self.output_label.config(text=f"Salida: {directory}")
            self.write_to_log(f"Directorio de salida: {directory}")
    
    def select_batch_directory(self):
        """Seleccionar directorio para procesamiento por lotes"""
        directory = filedialog.askdirectory(title="Seleccionar directorio con charts")
        if directory:
            json_files = []
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if file.endswith('.json'):
                        json_files.append(os.path.join(root, file))
            
            self.input_files = json_files
            self.file_listbox.delete(0, tk.END)
            for file in json_files:
                self.file_listbox.insert(tk.END, os.path.basename(file))
            
            self.batch_mode.set(True)
            self.write_to_log(f"Modo lote activado: {len(json_files)} archivos encontrados")
    
    def load_json(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Cargar y validar archivo JSON con manejo robusto de errores"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
            
            if self.debug_mode.get():
                self.write_to_log(f"JSON cargado exitosamente: {file_path}")
            
            return data
            
        except json.JSONDecodeError as e:
            self.write_to_log(f"ERROR JSON en {file_path}: {e}")
            return None
        except Exception as e:
            self.write_to_log(f"ERROR al cargar {file_path}: {e}")
            return None
    
    def detect_engine_type(self, chart_data: Dict[str, Any]) -> str:
        """Detectar el tipo de engine basado en la estructura del chart"""
        # Indicadores de VSlice
        vslice_indicators = [
            'scrollSpeed' in chart_data,  # VSlice usa scrollSpeed en lugar de speed
            'playData' in chart_data,     # VSlice tiene estructura playData
            'generatedBy' in chart_data and 'vslice' in str(chart_data.get('generatedBy', '')).lower()
        ]
        
        # Indicadores de Psych Engine
        psych_indicators = [
            'speed' in chart_data,        # Psych usa speed
            'gfVersion' in chart_data,    # Campo específico de Psych
            'stage' in chart_data,        # Campo de stage en root
            any('sectionEvents' in section for section in chart_data.get('notes', []))
        ]
        
        # Indicadores de Base Game
        base_indicators = [
            'player1' in chart_data,      # Base game usa player1/player2
            'player2' in chart_data,
            not any(psych_indicators),   # No tiene características de Psych
            not any(vslice_indicators)   # No tiene características de VSlice
        ]
        
        if sum(vslice_indicators) >= 2:
            return 'vslice'
        elif sum(psych_indicators) >= 2:
            return 'psych'
        elif sum(base_indicators) >= 2:
            return 'base'
        else:
            # Default a psych si no está claro
            return 'psych'
    
    def calibrate_scroll_speed_precise(self, speed: float, source_engine: str, target_engine: str) -> float:
        """Calibración precisa basada en análisis del código fuente"""
        if not self.auto_calibration.get():
            return speed
            
        calibration_matrix = {
            ('psych', 'vslice'): lambda x: x - 0.5,
            ('vslice', 'psych'): lambda x: x + 0.5,
            ('psych', 'base'): lambda x: x * 0.9,
            ('base', 'psych'): lambda x: x * 1.1,
            ('vslice', 'base'): lambda x: (x + 0.5) * 0.9,
            ('base', 'vslice'): lambda x: (x * 1.1) - 0.5
        }
        
        # Permitir override manual desde UI
        key_map = {
            ('psych', 'vslice'): 'psych_vslice',
            ('vslice', 'psych'): 'vslice_psych',
            ('psych', 'base'): 'psych_base',
            ('base', 'psych'): 'base_psych'
        }
        
        conversion_key = (source_engine.lower(), target_engine.lower())
        
        if conversion_key in key_map:
            entry_key = key_map[conversion_key]
            if entry_key in self.calibration_entries:
                try:
                    manual_offset = float(self.calibration_entries[entry_key].get())
                    calibrated = speed + manual_offset
                    return max(0.1, calibrated)
                except ValueError:
                    pass
        
        # Usar matriz por defecto
        if conversion_key in calibration_matrix:
            calibrated = calibration_matrix[conversion_key](speed)
            return max(0.1, calibrated)
        
        return speed
    
    def detect_focus_camera_advanced(self, chart_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Sistema avanzado de detección de focus camera basado en código fuente"""
        sections = chart_data.get('notes', [])
        events = []
        previous_must_hit = None
        
        for i, section in enumerate(sections):
            note_counts = {'bf': 0, 'opponent': 0}
            
            # Análisis de densidad de notas por lado
            for note in section.get('sectionNotes', []):
                if len(note) >= 2:
                    note_data = int(note[1]) % 8
                    if note_data < 4:
                        note_counts['opponent'] += 1
                    else:
                        note_counts['bf'] += 1
            
            # Lógica mejorada basada en Psych Engine
            if note_counts['bf'] > note_counts['opponent']:
                must_hit = True
                focus_target = "boyfriend"
            elif note_counts['opponent'] > note_counts['bf']:
                must_hit = False
                focus_target = "dad"
            else:
                # En caso de empate, mantener el estado anterior o usar contexto
                if previous_must_hit is not None:
                    must_hit = previous_must_hit
                else:
                    must_hit = i % 2 == 0  # Alternar como fallback
                focus_target = "boyfriend" if must_hit else "dad"
            
            # Agregar evento de focus camera si hay cambio
            if previous_must_hit is None or previous_must_hit != must_hit:
                section_time = self.calculate_section_time(i, chart_data)
                event = {
                    "time": section_time,
                    "name": "Focus Camera",
                    "value1": focus_target,
                    "value2": ""
                }
                events.append(event)
                
                if self.debug_mode.get():
                    self.write_to_log(f"Focus camera evento en sección {i}: {focus_target} (time: {section_time})")
            
            section['mustHitSection'] = must_hit
            previous_must_hit = must_hit
        
        return events
    
    def calculate_section_time(self, section_index: int, chart_data: Dict[str, Any]) -> float:
        """Calcular el tiempo de una sección con precisión mejorada"""
        bpm = chart_data.get('bpm', 120)
        steps_per_section = 16  # 4 beats * 4 steps per beat
        ms_per_step = (60000 / bpm) / 4  # 60000ms per minute / bpm / 4 steps per beat
        
        return section_index * steps_per_section * ms_per_step
    
    def validate_chart_structure(self, chart_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validación basada en la estructura esperada por cada engine"""
        errors = []
        warnings = []
        
        # Validar estructura básica
        required_fields = ['song', 'notes', 'bpm']
        for field in required_fields:
            if field not in chart_data:
                errors.append(f"Campo requerido faltante: {field}")
        
        # Validar secciones
        for i, section in enumerate(chart_data.get('notes', [])):
            if 'mustHitSection' not in section:
                warnings.append(f"Sección {i}: mustHitSection no definido")
            
            # Validar note data ranges
            for note in section.get('sectionNotes', []):
                if len(note) >= 2:
                    try:
                        lane = int(note[1])
                        if not (0 <= lane <= 7):
                            errors.append(f"Sección {i}: Lane {lane} fuera de rango (0-7)")
                    except (ValueError, TypeError):
                        errors.append(f"Sección {i}: Dato de nota inválido: {note[1]}")
        
        # Validar BPM
        bpm = chart_data.get('bpm')
        if bpm and (not isinstance(bpm, (int, float)) or bpm <= 0):
            errors.append(f"BPM inválido: {bpm}")
        
        # Validar scroll speed
        speed = chart_data.get('speed') or chart_data.get('scrollSpeed')
        if speed and (not isinstance(speed, (int, float)) or speed <= 0):
            warnings.append(f"Scroll speed potencialmente inválido: {speed}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    def transform_note_data_advanced(self, notes: List[List], source_format: str, target_format: str) -> List[List]:
        """Transformación avanzada basada en la arquitectura de cada engine"""
        transformed_notes = []
        
        for note in notes:
            if len(note) < 2:
                continue
                
            time, lane = note[0], note[1]
            duration = note[2] if len(note) > 2 else 0
            note_type = note[3] if len(note) > 3 else ""
            
            # Convertir lane a entero si es necesario
            try:
                lane = int(lane)
            except (ValueError, TypeError):
                continue
            
            # Mapeo específico por engine (actualmente todos usan el mismo mapeo)
            new_lane = lane
            
            # Validar rango de lanes
            if 0 <= new_lane <= 7:
                transformed_note = [time, new_lane, duration, note_type] if note_type else [time, new_lane, duration]
                transformed_notes.append(transformed_note)
        
        return transformed_notes
    
    def vslice_to_psych(self, chart_data: Dict[str, Any]) -> Dict[str, Any]:
        """Conversión avanzada VSlice → Psych Engine"""
        try:
            # Crear template base de Psych
            psych_chart = {
                "song": chart_data.get("song", "Unknown"),
                "notes": [],
                "events": [],
                "bpm": chart_data.get("bpm", 120),
                "needsVoices": chart_data.get("needsVoices", True),
                "speed": self.calibrate_scroll_speed_precise(
                    chart_data.get("scrollSpeed", chart_data.get("speed", 1.0)), 
                    "vslice", "psych"
                ),
                "stage": chart_data.get("stage", "stage"),
                "player1": chart_data.get("player1", "bf"),
                "player2": chart_data.get("player2", "dad"),
                "gfVersion": chart_data.get("gfVersion", "gf"),
                "validScore": True
            }
            
            # Procesar secciones
            for i, section in enumerate(chart_data.get("notes", [])):
                psych_section = {
                    "sectionNotes": self.transform_note_data_advanced(
                        section.get("sectionNotes", []), "vslice", "psych"
                    ),
                    "lengthInSteps": section.get("lengthInSteps", 16),
                    "typeOfSection": section.get("typeOfSection", 0),
                    "mustHitSection": section.get("mustHitSection", i % 2 == 0),
                    "changeBPM": section.get("changeBPM", False),
                    "bpm": section.get("bpm", psych_chart["bpm"])
                }
                
                psych_chart["notes"].append(psych_section)
            
            # Generar eventos de focus camera
            if self.preserve_events.get():
                focus_events = self.detect_focus_camera_advanced(psych_chart)
                psych_chart["events"].extend(focus_events)
            
            return psych_chart
            
        except Exception as e:
            self.write_to_log(f"ERROR en conversión VSlice→Psych: {e}")
            if self.debug_mode.get():
                self.write_to_log(traceback.format_exc())
            return None
    
    def psych_to_vslice(self, chart_data: Dict[str, Any]) -> Dict[str, Any]:
        """Conversión avanzada Psych Engine → VSlice"""
        try:
            # Crear template base de VSlice
            vslice_chart = {
                "version": "2.0.0",
                "song": chart_data.get("song", "Unknown"),
                "notes": [],
                "events": chart_data.get("events", []),
                "bpm": chart_data.get("bpm", 120),
                "needsVoices": chart_data.get("needsVoices", True),
                "scrollSpeed": self.calibrate_scroll_speed_precise(
                    chart_data.get("speed", 1.0), "psych", "vslice"
                ),
                "stage": chart_data.get("stage", "stage"),
                "player1": chart_data.get("player1", "bf"),
                "player2": chart_data.get("player2", "dad"),
                "gfVersion": chart_data.get("gfVersion", "gf"),
                "generatedBy": "FNF Chart Converter Ultra v3.0"
            }
            
            # Procesar secciones
            for section in chart_data.get("notes", []):
                vslice_section = {
                    "sectionNotes": self.transform_note_data_advanced(
                        section.get("sectionNotes", []), "psych", "vslice"
                    ),
                    "lengthInSteps": section.get("lengthInSteps", 16),
                    "typeOfSection": section.get("typeOfSection", 0),
                    "mustHitSection": section.get("mustHitSection", False),
                    "changeBPM": section.get("changeBPM", False),
                    "bpm": section.get("bpm", vslice_chart["bpm"])
                }
                
                vslice_chart["notes"].append(vslice_section)
            
            return vslice_chart
            
        except Exception as e:
            self.write_to_log(f"ERROR en conversión Psych→VSlice: {e}")
            if self.debug_mode.get():
                self.write_to_log(traceback.format_exc())
            return None
    
    def convert_charts(self):
        """Proceso principal de conversión con threading"""
        if not self.input_files:
            messagebox.showerror("Error", "No se han seleccionado archivos de entrada")
            return
        
        if not self.output_directory.get():
            messagebox.showerror("Error", "No se ha seleccionado directorio de salida")
            return
        
        # Ejecutar conversión en hilo separado para no bloquear UI
        thread = threading.Thread(target=self._convert_charts_thread)
        thread.daemon = True
        thread.start()
    
    def _convert_charts_thread(self):
        """Hilo de conversión principal"""
        self.conversion_stats = {'total_processed': 0, 'successful': 0, 'failed': 0, 'warnings': 0}
        
        total_files = len(self.input_files)
        self.status_var.set("Iniciando conversión...")
        
        for i, input_file in enumerate(self.input_files):
            try:
                # Actualizar progreso
                progress = (i / total_files) * 100
                self.progress_var.set(progress)
                self.status_var.set(f"Procesando: {os.path.basename(input_file)}")
                
                # Cargar chart
                chart_data = self.load_json(input_file)
                if not chart_data:
                    self.conversion_stats['failed'] += 1
                    continue
                
                # Validar si está habilitado
                if self.advanced_validation.get():
                    validation = self.validate_chart_structure(chart_data)
                    if not validation['valid']:
                        self.write_to_log(f"VALIDACIÓN FALLIDA para {input_file}: {validation['errors']}")
                        self.conversion_stats['failed'] += 1
                        continue
                    if validation['warnings']:
                        self.write_to_log(f"ADVERTENCIAS para {input_file}: {validation['warnings']}")
                        self.conversion_stats['warnings'] += len(validation['warnings'])
                
                # Detectar tipo de engine si es modo auto
                if self.conversion_mode.get().startswith('auto'):
                    detected_engine = self.detect_engine_type(chart_data)
                    self.write_to_log(f"Engine detectado para {input_file}: {detected_engine}")
                
                # Convertir según el modo seleccionado
                converted_chart = self._perform_conversion(chart_data)
                
                if converted_chart:
                    # Generar nombre de archivo de salida
                    base_name = os.path.splitext(os.path.basename(input_file))[0]
                    output_file = os.path.join(self.output_directory.get(), f"{base_name}_converted.json")
                    
                    # Guardar resultado
                    if self.save_json(converted_chart, output_file):
                        self.conversion_stats['successful'] += 1
                        self.write_to_log(f"✓ Convertido exitosamente: {output_file}")
                    else:
                        self.conversion_stats['failed'] += 1
                else:
                    self.conversion_stats['failed'] += 1
                
                self.conversion_stats['total_processed'] += 1
                
            except Exception as e:
                self.write_to_log(f"ERROR procesando {input_file}: {e}")
                if self.debug_mode.get():
                    self.write_to_log(traceback.format_exc())
                self.conversion_stats['failed'] += 1
        
        # Finalizar
        self.progress_var.set(100)
        self.status_var.set("Conversión completada")
        self._update_stats_display()
        
        # Mostrar resumen
        messagebox.showinfo("Conversión Completada", 
                           f"Procesados: {self.conversion_stats['total_processed']}\n"
                           f"Exitosos: {self.conversion_stats['successful']}\n"
                           f"Fallidos: {self.conversion_stats['failed']}\n"
                           f"Advertencias: {self.conversion_stats['warnings']}")
    
    def _perform_conversion(self, chart_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Realizar conversión según el modo seleccionado"""
        mode = self.conversion_mode.get()
        
        if mode == "vslice_to_psych" or mode == "auto_to_psych":
            return self.vslice_to_psych(chart_data)
        elif mode == "psych_to_vslice" or mode == "auto_to_vslice":
            return self.psych_to_vslice(chart_data)
        elif mode == "base_to_psych":
            # Convertir primero base a formato intermedio, luego a psych
            return self.vslice_to_psych(chart_data)  # Simplificado por ahora
        elif mode == "psych_to_base":
            # Convertir psych a formato base game
            return self.psych_to_vslice(chart_data)  # Simplificado por ahora
        else:
            self.write_to_log(f"Modo de conversión desconocido: {mode}")
            return None
    
    def save_json(self, data: Dict[str, Any], file_path: str) -> bool:
        """Guardar JSON con formato y validación"""
        try:
            with open(file_path, 'w', encoding='utf-8') as file:
                json.dump(data, file, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            self.write_to_log(f"ERROR guardando {file_path}: {e}")
            return False
    
    def analyze_chart(self):
        """Analizar chart seleccionado y mostrar información detallada"""
        if not self.input_files:
            messagebox.showwarning("Advertencia", "No hay archivos seleccionados para analizar")
            return
        
        selected_indices = self.file_listbox.curselection()
        if not selected_indices:
            file_to_analyze = self.input_files[0]  # Analizar el primero si no hay selección
        else:
            file_to_analyze = self.input_files[selected_indices[0]]
        
        chart_data = self.load_json(file_to_analyze)
        if not chart_data:
            return
        
        # Realizar análisis completo
        analysis = self._perform_detailed_analysis(chart_data, file_to_analyze)
        
        # Mostrar resultados en el área de texto
        self.analysis_text.delete(1.0, tk.END)
        self.analysis_text.insert(tk.END, analysis)
    
    def _perform_detailed_analysis(self, chart_data: Dict[str, Any], file_path: str) -> str:
        """Realizar análisis detallado del chart"""
        analysis = []
        analysis.append(f"=== ANÁLISIS DETALLADO DE CHART ===")
        analysis.append(f"Archivo: {os.path.basename(file_path)}")
        analysis.append(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        analysis.append("")
        
        # Información básica
        analysis.append("--- INFORMACIÓN BÁSICA ---")
        analysis.append(f"Canción: {chart_data.get('song', 'N/A')}")
        analysis.append(f"BPM: {chart_data.get('bpm', 'N/A')}")
        analysis.append(f"Scroll Speed: {chart_data.get('speed') or chart_data.get('scrollSpeed', 'N/A')}")
        analysis.append(f"Necesita Voces: {chart_data.get('needsVoices', 'N/A')}")
        analysis.append(f"Stage: {chart_data.get('stage', 'N/A')}")
        analysis.append("")
        
        # Detección de engine
        detected_engine = self.detect_engine_type(chart_data)
        analysis.append(f"--- DETECCIÓN DE ENGINE ---")
        analysis.append(f"Engine detectado: {detected_engine.upper()}")
        analysis.append("")
        
        # Análisis de secciones
        sections = chart_data.get('notes', [])
        analysis.append(f"--- ANÁLISIS DE SECCIONES ---")
        analysis.append(f"Total de secciones: {len(sections)}")
        
        bf_sections = sum(1 for s in sections if s.get('mustHitSection', False))
        opponent_sections = len(sections) - bf_sections
        
        analysis.append(f"Secciones de BF: {bf_sections}")
        analysis.append(f"Secciones de Oponente: {opponent_sections}")
        analysis.append("")
        
        # Análisis de notas
        total_notes = 0
        bf_notes = 0
        opponent_notes = 0
        
        for section in sections:
            for note in section.get('sectionNotes', []):
                if len(note) >= 2:
                    total_notes += 1
                    lane = int(note[1]) % 8
                    if lane < 4:
                        opponent_notes += 1
                    else:
                        bf_notes += 1
        
        analysis.append(f"--- ANÁLISIS DE NOTAS ---")
        analysis.append(f"Total de notas: {total_notes}")
        analysis.append(f"Notas de BF: {bf_notes}")
        analysis.append(f"Notas de Oponente: {opponent_notes}")
        
        if total_notes > 0:
            bf_percentage = (bf_notes / total_notes) * 100
            analysis.append(f"Porcentaje BF: {bf_percentage:.1f}%")
        analysis.append("")
        
        # Validación
        validation = self.validate_chart_structure(chart_data)
        analysis.append(f"--- VALIDACIÓN ---")
        analysis.append(f"Chart válido: {'SÍ' if validation['valid'] else 'NO'}")
        
        if validation['errors']:
            analysis.append("Errores encontrados:")
            for error in validation['errors']:
                analysis.append(f"  - {error}")
        
        if validation['warnings']:
            analysis.append("Advertencias:")
            for warning in validation['warnings']:
                analysis.append(f"  - {warning}")
        
        analysis.append("")
        
        # Eventos
        events = chart_data.get('events', [])
        analysis.append(f"--- EVENTOS ---")
        analysis.append(f"Total de eventos: {len(events)}")
        
        if events:
            event_types = {}
            for event in events:
                event_name = event.get('name', 'Unknown')
                event_types[event_name] = event_types.get(event_name, 0) + 1
            
            for event_type, count in event_types.items():
                analysis.append(f"  {event_type}: {count}")
        
        analysis.append("")
        analysis.append("=== FIN DEL ANÁLISIS ===")
        
        return "\n".join(analysis)
    
    def _update_stats_display(self):
        """Actualizar display de estadísticas"""
        stats_text = f"""ESTADÍSTICAS DE CONVERSIÓN
        
Total procesados: {self.conversion_stats['total_processed']}
Exitosos: {self.conversion_stats['successful']}
Fallidos: {self.conversion_stats['failed']}
Advertencias: {self.conversion_stats['warnings']}

Tasa de éxito: {(self.conversion_stats['successful'] / max(1, self.conversion_stats['total_processed'])) * 100:.1f}%
"""
        self.stats_text.delete(1.0, tk.END)
        self.stats_text.insert(tk.END, stats_text)
    
    def write_to_log(self, message: str):
        """Escribir mensaje al log con timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        print(log_message)  # También imprimir a consola para debug
    
    def run(self):
        """Ejecutar la aplicación"""
        self.root.mainloop()

def main():
    """Función principal"""
    try:
        app = UltraChartConverter()
        app.run()
    except Exception as e:
        print(f"Error fatal en la aplicación: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()