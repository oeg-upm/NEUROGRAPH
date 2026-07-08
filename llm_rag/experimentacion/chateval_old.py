import os
from openai import OpenAI
import json
import re
from time import time,sleep
from uuid import uuid4
import datetime
from searchInGraph import buscar_frecuentes_por_opcion, inferir_valor_adecuado
from formatHelper import extraer_support_category, extraer_cliente, formatear_para_llm, arreglar_lista_llm, merge_listas_or, limpiar_lista
from rdflib import Graph
import config

#from c_clause import QAHandler, Loader
#from clause import Options



graph = Graph()

graph.parse(config.TTL_FILE_PATH, format=config.TTL_FORMAT)


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


def text_completion(prompt, engine=config.MI_MODELO):
    max_retry = 5
    retry = 0


    
    while True:
        try:
            response = config.client.chat.completions.create(
                                messages=[
                                    {
                                        "role": "user",
                                        "content": prompt,
                                    }
                                ],
                                model=engine,
                            #stream=True #clave al parecer
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
            sleep(config.RETRY_DELAY_SECONDS)



if __name__ == '__main__':
    convo_length = 2 # se puede cambiar
    
    unique_conv_id = str(uuid4())
    prev_conv = ""
    filename = unique_conv_id+'_log.txt'
    log_file_path = os.path.join(config.LOGS_DIR, filename)
    save_file(log_file_path, prev_conv)

    primera = True
    buscar = False
    mi_opcion = None
    cat_buscar = 0
    graph_data = []
    mis_datos = [None, None, None, None, None, None]
    

    
    while True:

        if primera:
            a = input('\n\nUSER: ')

        primera = False

        
        if (a == "q"):
            break
        
        

        
        
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
        
        
        
        


        if None not in mis_datos and 'None' not in mis_datos:
            print('\nGraphRAG: query acabada. La query es '+ str(mis_datos))
            break

        try:
            cat_buscar = mis_datos.index(None)
        except ValueError:
            cat_buscar = mis_datos.index('None')
        graph_data = buscar_frecuentes_por_opcion(graph, mis_datos, cat_buscar)

        if graph_data == None or graph_data == []:
            graph_data = inferir_valor_adecuado(graph, mis_datos, cat_buscar)


        mi_opcion = graph_data[0]
        max_a_probar = len(graph_data)
        # bucle repetir error
        siguiente_a_probar = 1
        retry = True
        while retry:
            retry = False



            prev_conv = open_file(log_file_path)



            if graph_data == None:
                data = "No se encontraron datos. Seguramente sea un error por parte del usuario. Pregunta si se ha introducido bien el grupo"
            else:

                if retry and siguiente_a_probar < max_a_probar:
                    mi_opcion = graph_data[siguiente_a_probar]
                    siguiente_a_probar = siguiente_a_probar + 1  

                data = "El campo a rellenar es "+config.DICCIONARIO_PREDICADOS[cat_buscar] + " y estas son las opciones\n"+ mi_opcion




            #print("config.DICCIONARIO_PREDICADOS[cat_buscar]")

            reglas = formatear_para_llm('./textos/reglas_incidentes.json', tipo_cond=config.DICCIONARIO_PREDICADOS[cat_buscar])


            #No está conectado el LLM, pero descomentando las siguientes líneas se usaría

            prompt = open_file(config.CONTEXTO_FILE_PATH).replace('<<DATOS>>', data).replace('<<CONVERSACIÓN>>', prev_conv).replace('<<MENSAJE>>', a).replace('<<REGLAS>>', " \n".join(reglas))

            output = text_completion(prompt) #aquí se genera
            #esta es la parte clave
            print(output)

            #TODO sistema OR y pre formateo
            output = arreglar_lista_llm(output)



            mis_datos_nuevos = limpiar_lista(json.loads(output)) #quizasaa
            print("Del llm")
            print(mis_datos_nuevos)
            mis_datos = merge_listas_or(mis_datos, mis_datos_nuevos)
            print("Los 'buenos'")
            print(mis_datos)
            if mis_datos[cat_buscar] == "ERROR":
                retry = True


        # TODO hacer "OR" con los datos

        timestamp = time()
        timestring = timestamp_to_datetime(timestamp)
        #
        messageBot = '%s: %s - %s' % ('[Asistente]', timestring, output)
        #
        print('\n\[Asistente]: %s' % output)
        
        # Y aquí se guardaría los datos de la conversación 
        
        save_file(log_file_path, prev_conv+"\n"+message+"\n"+messageBot)

        

        