import re
import json
import config

def extraer_parametro_gen(texto, prefijo): # versión generalizada, no se usa por el momento
    """
    Extrae el parámetro basándose solo en el prefijo, detectando 
    automáticamente si tiene uno (_) o dos (__) guiones bajos.
    """

    patron = rf"{prefijo}_+[A-Z0-9]+"
    
    coincidencia = re.search(patron, texto, re.IGNORECASE)
    
    return coincidencia.group(0) if coincidencia else None




def extraer_support_category(texto): # Detecta el ID interno, no los "reales". Se necesita el diccionario traductor
    """
    Busca y extrae el identificador de supportCategory de un texto dado.
    """
    patron = r"supportCategory_\d+"
    
    coincidencia = re.search(patron, texto)
    
    if coincidencia:
        return coincidencia.group(0)
    else:
        return None
    


def extraer_cliente(texto): # Detecta el nombre raro interno, no los "reales". Se necesita el diccionario traductor
    """
    Busca y extrae el identificador de la compañía (company__) de un texto dado.
    """

    patron = r"company__[A-Z0-9]+|\bss\b"
    
    coincidencia = re.search(patron, texto)
    
    if coincidencia:
        #print(coincidencia.group(0))
        return coincidencia.group(0)
    else:
        return None


def formatear_para_llm(ruta_fichero, tipo_cond):
    # Intentamos abrir y leer el archivo JSON
    try:
        with open(ruta_fichero, 'r', encoding='utf-8') as f:
            reglas = json.load(f)
    except FileNotFoundError:
        print(f"Error: No se encontró el fichero '{ruta_fichero}'.")
        return
    except json.JSONDecodeError:
        print("Error: El fichero no contiene un JSON válido.")
        return

    textos_generados = []

    for regla in reglas:
        then_consecuencias = regla.get("then", {})
        str_then = " y ".join(str(v) for v in then_consecuencias.values())


        #print(tipo_cond)
        #print(then_consecuencias.keys())
        if tipo_cond not in list(then_consecuencias.keys()):
            #print("me triggeree")
            continue

        tipo_regla = regla.get("ruleType")
        if_condiciones = regla.get("if", {})

        # Extraemos solo los valores para armar la frase (ej: incidentOrigin__1)
        # Si hay más de una condición, las unimos con " y "
        str_if = " y ".join(str(v) for v in if_condiciones.values())

        # Formateamos según el tipo de regla
        if tipo_regla == "noValid":
            frase = f"Regla noValid. Si hay {str_if} NO ES POSIBLE {str_then}."
            if frase not in textos_generados:
                textos_generados.append(frase)

        elif tipo_regla == "df":
            frase = f"Regla df. Si hay {str_if} EL VALOR POR DEFECTO ES {str_then}."
            textos_generados.append(frase)

        else:
            # Por si existieran otros tipos de reglas en el futuro
            frase = f"Regla {tipo_regla}. Si hay {str_if} ENTONCES {str_then}."
            textos_generados.append(frase)

    # Imprimimos los resultados por consola
    for texto in textos_generados:
        #print(texto)
        #print("halo")
        pass

    return textos_generados




def aplicar_reglas(ruta_fichero, mis_datos, cat_buscar, graph_data, contadores):
    """
    Evalúa las reglas del JSON contra el estado actual de la conversación (mis_datos).
    Modifica graph_data en función de las reglas 'noValid' y 'df'.
    """
    if not graph_data:
        return graph_data

    # 1. Cargar el JSON de reglas
    try:
        with open(ruta_fichero, 'r', encoding='utf-8') as f:
            reglas = json.load(f)
    except FileNotFoundError:
        print(f"Error: No se encontró el fichero '{ruta_fichero}'.")
        return graph_data
    except json.JSONDecodeError:
        print("Error: El fichero no contiene un JSON válido.")
        return graph_data

    # Extraemos el nombre del predicado que estamos intentando rellenar
    # Asume que config.DICCIONARIO_PREDICADOS es accesible globalmente
    predicado_actual = config.DICCIONARIO_PREDICADOS[cat_buscar]

    for regla in reglas:
        if_condiciones = regla.get("if", {})
        then_consecuencias = regla.get("then", {})
        tipo_regla = regla.get("ruleType")

        # 2. Verificar si las condiciones del "if" se cumplen en el estado actual
        # Buscamos si los valores requeridos por la regla ya están guardados en mis_datos
        condiciones_cumplidas = all(valor in mis_datos for valor in if_condiciones.values())

        if condiciones_cumplidas:
            # 3. Comprobar si la regla afecta a la categoría actual que estamos buscando
            if predicado_actual in then_consecuencias:
                valor_regla = then_consecuencias[predicado_actual]

                # REGLA: noValid (Invalida la opción actual)
                if tipo_regla == "noValid":
                    # Si el valor propuesto por GraphRAG es el que la regla prohíbe
                    if graph_data[0] == valor_regla:
                        print(f"\n[Regla Aplicada - noValid] '{valor_regla}' no es válido para '{predicado_actual}'.")
                        print("[Regla Aplicada] Descartando opción principal. Saltando a la siguiente opción.")
                        
                        # Eliminamos la opción prohibida. El segundo valor sube a la posición [0]
                        graph_data.pop(0)
                        contadores["vecesnv"] += 1
                        if not graph_data:
                            print("[Advertencia] Nos hemos quedado sin opciones válidas en graph_data.")
                            break 

                # REGLA: df (Valor por defecto)
                elif tipo_regla == "df":
                    print(f"\n[Regla Aplicada - df] Forzando el valor por defecto: '{valor_regla}'.")
                    
                    # Si el valor ya estaba en la lista, lo sacamos para no duplicar
                    if valor_regla in graph_data:
                        graph_data.remove(valor_regla)
                    
                    # Insertamos el valor por defecto en la posición principal [0]
                    contadores["vecesdf"] += 1
                    graph_data.insert(0, valor_regla)

    return graph_data



def formatear_datos_existentes_LLM(datos):

    lineas_validas = []
    
    # Recorremos el array usando enumerate para obtener el valor y su índice (posición)
    for indice, valor in enumerate(datos):
        # Si el valor es None o está vacío, lo ignoramos
        if valor is None or valor == "":
            continue
            
        # Obtenemos el predicado correspondiente a la posición
        predicado = config.DICCIONARIO_PREDICADOS.get(indice)
        
        if predicado:
            # Construimos la línea con el formato 'repcon:predicado repcon:valor'
            linea = f"repcon:{predicado} repcon:{valor}"
            lineas_validas.append(linea)
    
    # Si no hay datos válidos, devolvemos un string vacío
    if not lineas_validas:
        return ""
        
    # Unimos las líneas intermedias con " ;" y cerramos la última con "."
    # Siguiendo tu ejemplo, si quieres que terminen estrictamente en ';' puedes cambiar el '.' por ';'
    resultado = " ;\n".join(lineas_validas) + " ;"
    
    return resultado

# --- Ejemplo de uso ---
#array_ejemplo = ['company__5B5JVGSPI', 'supportCategory_149769071762302662', None, None, None, None]

#resultado_formateado = formatear_datos_existentes_LLM(array_ejemplo)
#print(resultado_formateado) 


def arreglar_lista_llm(texto: str) -> str:
    """
    Limpia y normaliza la salida de GraphRAG según las nuevas instrucciones estrictas.
    Devuelve '"ERROR"' o el formato 'repcon:valor' eliminando espacios espurios
    o comillas mal puestas.
    """
    # 1. Limpieza inicial de espacios y saltos de línea
    texto_limpio = texto.strip()
    
    # 2. Si la salida es el caso de error, aseguramos que devuelva exactamente "ERROR"
    if "ERROR" in texto_limpio:
        return '"ERROR"'
        
    # 3. Si viene con el prefijo correcto, lo normalizamos eliminando comillas extras 
    # (por si el LLM se equivocó e incluyó comillas por inercia)
    if "repcon:" in texto_limpio:
        # Extrae solo el contenido alfanumérico y guiones bajos después de repcon:
        match = re.search(r'repcon:([A-Za-z0-9_]+)', texto_limpio)
        if match:
            return f"repcon:{match.group(1)}"
            
    # 4. Caso de contingencia: Si el LLM devolvió solo el valor sin el prefijo 'repcon:'
    # (ej: 'typeIncident__4' o '"typeIncident__4"')
    valor_plano = texto_limpio.replace('"', '').replace("'", "")
    if any(prefijo in valor_plano for prefijo in ["company__", "supportCategory", "typeIncident", "incidentOrigin", "supportGroup", "employee"]):
        return f"repcon:{valor_plano}"
        
    # Si no cumple ningún patrón válido, por seguridad mapea a ERROR
    return '"ERROR"'

# --- Ejemplos de uso basados en el nuevo formato ---
#print(arreglar_lista_llm('  repcon:typeIncident__4  '))  # Devuelve: repcon:typeIncident__4
#print(arreglar_lista_llm('GraphRAG: "ERROR"'))          # Devuelve: "ERROR"
#print(arreglar_lista_llm('"repcon:supportGroup_123"'))  # Devuelve: repcon:supportGroup_123
#print(arreglar_lista_llm('company__UPFP8CUEG'))          # Devuelve: repcon:company__UPFP8CUEG (Autocorrige prefijo)


#def merge_listas_or(lista1, lista2):
#    """
#    Combina dos listas usando lógica tipo OR:
#    - Se queda con el valor de lista1 si NO es None ni 'None'
#    - Si lista1 tiene None o 'None', usa el valor de lista2
#    """
#
#    if len(lista1) != len(lista2):
#        raise ValueError("Las listas deben tener la misma longitud")
#
#    return [
#        v1 if v1 not in (None, 'None') else v2
#        for v1, v2 in zip(lista1, lista2)
#    ]
#def merge_listas_or(lista1, lista2):
#    """
#    Combina dos listas y las ordena según un esquema fijo.
#    - Busca a qué prefijo pertenece cada valor.
#    - Da prioridad a los valores de lista1 sobre los de lista2.
#    - Devuelve una lista de exactamente 6 elementos en el orden correcto.
#    """
#    # El esquema define el orden exacto de nuestra lista final
#    esquema = [
#        "company",
#        "supportCategory",
#        "typeIncident",
#        "incidentOrigin",
#        "supportGroup",
#        "employee"
#    ]
#
#    # Usaremos un diccionario para guardar el valor correspondiente a cada prefijo
#    valores_mapeados = {}
#
#    # Función auxiliar para saber a qué prefijo pertenece un texto
#    def obtener_prefijo(valor):
#        if valor is None or valor == "None":
#            return None
#        if valor == "ss":
#            return "company"
#        for prefijo in esquema:
#            if valor.find(prefijo + "_") != -1:
#                return prefijo
#        return None
#
#    # 1. Cargamos primero la lista2 (tiene menor prioridad)
#    for item in lista2:
#        prefijo = obtener_prefijo(item)
#        if prefijo:
#            valores_mapeados[prefijo] = item
#
#    # 2. Cargamos la lista1 (tiene mayor prioridad, sobrescribirá a lista2 si hay colisión)
#    for item in lista1:
#        prefijo = obtener_prefijo(item)
#        if prefijo:
#            valores_mapeados[prefijo] = item
#
#    # 3. Construimos la lista final recorriendo el esquema en orden
#    # Si no encontramos el valor para un prefijo en ninguna lista, ponemos None
#    resultado = [valores_mapeados.get(prefijo, None) for prefijo in esquema]
#    print("Wey")
#    print(lista1)
#    print("Weeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeey")
#    print(lista1[0])
#    if lista1[0]=="ss":
#        resultado[0]= "ss"
#        print("BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB")
#    print("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
#
#    print(resultado)
#    
#    return resultado


def merge_lista_y_parametro(lista_base, nuevo_valor):
    """
    Combina una lista y un nuevo parámetro, ordenándolos según un esquema fijo.
    - Busca a qué prefijo pertenece cada valor.
    - Da prioridad al 'nuevo_valor' sobre los elementos de 'lista_base'.
    - Devuelve una lista de exactamente 6 elementos en el orden correcto.
    """
    # El esquema define el orden exacto de nuestra lista final
    esquema = [
        "company",
        "supportCategory",
        "typeIncident",
        "incidentOrigin",
        "supportGroup",
        "employee"
    ]

    # Usaremos un diccionario para guardar el valor correspondiente a cada prefijo
    valores_mapeados = {}

    # Función auxiliar para saber a qué prefijo pertenece un texto
    def obtener_prefijo(valor):
        if valor is None or str(valor) == "None":
            return None
        for prefijo in esquema:
            if str(valor).find(prefijo + "_") != -1:
                return prefijo
        return None

    # 1. Cargamos primero la lista base (tiene menor prioridad)
    if lista_base:
        for item in lista_base:
            prefijo = obtener_prefijo(item)
            if prefijo:
                valores_mapeados[prefijo] = item

    # 2. Cargamos el nuevo parámetro (mayor prioridad, sobrescribe si hay colisión)
    prefijo_nuevo = obtener_prefijo(nuevo_valor)
    if prefijo_nuevo:
        valores_mapeados[prefijo_nuevo] = nuevo_valor

    # 3. Construimos la lista final recorriendo el esquema en orden
    # Si no encontramos el valor para un prefijo, ponemos None
    resultado = [valores_mapeados.get(prefijo, None) for prefijo in esquema]
    
    
    if lista_base[0]=="ss":
        resultado[0]= "ss"
    
    return resultado





def extraer_respuesta_limpia_llm(texto: str) -> str:
    """
    Detecta y extrae únicamente la respuesta final de GraphRAG,
    ignorando explicaciones, introducciones o repeticiones extras.
    """
    # 1. Primera línea de defensa: Buscar la etiqueta "GraphRAG:"
    # Captura todo lo que esté después de GraphRAG: hasta el final de esa línea
    match_etiqueta = re.search(r'GraphRAG:\s*([^\n]+)', texto, re.IGNORECASE)
    
    if match_etiqueta:
        resultado = match_etiqueta.group(1).strip()
        # Si el resultado es el error, lo devolvemos con comillas estructuradas
        if "ERROR" in resultado:
            return '"ERROR"'
        return resultado

    # 2. Segunda línea de defensa (Contingencia): Si el LLM olvidó poner "GraphRAG:"
    # pero el texto contiene un "ERROR" definitivo
    if "ERROR" in texto:
        return '"ERROR"'

    # 3. Tercera línea de defensa: Buscar cualquier patrón 'repcon:valor' en el texto
    # si es que no se encontró la etiqueta explícita
    patrones_validos = re.findall(r'repcon:(?:company__|supportCategory|typeIncident|incidentOrigin|supportGroup|employee)[A-Za-z0-9_]*', texto)
    if patrones_validos:
        # Devolvemos el último encontrado (suele ser el de la respuesta o el repetido al final)
        return patrones_validos[-1]

    # Si de verdad no hay nada procesable, devolvemos ERROR por seguridad
    return '"ERROR"'