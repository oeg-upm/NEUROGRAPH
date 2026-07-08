import re
import os

def anonimizar_texto(texto_original):
    # Diccionario para almacenar las equivalencias y mantener la consistencia
    mappings = {}
    
    # Contadores individuales para generar ID secuenciales (1, 2, 3...)
    # Se eliminan typeIncident e incidentOrigin para que no se alteren
    counters = {
        'company': 0,
        'supportCategory': 0,
        'supportGroup': 0,
        'employee': 0
    }

    # --- FASE 1: Procesar identificadores con prefijos conocidos ---
    def repl_prefixes(match):
        full_str = match.group(0)
        prefix = match.group(1)
        
        if full_str in mappings:
            return mappings[full_str]
        
        if 'company' in prefix:
            base_type = 'company'
        elif 'supportCategory' in prefix:
            base_type = 'supportCategory'
        elif 'supportGroup' in prefix:
            base_type = 'supportGroup'
        elif 'employee' in prefix:
            base_type = 'employee'
        else:
            base_type = 'entidad'
            
        counters[base_type] += 1
        anon_name = f"{base_type}_{counters[base_type]}"
        mappings[full_str] = anon_name
        return anon_name

    # Se eliminaron 'typeIncident__' e 'incidentOrigin__' del patrón de regex
    pattern_prefixes = r'\b(company__|company_|supportCategory_|supportGroup_|employee__)[A-Za-z0-9]+\b'
    texto_procesado = re.sub(pattern_prefixes, repl_prefixes, texto_original)

    # --- FASE 2: Procesar nombres de empresas cortos (ej: "la empresa ss") ---
    def repl_raw_companies(match):
        literal_empresa = match.group(1)
        spacing = match.group(2)
        company_name = match.group(3)
        
        if re.match(r'^company_\d+$', company_name):
            return match.group(0)
        
        if company_name in mappings:
            anon_name = mappings[company_name]
        else:
            counters['company'] += 1
            anon_name = f"company_{counters['company']}"
            mappings[company_name] = anon_name
            
        return f"{literal_empresa}{spacing}{anon_name}"

    pattern_raw_company = r'\b(la empresa)(\s+)([A-Za-z0-9]+)\b'
    texto_procesado = re.sub(pattern_raw_company, repl_raw_companies, texto_procesado)
    
    # --- FASE 3: Eliminar emojis ---
    # Este patrón cubre los rangos Unicode más comunes de emojis y símbolos
    pattern_emojis = re.compile(
        r'[\U00010000-\U0010ffff]'  # Caracteres de plano superior (la mayoría de emojis)
        r'|[\u2600-\u27BF]'          # Símbolos misceláneos y dingbats (estrellas, corazones, etc.)
        r'|[\u2300-\u23FF]'          # Símbolos técnicos misceláneos (relojes, etc.)
    )
    texto_final = pattern_emojis.sub('', texto_procesado)
    
    return texto_final, mappings


def anonimizar_archivo(ruta_entrada, ruta_salida):
    """Lee el archivo de entrada, lo anonimiza, quita emojis y guarda el resultado."""
    if not os.path.exists(ruta_entrada):
        print(f"Error crítico: El archivo de origen '{ruta_entrada}' no existe.")
        print("Asegúrate de que la ruta sea correcta y el archivo esté allí.")
        return

    print(f"Leyendo archivo origen: {ruta_entrada}...")
    with open(ruta_entrada, 'r', encoding='utf-8') as f:
        contenido = f.read()
    
    contenido_anonimo, mapeos = anonimizar_texto(contenido)
    
    print(f"Guardando archivo anonimizado en: {ruta_salida}...")
    with open(ruta_salida, 'w', encoding='utf-8') as f:
        f.write(contenido_anonimo)
        
    print(f"¡Proceso completado con éxito!")
    print(f"Se han anonimizado {len(mapeos)} entidades únicas manteniendo la consistencia.")



def numerar_casos(texto_traza):
    lineas = texto_traza.split('\n')
    resultado = []
    contador = 1
    
    for linea in lineas:
        # Detecta si la línea empieza con ACIERTO o FALLO (puede tener espacios al inicio)
        if re.match(r'^\s*(ACIERTO|FALLO)\b', linea):
            # Limpia espacios extraños y añade el número al frente
            linea_limpia = linea.strip()
            resultado.append(f"{contador}. {linea_limpia}")
            contador += 1
        else:
            resultado.append(linea)
            
    return '\n'.join(resultado)

# --- EJEMPLO DE USO ---
# Si guardas tu traza en un archivo llamado 'traza_original.txt'


    
# --- BLOQUE DE EJECUCIÓN EXCLUSIVO DE LECTURA ---
if __name__ == "__main__":
    # Definición de rutas (reemplaza o usa estas)
    archivo_input = "../results/resultado_fin8.txt"
    archivo_output = "log_anonimizado2.txt"
        
    # Ejecutamos la anonimización directamente leyendo tu archivo existente
    #anonimizar_archivo(archivo_input, archivo_output)
    try:
        with open('log_anonimizado2.txt', 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        contenido_numerado = numerar_casos(contenido)
        
        with open('traza_numerada.txt', 'w', encoding='utf-8') as f:
            f.write(contenido_numerado)
            
        print("¡Traza numerada con éxito y guardada en 'traza_numerada.txt'!")
    except FileNotFoundError:
        print("Para probarlo, guarda la traza en un archivo llamado 'traza_original.txt'")