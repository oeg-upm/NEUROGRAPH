import os
from openai import OpenAI
import json
import re
from time import time,sleep
from uuid import uuid4
import datetime
from searchInGraph import buscar_frecuentes_por_opcion, inferir_valor_adecuado
from formatHelper import extraer_support_category, extraer_cliente, extraer_parametro_gen
from rdflib import Graph


graph = Graph()

graph.parse("filtrado.ttl", format="turtle")




mi_model = "mistral:latest"

def open_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as infile:
        return infile.read()


def save_file(filepath, content):
    #s.makedirs(os.path.dirname(filepath), exist_ok=True) no cambies esto, revisa el directorio antes
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


client = OpenAI(
    # This is the default and can be omitted
    base_url="http://localhost:11434/v1",
    api_key="ollama"
)


def text_completion(prompt, engine=mi_model):
    max_retry = 5
    retry = 0


    
    while True:
        try:
            response = client.chat.completions.create(
                                messages=[
                                    {
                                        "role": "user",
                                        "content": prompt,
                                    }
                                ],
                                model=engine,
                            )
            
            
            text = response.choices[0].message.content
            #text = response['choices'][0]['text'].strip()
            #print("\n"+text+"\n")
            text = re.sub('[\r\n]+', '\n', text)
            text = re.sub('[\t ]+', ' ', text)
            #filename = '%s_log.txt' % time()
            #if not os.path.exists('./textos/logs'):
            #    os.makedirs('./textos/logs')
            #save_file('./textos/logs/%s' % filename, prompt + '\n\n==========\n\n' + text)
            return text
        except Exception as oops:
            retry += 1
            if retry >= max_retry:
                return "Model error: %s" % oops
            print('Error communicating with model:', oops)
            sleep(1)



if __name__ == '__main__':
    convo_length = 2 # se puede cambiar
    
    unique_conv_id = str(uuid4())
    prev_conv = ""
    filename = unique_conv_id+'_log.txt' 
    
    #Por si se quiere mantener un registro de las conversaciones
    #save_file('./textos/logs/%s' % filename, prev_conv)

    primera = True
    buscar = False
    mi_opcion = None
    cat_buscar = 0
    graph_data = []
    mis_datos = [None, None, None, None, None, None]
    
    diccionario_predicados = {
        0: "int_hasCustomer",
        1: "hasSupportCategory",  # en teoría es hasUser pero no hay de eso, al menos en filtrado.ttl. Lo cambio a hasSupportCategory
        2: "hasTypeInc",
        3: "incident_hasOrigin",
        4: "hasSupportGroup",
        5: "hasTechnician"
        }
    
    diccionario_prefijos = {
    0: "company",         # Para int_hasCustomer
    1: "supportCategory", # Para hasSupportCategory
    2: "typeIncident",    # Para hasTypeInc
    3: "incidentOrigin",  # Para incident_hasOrigin
    4: "supportGroup",    # Para hasSupportGroup
    5: "employee"         # Para hasTechnician (que usa el prefijo employee)
}
    
    while True:

        if primera:
            a = input('\n\nUSER: ')
        
        primera = False
        buscar = True
        
        
        if (a == "q"):
            #save_json('./nexo/%s.json' % unique_id, metadata)
            break
        
        
        
        
        
        opciones_si = {"y", "s", "yes", "si"}
        opciones_no = {"n", "no", "skip"}

        confirmado = False

        if graph_data:
            # 1. Mostrar todas las opciones a la vez (estilo imagen)
            print(f"\n[Asistente] ¿Cuál es el valor para {diccionario_prefijos[cat_buscar]}? (Responde con el número o 'si' si es la primera opción)")
            print("Opciones recomendadas (GraphRAG):")
            
            for i, opcion in enumerate(graph_data):
                print(f" {i+1}. {opcion}")
            
            
            print(f"(responde con número, s/si = #1, n/no = inferencia, q = salir)")
            a = input('\nUSER: ').strip().lower()

            
            if a == 'q':
                pass 
            
            # CASO A: El usuario elige por número (1, 2, 3...)
            elif a.isdigit():
                idx = int(a) - 1
                if 0 <= idx < len(graph_data):
                    mis_datos[cat_buscar] = graph_data[idx]
                    confirmado = True
            
            # CASO B: El usuario dice "Sí" (se asume la opción #1 por defecto)
            elif a in opciones_si:
                mis_datos[cat_buscar] = graph_data[0]
                confirmado = True

            # CASO C: El usuario dice "No" explícitamente
            elif a in opciones_no:
                print("\nGraphRAG: Entendido. Buscando alternativas...")
                graph_data = inferir_valor_adecuado(graph, mis_datos, cat_buscar)
                buscar = False

       
        
        
        
        
        
        
        # Esto no tiene funcionalidad por el momento pero servirá si se quiere mantener un registro de las peticiones del usuario
        timestamp = time()
        timestring = timestamp_to_datetime(timestamp)
        message = '%s: %s - %s' % ('USER', timestring, a)
       
       
        
        '''
        0- Int_hasCustomer - Esta priori nos las dan
        1- hasUser - esto no existe? # en teoría es hasUser pero no hay de eso, al menos en filtrado.ttl. Lo cambio a hasSupportCategory
        2- hasTypeInc
        3- incident_hasOrigin
        4- hasSupportGroup
        5- hasTechnician
        '''
        
        
        
                
         # TODO esto es algo burdo, mejorar mas tarde
        
        if mis_datos[0] == None:
            cliente = extraer_cliente(a)
            mis_datos[0] = cliente
            
        if mis_datos[1] == None:
            support_cat = extraer_support_category(a)
            mis_datos[1] = support_cat
        
        
        
        
        if buscar:
            
            if None not in mis_datos:
                print('\nGraphRAG: query acabada. La query es '+ str(mis_datos))
                break
            cat_buscar = mis_datos.index(None)
            graph_data = buscar_frecuentes_por_opcion(graph, mis_datos, cat_buscar)

            
            if graph_data == None or graph_data == []:

                graph_data = inferir_valor_adecuado(graph, mis_datos, cat_buscar)

        
        
            mi_opcion = graph_data[0]
        

        if not os.path.exists('./textos/logs'):
            os.makedirs('./textos/logs')
        

        
        prev_conv = open_file('./textos/logs/%s' % filename)
        
        

        if graph_data == None:
            data = "No se encontraron datos. Seguramente sea un error por parte del usuario. Pregunta si se ha introducido bien el grupo"
        else:
            data = "El campo a rellenar es "+diccionario_predicados[cat_buscar] + " y estas son las opciones\n"+ mi_opcion

        #No está conectado el LLM, pero así se usaría 
        prompt = open_file('./textos/contexto.txt').replace('<<DATOS>>', data).replace('<<CONVERSACIÓN>>', prev_conv).replace('<<MENSAJE>>', a)



        #output = text_completion(prompt) #aquí se genera
        #timestamp = time()
        #timestring = timestamp_to_datetime(timestamp)
        #
        #messageBot = '%s: %s - %s' % ('[Asistente]', timestring, output)
        #
        #print('\n\[Asistente]: %s' % output) 
        
        # Y aquí se guardaría los datos de la conversación 
        
        #save_file('./textos/logs/%s' % filename, prev_conv+"\n"+message+"\n"+messageBot)
        #timestamp = time()
        #timestring = timestamp_to_datetime(timestamp)
        

        