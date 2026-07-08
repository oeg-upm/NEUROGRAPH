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


def primer_elemento_valido(array):
    for elemento in array:
        if elemento is not None and elemento != "ERROR":
            return elemento
    return None  # Retorna None si todos son None o "ERROR"


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
    max_a_probar = len(graph_data) if graph_data else 0
    siguiente_a_probar = 1
    retry = True
    while retry:
        retry = False
        #prev_conv = open_file(log_file_path)
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
        output = primer_elemento_valido(nuevo)
        mis_datos = merge_lista_y_parametro(mis_datos, output)
        print("\n--- Estado actualizado de mis_datos ---")
        print(mis_datos)
        if output == "ERROR":
            retry = True
    
    return True, mis_datos


def procesar_query(texto):
    mis_datos = [None, None, None, None, None, None]
    
    mis_datos[0] = extraer_cliente(texto)
    mis_datos[1] = extraer_support_category(texto)

    intentos = 0
    
    while intentos <20:
        intentos +=1
        continuar, mis_datos = completar_siguiente_campo(mis_datos)
        #print(mis_datos)
        if not continuar:
            
            break
    
    print(f'\nGraphRAG: query acabada. La query es {mis_datos}')

    return mis_datos



    
# ============================================
# PRUEBAS UNITARIAS
# ============================================

class TestQueryProcessor(unittest.TestCase):
    def setUp(self):
        self.casos_de_prueba = [
            # 1 - 10 se activa solo DF
          #  (
          #      'Hola quiero completar una query. Tengo el supportCategory_1497617941762302663 y la empresa company_149762002231762302862',
          #      
          #      ['company__F7UMNAXNO', 'supportCategory_1497617941762302663', 'typeIncident__2', 'incidentOrigin__3',
          #       'supportGroup_149762881762302662', 'employee__294']
          #  ),

         #   (
         #       'Hola quiero completar una query. Tengo el supportCategory_149762916841762302974 y la empresa company__UQHIM9QXH',
         #       ['company__UQHIM9QXH', 'supportCategory_149762916841762302974', 'typeIncident__1', 'incidentOrigin__2',
         #        'supportGroup_14976631762302662', 'employee__486']
         #   ),
         #   (
         #       'Hola quiero completar una query. Tengo el supportCategory_149763527461762303053 y la empresa company__QWY4YPRG7',
         #       ['company__QWY4YPRG7', 'supportCategory_149763527461762303053', 'typeIncident__1', 'incidentOrigin__3',
         #        'supportGroup_149762881762302662', 'employee__294']
         #   ),
            
         #   (
         #       'Hola quiero completar una query. Tengo el supportCategory_1497611841762302662 y la empresa company__1GR6455ID',
         #       ['company__1GR6455ID', 'supportCategory_1497611841762302662', 'typeIncident__1', 'incidentOrigin__2',
         #        'supportGroup_14976631762302662', 'employee__259']
         #   )
            ,
       #    (
       #        'Hola quiero completar una query. Tengo el supportCategory_149761991762302662 y la empresa company__2ZFMBC970',
       #        ['company__2ZFMBC970', 'supportCategory_149761991762302662', 'typeIncident__1', 'incidentOrigin__2',
       #         'supportGroup_1497684871762302665', 'employee__366']
       #    ),
       #     (
       #         'Hola quiero completar una query. Tengo el supportCategory_149767291231762303563 y la empresa ss',
       #         ['ss', 'supportCategory_149767291231762303563', 'typeIncident__1', 'incidentOrigin__2',
       #          'supportGroup_14976691762302662', 'employee__366']
       #     ),
         #   (
         #       'Hola quiero completar una query. Tengo el supportCategory_1497681762302662 y la empresa company_149762002231762302862',
         #       ['company__F7UMNAXNO', 'supportCategory_1497681762302662', 'typeIncident__1', 'incidentOrigin__3',
         #        'supportGroup_149762881762302662', 'employee__294']
         #   ),
            (
                'Hola quiero completar una query. Tengo el supportCategory_1497614541762302662 y la empresa ss',
                ['ss', 'supportCategory_1497614541762302662', 'typeIncident__1', 'incidentOrigin__2',
                 'supportGroup_14976691762302662', 'employee__366']
            ),
           # (
           #     'Hola quiero completar una query. Tengo el supportCategory_149763671762302662 y la empresa company_149767814271762303637',
           #     ['company_149762002231762302862', 'supportCategory_149763671762302662', 'typeIncident__2',
           #      'incidentOrigin__3', 'supportGroup_149762881762302662', 'employee__294']
           # ),
           # (
           #     'Hola quiero completar una query. Tengo el supportCategory_149764151762302662 y la empresa company__CFD5UKZBE',
           #     ['company__CFD5UKZBE', 'supportCategory_149764151762302662', 'typeIncident__2', 'incidentOrigin__3',
           #      'supportGroup_149762881762302662', 'employee__294']
           # ),
#
            # 11-20 se activa solo nv
           # (
           #     'Hola quiero completar una query. Tengo el supportCategory_1497611981762302662 y la empresa company__D52NKD9SS',
           #     ['company__D52NKD9SS', 'supportCategory_1497611981762302662', 'typeIncident__1', 'incidentOrigin__2',
           #      'supportGroup_14976631762302662', 'employee__108']
           # ),
            (
                'Hola quiero completar una query. Tengo el supportCategory_1497611981762302662 y la empresa company__17Q32M10L',
                ['company__17Q32M10L', 'supportCategory_1497611981762302662', 'typeIncident__1', 'incidentOrigin__2',
                 'supportGroup_149761521762302662', 'employee__108']
            ),
            (
                'Hola quiero completar una query. Tengo el supportCategory_149763671762302662 y la empresa company__17Q32M10L',
                ['company__17Q32M10L', 'supportCategory_149763671762302662', 'typeIncident__2', 'incidentOrigin__2',
                 'supportGroup_149761521762302662', 'employee__294']
            ),
            (
                'Hola quiero completar una query. Tengo el supportCategory_1497691561762302665 y la empresa company__17Q32M10L',
                ['company__17Q32M10L', 'supportCategory_1497691561762302665', 'typeIncident__1', 'incidentOrigin__2',
                 'supportGroup_149761521762302662', 'employee__366']
            ),
           # (
           #     'Hola quiero completar una query. Tengo el supportCategory_149765491762302662 y la empresa company__077OCQVXM',
           #     ['company__077OCQVXM', 'supportCategory_149765491762302662', 'typeIncident__2', 'incidentOrigin__2',
           #      'supportGroup_14976631762302662', 'employee__294']
           # ),
            (
                'Hola quiero completar una query. Tengo el supportCategory_149765458501762303308 y la empresa company__UQ0EGOKMC',  #EL BUENO
                ['company__UQ0EGOKMC', 'supportCategory_149765458501762303308', 'typeIncident__2', 'incidentOrigin__2',
                 'supportGroup_149761521762302662', 'employee__294']
            ),
           # (
           #     'Hola quiero completar una query. Tengo el supportCategory_1497611981762302662 y la empresa company__DQJKY6U6E',
           #     ['company__DQJKY6U6E', 'supportCategory_1497611981762302662', 'typeIncident__1', 'incidentOrigin__2',
           #      'supportGroup_14976631762302662', 'employee__108']
           # ),
            (
                'Hola quiero completar una query. Tengo el supportCategory_149765491762302662 y la empresa company__10QMPVMGA',
                ['company__10QMPVMGA', 'supportCategory_149765491762302662', 'typeIncident__2', 'incidentOrigin__2', #hecho
                 'supportGroup_14976631762302662', 'employee__294']
            ),
            (
                'Hola quiero completar una query. Tengo el supportCategory_149763371762302662 y la empresa company__17Q32M10L',
                ['company__17Q32M10L', 'supportCategory_149763371762302662', 'typeIncident__1', 'incidentOrigin__2',
                 'supportGroup_149761521762302662', 'employee__366']
            ),
            (
                'Hola quiero completar una query. Tengo el supportCategory_149765491762302662 y la empresa company__HVY8FPJ74',
                ['company__HVY8FPJ74', 'supportCategory_149765491762302662', 'typeIncident__2', 'incidentOrigin__2',
                 'supportGroup_14976631762302662', 'employee__294']
            ),

            # 21-30 se activan ambas en el mismo momento
            (
                'Hola quiero completar una query. Tengo el supportCategory_149767060481762303533 y la empresa company_149767070781762303534',
                ['company__3S8A2Y7FV', 'supportCategory_149767060481762303533', 'typeIncident__1', 'incidentOrigin__2',
                 'supportGroup_149765457361762303308', 'employee__429']
            ),
            (
                'Hola quiero completar una query. Tengo el supportCategory_149767060481762303533 y la empresa company_149761171471762302766',
                ['company__3S8A2Y7FV', 'supportCategory_149767060481762303533', 'typeIncident__1', 'incidentOrigin__2',
                 'supportGroup_149765457361762303308', 'employee__429']
            ),
            (
                'Hola quiero completar una query. Tengo el supportCategory_149762916841762302974 y la empresa company_14976568571762302706',
                ['company__3S8A2Y7FV', 'supportCategory_149762916841762302974', 'typeIncident__1', 'incidentOrigin__2',
                 'supportGroup_149769961762302662', 'employee__429']
            ),
            (
                'Hola quiero completar una query. Tengo el supportCategory_1497617231762302663 y la empresa company__3S8A2Y7FV',
                ['company__3S8A2Y7FV', 'supportCategory_1497617231762302663', 'typeIncident__1', 'incidentOrigin__2',
                 'supportGroup_14976631762302662', 'employee__429']
            ),
            (
                'Hola quiero completar una query. Tengo el supportCategory_149762916841762302974 y la empresa company_149763729881762303079',
                ['company__3S8A2Y7FV', 'supportCategory_149762916841762302974', 'typeIncident__1', 'incidentOrigin__2',
                 'supportGroup_149769961762302662', 'employee__429']
            ),
            (
                'Hola quiero completar una query. Tengo el supportCategory_149767601762302662 y la empresa company_149766665321762303469',
                ['company__3S8A2Y7FV', 'supportCategory_149767601762302662', 'typeIncident__1', 'incidentOrigin__2',
                 'supportGroup_149764431762302662', 'employee__429']
            ),
            (
                'Hola quiero completar una query. Tengo el supportCategory_14976411762302662 y la empresa company_149767814271762303637',
                ['company__3S8A2Y7FV', 'supportCategory_14976411762302662', 'typeIncident__2', 'incidentOrigin__1',
                 'supportGroup_149762761762302662', 'employee__429']
            ),
            (
                'Hola quiero completar una query. Tengo el supportCategory_149763471762302662 y la empresa company_149764841521762303225',
                ['company__3S8A2Y7FV', 'supportCategory_149763471762302662', 'typeIncident__1', 'incidentOrigin__2',
                 'supportGroup_149763481762302662', 'employee__429']
            ),
            (
                'Hola quiero completar una query. Tengo el supportCategory_149763834511762303087 y la empresa company_149764242351762303146',
                ['company__3S8A2Y7FV', 'supportCategory_149763834511762303087', 'typeIncident__2', 'incidentOrigin__2',
                 'supportGroup_149762761762302662', 'employee__429']
            ),
            (
                'Hola quiero completar una query. Tengo el supportCategory_1497631491762302663 y la empresa company__3S8A2Y7FV',
                ['company__3S8A2Y7FV', 'supportCategory_1497631491762302663', 'typeIncident__1', 'incidentOrigin__2',
                 'supportGroup_14976631762302662', 'employee__429']
            ),

            # 31-32 se activa una df y una nv en momentos distintos
            (
                'Hola quiero completar una query. Tengo el supportCategory_14976110321762302666 y la empresa company__W0S6TBURD',
                ['company__W0S6TBURD', 'supportCategory_14976110321762302666', 'typeIncident__1', 'incidentOrigin__3',
                 'supportGroup_149762881762302662', 'employee__294']
            ),
            (
                'Hola quiero completar una query. Tengo el supportCategory_1497610291762302662 y la empresa company__UQ0EGOKMC',
                ['company__UQ0EGOKMC', 'supportCategory_1497610291762302662', 'typeIncident__2', 'incidentOrigin__3',
                 'supportGroup_149762881762302662', 'employee__294']
            ),

            # 33 - 50 no se activa ninguna regla
            (
                'Hola quiero completar una query. Tengo el supportCategory_149769471762302662 y la empresa company__IJVARZ08A',
                ['company__IJVARZ08A', 'supportCategory_149769471762302662', 'typeIncident__2', 'incidentOrigin__2',
                 'supportGroup_14976631762302662', 'employee__266']
            ),
            (
                'Hola quiero completar una query. Tengo el supportCategory_1497623551762302663 y la empresa company__Y1XHYEPUS',
                ['company__Y1XHYEPUS', 'supportCategory_1497623551762302663', 'typeIncident__2', 'incidentOrigin__2',
                 'supportGroup_14976631762302662', 'employee__294']
            ),
            (
                'Hola quiero completar una query. Tengo el supportCategory_1497622131762302663 y la empresa company_149766632941762303467',
                ['company__QCTRKWQRI', 'supportCategory_1497622131762302663', 'typeIncident__2', 'incidentOrigin__2',
                 'supportGroup_1497691762302662', 'employee__266']
            ),
            (
                'Hola quiero completar una query. Tengo el supportCategory_149765639211762303330 y la empresa company__GBKQFD0VA',
                ['company__GBKQFD0VA', 'supportCategory_149765639211762303330', 'typeIncident__1', 'incidentOrigin__2',
                 'supportGroup_14976631762302662', 'employee__366']
            ),
            (
                'Hola quiero completar una query. Tengo el supportCategory_1497643821762302663 y la empresa company__G93IZU6VM',
                ['company__G93IZU6VM', 'supportCategory_1497643821762302663', 'typeIncident__1', 'incidentOrigin__2',
                 'supportGroup_14976631762302662', 'employee__366']
            ),
            (
                'Hola quiero completar una query. Tengo el supportCategory_14976110321762302666 y la empresa company__JAOY9VHCI',
                ['company__JAOY9VHCI', 'supportCategory_14976110321762302666', 'typeIncident__1', 'incidentOrigin__2',
                 'supportGroup_14976631762302662', 'employee__366']
            ),
            (
                'Hola quiero completar una query. Tengo el supportCategory_1497612201762302662 y la empresa company__8VD90FMG4',
                ['company__8VD90FMG4', 'supportCategory_1497612201762302662', 'typeIncident__1', 'incidentOrigin__2',
                 'supportGroup_14976631762302662', 'employee__366']
            ),
            (
                'Hola quiero completar una query. Tengo el supportCategory_1497644851762302663 y la empresa company__9G1G3MV0P',
                ['company__9G1G3MV0P', 'supportCategory_1497644851762302663', 'typeIncident__2', 'incidentOrigin__2',
                 'supportGroup_14976631762302662', 'employee__294']
            ),
            (
                'Hola quiero completar una query. Tengo el supportCategory_1497634611762302663 y la empresa company__FWP37ZIFM',
                ['company__FWP37ZIFM', 'supportCategory_1497634611762302663', 'typeIncident__1', 'incidentOrigin__2',
                 'supportGroup_14976631762302662', 'employee__366']
            ),
            (
                'Hola quiero completar una query. Tengo el supportCategory_149762050541762302872 y la empresa company__44XJYGG3L',
                ['company__44XJYGG3L', 'supportCategory_149762050541762302872', 'typeIncident__1', 'incidentOrigin__2',
                 'supportGroup_14976631762302662', 'employee__366']
            ),
            (
                'Hola quiero completar una query. Tengo el supportCategory_149762443731762302917 y la empresa company__HJLEZ1WY6',
                ['company__HJLEZ1WY6', 'supportCategory_149762443731762302917', 'typeIncident__1', 'incidentOrigin__2',
                 'supportGroup_14976631762302662', 'employee__366']
            ),
            (
                'Hola quiero completar una query. Tengo el supportCategory_1497634611762302663 y la empresa company__QRPQNRU25',
                ['company__QRPQNRU25', 'supportCategory_1497634611762302663', 'typeIncident__1', 'incidentOrigin__2',
                 'supportGroup_14976631762302662', 'employee__366']
            ),
            (
                'Hola quiero completar una query. Tengo el supportCategory_149768521762302662 y la empresa company__0GQ4QH8N2',
                ['company__0GQ4QH8N2', 'supportCategory_149768521762302662', 'typeIncident__1', 'incidentOrigin__2',
                 'supportGroup_149761521762302662', 'employee__366']
            ),
            (
                'Hola quiero completar una query. Tengo el supportCategory_149766361762302662 y la empresa company__Y1XHYEPUS',
                ['company__Y1XHYEPUS', 'supportCategory_149766361762302662', 'typeIncident__2', 'incidentOrigin__2',
                 'supportGroup_14976631762302662', 'employee__294']
            ),
            (
                'Hola quiero completar una query. Tengo el supportCategory_149767793181762303635 y la empresa company_149763071541762302992',
                ['company__10QMPVMGA', 'supportCategory_149767793181762303635', 'typeIncident__1', 'incidentOrigin__2',
                 'supportGroup_149761521762302662', 'employee__403']
            ),
            (
                'Hola quiero completar una query. Tengo el supportCategory_1497611711762302662 y la empresa company__ZLMCEWBY6',
                ['company__ZLMCEWBY6', 'supportCategory_1497611711762302662', 'typeIncident__1', 'incidentOrigin__2',
                 'supportGroup_14976631762302662', 'employee__366']
            ),
            (
                'Hola quiero completar una query. Tengo el supportCategory_149764571762302662 y la empresa company__Y1XHYEPUS',
                ['company__Y1XHYEPUS', 'supportCategory_149764571762302662', 'typeIncident__2', 'incidentOrigin__2',
                 'supportGroup_14976631762302662', 'employee__266']
            ),
            (
                'Hola quiero completar una query. Tengo el supportCategory_1497621981762302663 y la empresa company__TLL5K8PC5',
                ['company__TLL5K8PC5', 'supportCategory_1497621981762302663', 'typeIncident__1', 'incidentOrigin__2',
                 'supportGroup_14976631762302662', 'employee__366']
            )
        ]

    def test_procesar_queries(self):
        """
        Itera sobre todos los casos de prueba simulando el procesamiento de GraphRAG.
        Debes ajustar la lógica interna de este método para que llame a tu función
        procesadora y verifique la salida.
        """
        for i, (input_texto, output_esperado) in enumerate(self.casos_de_prueba):
            with self.subTest(input_texto=input_texto):
                result = procesar_query(input_texto)
                self.assertEqual(
                    result, output_esperado,
                    msg=f"Caso {i} fallido.\nQuery: {input_texto}\nEsperado: {output_esperado}\nObtenido: {result}"
                )
                
                # ==============================================================
                # AQUI DEBES INCLUIR LA LLAMADA A TU LÓGICA DE PROCESAMIENTO
                # Ejemplo: resultado = procesar_query(input_texto)
                # self.assertEqual(resultado, output_esperado)
                # ==============================================================
               


def ejecutar_tests_en_fichero():
    archivo_salida = "resultados_tests.txt"
    print(f"\nEjecutando pruebas unitarias. La salida se guardará en '{archivo_salida}'...")
    
    with open(archivo_salida, "w", encoding="utf-8") as f:
        runner = unittest.TextTestRunner(stream=f, verbosity=2)
        suite = unittest.TestLoader().loadTestsFromTestCase(TestQueryProcessor)
        result = runner.run(suite)
        
    print("Pruebas finalizadas. Revisa el archivo generado.")
    sys.exit(0 if result.wasSuccessful() else 1)


# ============================================
# BLOQUE PRINCIPAL (BUCLE INTERACTIVO)
# ============================================

if __name__ == '__main__':
    # Validar si el script se ha ejecutado con el flag de testing
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        ejecutar_tests_en_fichero()

    #print("\n" + "=" * 40)
    #print(" SISTEMA GraphRAG + Ollama INICIADO")
    #print("====================================")
    #print("Escribe 'q' para salir")
#
    ## Inicialización de variables de estado
    #convo_length = 2
    #unique_conv_id = str(uuid4())
    #prev_conv = ""
    #filename = unique_conv_id + "_log.txt"
    #log_file_path = os.path.join(config.LOGS_DIR, filename)
#
    #save_file(log_file_path, prev_conv)
    #a = ""
    #primera = True
    #mis_datos = [None, None, None, None, None, None]
#
    #while True:
#
    #    if None not in mis_datos and 'None' not in mis_datos:
    #        print('\nGraphRAG: query acabada. La query completada es:')
    #        print(mis_datos)
    #        break
#
    #    if primera:
    #        a = input('\nUSER: ')
#
    #    primera = False
#
    #    if a.lower() == "q":
    #        print("\nFinalizando conversación...")
    #        break
#
    #    timestamp = time()
    #    timestring = timestamp_to_datetime(timestamp)
    #    message = f"USER: {timestring} - {a}"
#
    #    # ----------------------------------------
    #    # EXTRACCIÓN DE DATOS INICIALES
    #    # ----------------------------------------
    #    if mis_datos[0] is None:
    #        cliente = extraer_cliente(a)
    #        if cliente: print(f"Cliente extraído: {cliente}")
    #        mis_datos[0] = cliente
#
    #    if mis_datos[1] is None:
    #        support_cat = extraer_support_category(a)
    #        mis_datos[1] = support_cat
#
    #    # ----------------------------------------
    #    # VERIFICACIÓN DE FIN DE BÚSQUEDA
    #    # ----------------------------------------
#
    #    try:
    #        cat_buscar = mis_datos.index(None)
    #    except ValueError:
    #        cat_buscar = mis_datos.index('None')
#
    #    # ----------------------------------------
    #    # CONSULTA AL GRAFO RDF
    #    # ----------------------------------------
    #    graph_data = buscar_frecuentes_por_opcion(graph, mis_datos, cat_buscar)
#
    #    if not graph_data:
    #        graph_data = inferir_valor_adecuado(graph, mis_datos, cat_buscar)
#
    #    # ----------------------------------------
    #    # LÓGICA DE REINTENTOS Y LLM
    #    # ----------------------------------------
    #    max_a_probar = len(graph_data) if graph_data else 0
    #    siguiente_a_probar = 1
    #    retry = True
#
    #    while retry:
    #        retry = False
    #        prev_conv = open_file(log_file_path)
#
    #        if not graph_data:
    #            data = "No se encontraron datos. Seguramente sea un error por parte del usuario. Pregunta si se ha introducido bien el grupo."
    #        else:
    #            mi_opcion = graph_data[0]
    #            if retry and siguiente_a_probar < max_a_probar:
    #                mi_opcion = graph_data[siguiente_a_probar]
    #                siguiente_a_probar += 1
#
    #            data = (
    #                f"El campo a rellenar es "
    #                f"{config.DICCIONARIO_PREFIJOS[cat_buscar]}"
    #                f" y estas son las opciones:\n\nrepcon:"
    #                f"{config.DICCIONARIO_PREFIJOS[cat_buscar]}"
    #                f" repcon:{mi_opcion}"
    #            )
#
    #        # Preparar prompt
    #        reglas = formatear_para_llm(
    #            './textos/reglas_incidentes.json',
    #            tipo_cond=config.DICCIONARIO_PREDICADOS[cat_buscar]
    #        )
#
    #        prompt_base = open_file(config.CONTEXTO_FILE_PATH)
    #        mensajeinstruc = "Se espera que extraigas el campo " + config.DICCIONARIO_PREFIJOS[cat_buscar]
    #        datos_existentes = formatear_datos_existentes_LLM(graph_data)
#
    #        prompt = (
    #            prompt_base
    #            .replace('<<DATOS>>', data)
    #            .replace('<<CONVERSACIÓN>>', datos_existentes)
    #            .replace('<<MENSAJE>>', mensajeinstruc)
    #            .replace('<<REGLAS>>', "\n".join(reglas))
    #        )
#
    #        # Ejecutar LLM en paralelo usando asyncio (proveniente del Script 1)
    #        outputs = asyncio.run(text_completion_batch([prompt, prompt, prompt]))
#
    #        # Procesar y limpiar respuesta
    #        nuevo = []
    #        for x in outputs:
    #            limpio = extraer_respuesta_limpia_llm(arreglar_lista_llm(x)).replace("repcon:", "")
    #            nuevo.append(limpio)
#
    #        output = elemento_mas_comun(nuevo)
    #        mis_datos = merge_lista_y_parametro(mis_datos, output)
#
    #        print("\n--- Estado actualizado de mis_datos ---")
    #        print(mis_datos)
#
    #        if output == "ERROR":
    #            retry = True
#
    #    # ----------------------------------------
    #    # GUARDAR LOG Y RESPONDER
    #    # ----------------------------------------
    #    timestamp = time()
    #    timestring = timestamp_to_datetime(timestamp)
    #    messageBot = f"[Asistente]: {timestring} - {output}"
#
    #    print(f"\n[Asistente]: {output}")
#
    #    save_file(
    #        log_file_path,
    #        prev_conv + "\n" + message + "\n" + messageBot
    #    )