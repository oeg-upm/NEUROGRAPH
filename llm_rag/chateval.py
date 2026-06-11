# ============================================
# SCRIPT PYTHON - GraphRAG con Ollama + RDF
# (Versión Unificada y Optimizada)
# ============================================

import os
import json
import re
import datetime
import asyncio
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

client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama"
)

mi_modelo = "mistral:latest"
print(f"Modelo configurado: {mi_modelo}")


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


def elemento_mas_comun(array):
    return max(array, key=array.count)


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



# ============================================
# BLOQUE PRINCIPAL (BUCLE INTERACTIVO)
# ============================================

if __name__ == '__main__':
    print("\n" + "=" * 40)
    print(" SISTEMA GraphRAG + Ollama INICIADO")
    print("====================================")
    print("Escribe 'q' para salir")

    # Inicialización de variables de estado
    convo_length = 2
    unique_conv_id = str(uuid4())
    prev_conv = ""
    filename = unique_conv_id + "_log.txt"
    log_file_path = os.path.join(config.LOGS_DIR, filename)

    save_file(log_file_path, prev_conv)
    a =""
    primera = True
    mis_datos = [None, None, None, None, None, None]

    while True:

        if None not in mis_datos and 'None' not in mis_datos:
            print('\nGraphRAG: query acabada. La query completada es:')
            print(mis_datos)
            break


        if primera:
            a = input('\nUSER: ')


        primera = False

        if a.lower() == "q":
            print("\nFinalizando conversación...")
            break

        timestamp = time()
        timestring = timestamp_to_datetime(timestamp)
        message = f"USER: {timestring} - {a}"

        # ----------------------------------------
        # EXTRACCIÓN DE DATOS INICIALES
        # ----------------------------------------
        if mis_datos[0] is None:
            cliente = extraer_cliente(a)
            if cliente: print(f"Cliente extraído: {cliente}")
            mis_datos[0] = cliente

        if mis_datos[1] is None:
            support_cat = extraer_support_category(a)
            mis_datos[1] = support_cat

        # ----------------------------------------
        # VERIFICACIÓN DE FIN DE BÚSQUEDA
        # ----------------------------------------


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
        max_a_probar = len(graph_data) if graph_data else 0
        siguiente_a_probar = 1
        retry = True

        while retry:
            retry = False
            prev_conv = open_file(log_file_path)

            if not graph_data:
                data = "No se encontraron datos. Seguramente sea un error por parte del usuario. Pregunta si se ha introducido bien el grupo."
            else:
                mi_opcion = graph_data[0]
                if retry and siguiente_a_probar < max_a_probar:
                    mi_opcion = graph_data[siguiente_a_probar]
                    siguiente_a_probar += 1

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
            datos_existentes = formatear_datos_existentes_LLM(graph_data)

            prompt = (
                prompt_base
                .replace('<<DATOS>>', data)
                .replace('<<CONVERSACIÓN>>', datos_existentes)
                .replace('<<MENSAJE>>', mensajeinstruc)
                .replace('<<REGLAS>>', "\n".join(reglas))
            )

            # Ejecutar LLM en paralelo usando asyncio (proveniente del Script 1)
            outputs = asyncio.run(text_completion_batch([prompt, prompt, prompt]))

            # Procesar y limpiar respuesta
            nuevo = []
            for x in outputs:
                limpio = extraer_respuesta_limpia_llm(arreglar_lista_llm(x)).replace("repcon:", "")
                nuevo.append(limpio)

            output = elemento_mas_comun(nuevo)
            mis_datos = merge_lista_y_parametro(mis_datos, output)

            print("\n--- Estado actualizado de mis_datos ---")
            print(mis_datos)

            if output == "ERROR":
                retry = True

        # ----------------------------------------
        # GUARDAR LOG Y RESPONDER
        # ----------------------------------------
        timestamp = time()
        timestring = timestamp_to_datetime(timestamp)
        messageBot = f"[Asistente]: {timestring} - {output}"

        print(f"\n[Asistente]: {output}")

        save_file(
            log_file_path,
            prev_conv + "\n" + message + "\n" + messageBot
        )