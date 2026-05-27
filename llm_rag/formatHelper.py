import re
import json

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

    patron = r"company__[A-Z0-9]+"
    
    coincidencia = re.search(patron, texto)
    
    if coincidencia:
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
        print(texto)
        #print("halo")

    return textos_generados


def arreglar_lista_llm(texto: str) -> str:
    """
    Añade comillas a elementos no quoted dentro de una lista estilo JSON.
    Respeta null, true, false y elementos ya entrecomillados.
    """

    patron = r'(?<=\[|,)\s*([A-Za-z0-9_]+(?:__[A-Za-z0-9_]+)?)\s*(?=,|\])'

    def reemplazo(match):
        valor = match.group(1)

        # No tocar valores especiales JSON
        if valor in {"null", "true", "false"}:
            return match.group(0)

        return f' "{valor}"'

    return re.sub(patron, reemplazo, texto)


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
def merge_listas_or(lista1, lista2):
    """
    Combina dos listas y las ordena según un esquema fijo.
    - Busca a qué prefijo pertenece cada valor.
    - Da prioridad a los valores de lista1 sobre los de lista2.
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
        if valor is None or valor == "None":
            return None
        for prefijo in esquema:
            if valor.find(prefijo + "_") != -1:
                return prefijo
        return None

    # 1. Cargamos primero la lista2 (tiene menor prioridad)
    for item in lista2:
        prefijo = obtener_prefijo(item)
        if prefijo:
            valores_mapeados[prefijo] = item

    # 2. Cargamos la lista1 (tiene mayor prioridad, sobrescribirá a lista2 si hay colisión)
    for item in lista1:
        prefijo = obtener_prefijo(item)
        if prefijo:
            valores_mapeados[prefijo] = item

    # 3. Construimos la lista final recorriendo el esquema en orden
    # Si no encontramos el valor para un prefijo en ninguna lista, ponemos None
    resultado = [valores_mapeados.get(prefijo, None) for prefijo in esquema]

    return resultado

def limpiar_lista(lista_sucia):
    prefijos_validos = [
        "company",
        "supportCategory",
        "typeIncident",
        "incidentOrigin",
        "supportGroup",
        "employee"
    ]

    lista_limpia = []

    for item in lista_sucia:
        # --- NUEVA REGLA ---
        # Si el elemento es el objeto None o el string "None",
        # lo guardamos tal cual y pasamos al siguiente.
        if item is None or item == "None":
            lista_limpia.append(item)
            continue

        # Para el resto de elementos, aplicamos la lógica anterior
        for prefijo in prefijos_validos:
            indice = item.find(prefijo + "_")

            if indice != -1:
                lista_limpia.append(item[indice:])
                break

    return lista_limpia

