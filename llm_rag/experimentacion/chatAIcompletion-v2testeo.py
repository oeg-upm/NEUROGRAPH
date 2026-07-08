# ============================================
# SCRIPT PYTHON - GraphRAG con Ollama + RDF
# (Versión Unificada y Optimizada)
# ============================================

import os
import sys
import json
import re
import datetime
import asyncio
import unittest
from time import time, sleep
from uuid import uuid4

from openai import OpenAI, AsyncOpenAI
from rdflib import Graph
#import nest_asyncio

# Imports propios
from searchInGraph import (
    buscar_frecuentes_por_opcion,
    inferir_valor_adecuado
)

from formatHelper import (
    extraer_support_category,
    extraer_cliente,
    formatear_para_llm,
    arreglar_lista_llm,
    extraer_respuesta_limpia_llm,
    merge_lista_y_parametro,
    formatear_datos_existentes_LLM
)

import config

# Aplicar nest_asyncio para permitir bucles de eventos anidados
#nest_asyncio.apply()

# ============================================
# CARGA DEL GRAFO RDF Y MODELO
# ============================================

graph = Graph()
graph.parse(
    config.TTL_FILE_PATH,
    format=config.TTL_FORMAT
)

print("Grafo cargado correctamente")
print(f"Número de triples: {len(graph)}")



# ============================================
# FUNCIONES AUXILIARES
# ============================================

def open_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as infile:
        return infile.read()


def save_file(filepath, content):
    with open(filepath, 'w', encoding='utf-8') as outfile:
        outfile.write(content)


def load_json(filepath):
    with open(filepath, 'r', encoding='utf-8') as infile:
        return json.load(infile)


def save_json(filepath, payload):
    with open(filepath, 'w', encoding='utf-8') as outfile:
        json.dump(payload, outfile, ensure_ascii=False, sort_keys=True, indent=2)


def timestamp_to_datetime(unix_time):
    return datetime.datetime.fromtimestamp(unix_time).strftime("%A, %B %d, %Y at %I:%M%p %Z")


#def primer_elemento_valido(array):
#    for elemento in array:
#        if elemento is not None and elemento != "ERROR":
#            return elemento
#    return None  # Retorna None si todos son None o "ERROR"

def obtener_mas_comun(arr):
    return max(set(arr), key=arr.count)
# ============================================
# FUNCIONES DE LLM (Clásico y Asíncrono)
# ============================================

def text_completion(prompt, engine=config.MI_MODELO):
    max_retry = 5
    retry = 0

    while True:
        try:
            response = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=engine
            )
            text = response.choices[0].message.content
            text = re.sub(r'[\r\n]+', '\n', text)
            text = re.sub(r'[\t ]+', ' ', text)
            return text
        except Exception as oops:
            retry += 1
            if retry >= max_retry:
                return f"Model error: {oops}"
            print("Error comunicando con el modelo:", oops)
            sleep(config.RETRY_DELAY_SECONDS)


async def text_completion_async(prompt, engine=config.MI_MODELO):
    max_retry = 5
    retry = 0

    while True:
        try:
            response = await config.async_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=engine
            )
            text = response.choices[0].message.content
            text = re.sub(r'[\r\n]+', '\n', text)
            text = re.sub(r'[\t ]+', ' ', text)
            return text
        except Exception as oops:
            retry += 1
            if retry >= max_retry:
                return f"Model error: {oops}"
            print(f"Error comunicando con el modelo (Intento {retry}/{max_retry}):", oops)
            await asyncio.sleep(config.RETRY_DELAY_SECONDS)


async def text_completion_batch(prompts_list, engine=config.MI_MODELO):
    tasks = [text_completion_async(prompt, engine) for prompt in prompts_list]
    results = await asyncio.gather(*tasks)
    return results




def completar_siguiente_campo(mis_datos):

    if None not in mis_datos and 'None' not in mis_datos:
        print(f'\nGraphRAG: query acabada. La query es {mis_datos}')
        return False, mis_datos
    
    try:
        cat_buscar = mis_datos.index(None)
    except ValueError:
        cat_buscar = mis_datos.index('None')

        # ----------------------------------------
        # CONSULTA AL GRAFO RDF
        # ----------------------------------------
    graph_data = buscar_frecuentes_por_opcion(graph, mis_datos, cat_buscar)
    if not graph_data:
        graph_data = inferir_valor_adecuado(graph, mis_datos, cat_buscar)

        
    # ----------------------------------------
    # LÓGICA DE REINTENTOS Y LLM
    # ----------------------------------------

    
    #max_a_probar = len(graph_data) if graph_data else 0
    #siguiente_a_probar = 1
    #retry = True

    
    #retry = False
    #prev_conv = open_file(log_file_path)
    if not graph_data:
        data = "No se encontraron datos. Seguramente sea un error por parte del usuario. Pregunta si se ha introducido bien el grupo."
    else:
        mi_opcion = graph_data[0]
        #if retry and siguiente_a_probar < max_a_probar:
        #    mi_opcion = graph_data[siguiente_a_probar]
        #    siguiente_a_probar += 1
        data = (
            f"El campo a rellenar es "
            f"{config.DICCIONARIO_PREFIJOS[cat_buscar]}"
            f" y estas son las opciones:\n\nrepcon:"
            f"{config.DICCIONARIO_PREFIJOS[cat_buscar]}"
            f" repcon:{mi_opcion}"
        )
    # Preparar prompt
    reglas = formatear_para_llm(
        './textos/reglas_incidentes.json',
        tipo_cond=config.DICCIONARIO_PREDICADOS[cat_buscar]
    )
    prompt_base = open_file(config.CONTEXTO_FILE_PATH)
    mensajeinstruc = "Se espera que extraigas el campo " + config.DICCIONARIO_PREFIJOS[cat_buscar]
    
    datos_existentes = formatear_datos_existentes_LLM(mis_datos)
    
    prompt = (
        prompt_base
        .replace('<<DATOS>>', data)
        .replace('<<CONVERSACIÓN>>', datos_existentes)
        .replace('<<MENSAJE>>', mensajeinstruc)
        .replace('<<REGLAS>>', "\n".join(reglas))
    )
    #print("Datos nuevos")
    #print(data)
    #print("Datos existentes")
    #print(datos_existentes)
    print("Reglas")
    print(reglas)
    
    # Ejecutar LLM en paralelo usando asyncio (proveniente del Script 1)
    outputs = asyncio.run(text_completion_batch([prompt, prompt, prompt]))
    print(outputs)
    # Procesar y limpiar respuesta
    nuevo = []
    for x in outputs:
        limpio = extraer_respuesta_limpia_llm(arreglar_lista_llm(x))
        nuevo.append(limpio.replace("repcon:", "").replace('"ERROR"', "ERROR").replace("'ERROR'", "ERROR"))

    print(nuevo)
    output = obtener_mas_comun(nuevo)

    #print(output)
    mis_datos = merge_lista_y_parametro(mis_datos, output)
    
    
    if output == 'ERROR':
        mis_datos[cat_buscar] = output
         
    print("\n--- Estado actualizado de mis_datos ---")
    print(mis_datos)
    
    return mis_datos


def preprocesado(mis_datos):
    # Definimos la longitud máxima requerida según el ejemplo
    MAX_LEN = 6
    
    # expected: La lista original rellenada con 'None' hasta llegar a 6 elementos
    expected = mis_datos + [None] * (MAX_LEN - len(mis_datos))
    
    # mis_datospre: La lista sin el último elemento ([:-1]), rellenada con 'None'
    mis_datospre = mis_datos[:-1] + [None] * (MAX_LEN - len(mis_datos[:-1]))
    
    return mis_datospre, expected


def procesar_query(item_json, archivo_salida):
    # 1. Extraemos los datos necesarios del JSON
    query_text = item_json.get("query", "")
    mis_datos = item_json.get("expected", [])
    ruletype = item_json.get("ruletype", "Desconocido")
    ruleField = item_json.get("ruleField", "Desconocido")
    
    # 2. Preprocesamos la lista original extraída del JSON
    # (Asumiendo que 'preprocesado' es la función que definimos antes)
    mis_datospre, expected = preprocesado(mis_datos)
    
    # 3. Tu lógica de predicción
    result = completar_siguiente_campo(mis_datospre)

    # 4. Verificamos si la predicción es exacta
    acierto = (result == expected)
    
    # Escribimos los logs en el archivo externo pasándole el parámetro 'file'
    estado = "✅ ACIERTO" if acierto else "❌ FALLO"
    print(f"{estado} | RuleType: {ruletype} | RuleField: {ruleField}", file=archivo_salida)
    if not acierto:
        print(f"   Esperado: {expected}", file=archivo_salida)
        print(f"   Obtenido: {result}", file=archivo_salida)
    print(f'GraphRAG: query acabada. La query es: "{query_text}"\n', file=archivo_salida)

    return acierto, ruletype, ruleField


# ============================================
# BLOQUE PRINCIPAL (AUTOMATIZADO Y REGISTRO)
# ============================================

if __name__ == '__main__':
    
    # Archivos
    nombre_archivo = './textos/datasetsantolimpio3.json'
    archivo_reporte = './results/resultado_fin8.txt'  # <-- Nombre del archivo de salida
    
    # Diccionarios para registrar aciertos y fallos
    registro_ruletype = {}
    registro_ruleField = {}
    
    try:
        with open(nombre_archivo, 'r', encoding='utf-8') as f:
            dataset = json.load(f)
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo '{nombre_archivo}'. Asegúrate de que está en la misma carpeta.")
        exit()

    total_casos = len(dataset)
    aciertos_globales = 0

    # Abrimos el archivo de salida en modo escritura ('w') con codificación utf-8
    with open(archivo_reporte, 'w', encoding='utf-8') as out_f:
        
        print("=" * 50, file=out_f)
        print(f" INICIANDO EVALUACIÓN DE {total_casos} QUERIES ", file=out_f)
        print("=" * 50, file=out_f)

        for item in dataset:
            # Evaluamos la query pasando también el archivo abierto
            acierto, r_type, r_field = procesar_query(item, out_f)
            
            # Inicializamos contadores si es la primera vez que vemos esta regla/campo
            if r_type not in registro_ruletype:
                registro_ruletype[r_type] = {"aciertos": 0, "fallos": 0}
            if r_field not in registro_ruleField:
                registro_ruleField[r_field] = {"aciertos": 0, "fallos": 0}
                
            # Actualizamos los contadores según el resultado
            if acierto:
                registro_ruletype[r_type]["aciertos"] += 1
                registro_ruleField[r_field]["aciertos"] += 1
                aciertos_globales += 1
            else:
                registro_ruletype[r_type]["fallos"] += 1
                registro_ruleField[r_field]["fallos"] += 1

        # --- REPORTE FINAL ---
        print("============================================", file=out_f)
        print("              RESUMEN DE PRUEBAS            ", file=out_f)
        print("============================================", file=out_f)
        print(f"Total de queries : {total_casos}", file=out_f)
        print(f"Aciertos totales : {aciertos_globales}", file=out_f)
        print(f"Fallos totales   : {total_casos - aciertos_globales}", file=out_f)
        print(f"Precisión Global : {(aciertos_globales / total_casos) * 100:.2f}%\n", file=out_f)
        
        print("--- Resultados por 'ruletype' ---", file=out_f)
        for rt, conteo in registro_ruletype.items():
            total_rt = conteo['aciertos'] + conteo['fallos']
            porcentaje = (conteo['aciertos'] / total_rt) * 100 if total_rt > 0 else 0
            print(f"  {rt.ljust(10)}: {conteo['aciertos']} aciertos, {conteo['fallos']} fallos ({porcentaje:.1f}%)", file=out_f)

        print("\n--- Resultados por 'ruleField' ---", file=out_f)
        for rf, conteo in registro_ruleField.items():
            total_rf = conteo['aciertos'] + conteo['fallos']
            porcentaje = (conteo['aciertos'] / total_rf) * 100 if total_rf > 0 else 0
            print(f"  {rf.ljust(20)}: {conteo['aciertos']} aciertos, {conteo['fallos']} fallos ({porcentaje:.1f}%)", file=out_f)

    # Aviso final en la consola real de que el proceso ha terminado
    print(f"Proceso completado con éxito. Todo el resultado se ha volcado en '{archivo_reporte}'.")