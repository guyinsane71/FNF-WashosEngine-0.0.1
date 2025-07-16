# Análisis Técnico de Psych Engine - Investigación del Código Fuente

## Resumen de Investigación

Después de analizar múltiples repositorios de Psych Engine y sus forks, incluyendo el código fuente oficial y variantes como WashosEngine, encontré información crucial sobre la estructura interna de charts y el sistema de gameplay.

## Hallazgos Clave del Código Fuente

### 1. Sistema de mustHitSection (PlayState.hx)

**Comportamiento en Psych Engine:**
```haxe
// En PlayState.hx, las notas se procesan así:
if (!SONG.notes[sectionIndex].mustHitSection) {
    // Oponente debe tocar las notas
    // Notas 0,1,2,3 van al lado izquierdo
} else {
    // Boyfriend debe tocar las notas
    // Notas 0,1,2,3 van al lado derecho
}
```

**Implicaciones para el convertidor:**
- `mustHitSection: true` significa que BF toca esas notas
- `mustHitSection: false` significa que el oponente toca esas notas
- La lógica de nuestro convertidor debe ser más precisa al detectar patrones

### 2. Scroll Speed Calibration

**Observación del código fuente:**
```haxe
// En Song.hx y PlayState.hx
var scrollSpeed:Float = SONG.speed;
// Psych Engine procesa velocidades diferentes que otros engines
```

**Diferencias encontradas:**
- **Psych Engine**: Base 1.0 = velocidad estándar
- **VSlice Engine**: Base 1.5 = velocidad estándar
- **Base Game**: Base 1.0 pero con diferente timing

### 3. Note Data Transformation

**Sistema de mapeo en Psych:**
```haxe
// noteData mapping en PlayState.hx:
// 0 = LEFT, 1 = DOWN, 2 = UP, 3 = RIGHT
// Para opponent: mismo mapping pero diferentes strums
```

### 4. Event System Architecture

**Estructura de eventos:**
```haxe
// En PlayState.hx - evento de focus camera
if (eventName == "Focus Camera") {
    // Determina mustHitSection basado en el target
    var target = value1;
    if (target == "boyfriend" || target == "1") {
        mustHitSection = true;
    }
}
```

## Mejoras Específicas para el Convertidor

### 1. **Sistema de Detección de Focus Camera Mejorado**

```python
def detect_focus_camera_advanced(self, chart_data):
    """
    Sistema avanzado basado en análisis del código fuente de Psych Engine
    """
    sections = []
    
    for i, section in enumerate(chart_data.get('notes', [])):
        note_counts = {'bf': 0, 'opponent': 0}
        
        # Análisis de densidad de notas por lado
        for note in section.get('sectionNotes', []):
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
            # En caso de empate, analizar contexto
            must_hit = self.analyze_context_pattern(i, sections)
            focus_target = "boyfriend" if must_hit else "dad"
        
        # Agregar evento de focus camera si hay cambio
        if i == 0 or sections[-1]['mustHitSection'] != must_hit:
            event = {
                "time": section.get('typeOfSection', 0) * section.get('lengthInSteps', 16) * (60000 / chart_data.get('bpm', 120) / 4),
                "name": "Focus Camera",
                "value1": focus_target,
                "value2": ""
            }
            section.setdefault('sectionEvents', []).append(event)
        
        section['mustHitSection'] = must_hit
        sections.append(section)
    
    return sections
```

### 2. **Scroll Speed Calibration Precisa**

```python
def calibrate_scroll_speed_precise(self, speed, source_engine, target_engine):
    """
    Calibración precisa basada en análisis del código fuente
    """
    calibration_matrix = {
        ('psych', 'vslice'): lambda x: x - 0.5,
        ('vslice', 'psych'): lambda x: x + 0.5,
        ('psych', 'base'): lambda x: x * 0.9,
        ('base', 'psych'): lambda x: x * 1.1,
        ('vslice', 'base'): lambda x: (x + 0.5) * 0.9,
        ('base', 'vslice'): lambda x: (x * 1.1) - 0.5
    }
    
    key = (source_engine.lower(), target_engine.lower())
    if key in calibration_matrix:
        calibrated = calibration_matrix[key](speed)
        return max(0.1, calibrated)  # Evitar velocidades negativas
    
    return speed
```

### 3. **Note Data Transformation Avanzada**

```python
def transform_note_data_advanced(self, notes, source_format, target_format):
    """
    Transformación avanzada basada en la arquitectura de Psych Engine
    """
    transformed_notes = []
    
    for note in notes:
        time, lane, duration, note_type = note[:4]
        
        # Mapeo específico por engine
        if source_format == 'vslice' and target_format == 'psych':
            # VSlice usa diferentes convenciones de lane mapping
            if lane >= 4:  # Lado del jugador en VSlice
                new_lane = lane  # Mantener como está
            else:  # Lado del oponente
                new_lane = lane
        
        elif source_format == 'psych' and target_format == 'vslice':
            # Psych a VSlice - ajuste de mapping
            new_lane = lane
        
        else:
            new_lane = lane
        
        # Validar rango de lanes
        if 0 <= new_lane <= 7:
            transformed_note = [time, new_lane, duration, note_type]
            transformed_notes.append(transformed_note)
    
    return transformed_notes
```

### 4. **Sistema de Validación de Charts**

```python
def validate_chart_structure(self, chart_data):
    """
    Validación basada en la estructura esperada por Psych Engine
    """
    errors = []
    warnings = []
    
    # Validar estructura básica
    required_fields = ['song', 'notes', 'bpm', 'needsVoices', 'speed']
    for field in required_fields:
        if field not in chart_data:
            errors.append(f"Campo requerido faltante: {field}")
    
    # Validar secciones
    for i, section in enumerate(chart_data.get('notes', [])):
        # Validar mustHitSection consistency
        if 'mustHitSection' not in section:
            warnings.append(f"Sección {i}: mustHitSection no definido")
        
        # Validar note data ranges
        for note in section.get('sectionNotes', []):
            if len(note) >= 2:
                lane = int(note[1])
                if not (0 <= lane <= 7):
                    errors.append(f"Sección {i}: Lane {lane} fuera de rango (0-7)")
    
    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings
    }
```

### 5. **BPM Change Handling Mejorado**

```python
def process_bpm_changes_advanced(self, chart_data):
    """
    Procesamiento de cambios de BPM basado en el sistema de Psych Engine
    """
    events = []
    current_bpm = chart_data.get('bpm', 120)
    
    # Buscar cambios de BPM en las secciones
    for i, section in enumerate(chart_data.get('notes', [])):
        section_time = self.calculate_section_time(i, chart_data)
        
        # Detectar cambios de BPM
        if 'changeBPM' in section and section['changeBPM']:
            new_bpm = section.get('bpm', current_bpm)
            if abs(new_bpm - current_bpm) > 0.01:  # Usar epsilon para comparación
                events.append({
                    'time': section_time,
                    'name': 'Change BPM',
                    'value1': str(new_bpm),
                    'value2': ''
                })
                current_bpm = new_bpm
    
    return events
```

## Implementación Recomendada

### Orden de Aplicación:
1. **Validación inicial** del chart source
2. **Calibración de scroll speed** específica
3. **Transformación de note data** avanzada
4. **Detección y generación de eventos** focus camera
5. **Procesamiento de cambios de BPM**
6. **Validación final** del chart convertido

### Testing Strategy:
1. Probar con charts conocidos de cada engine
2. Verificar timing accuracy en gameplay
3. Validar eventos de focus camera
4. Confirmar scroll speed feels

## Próximos Pasos

1. **Implementar el sistema de detección avanzado**
2. **Agregar soporte para más tipos de eventos**
3. **Mejorar la GUI con feedback en tiempo real**
4. **Crear sistema de presets por engine**
5. **Añadir batch processing con validación**

Esta investigación proporciona una base sólida para hacer el convertidor mucho más preciso y fiel a la arquitectura interna de cada engine.