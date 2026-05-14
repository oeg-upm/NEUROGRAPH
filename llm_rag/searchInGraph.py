from collections import Counter
from rdflib import Graph, URIRef, Namespace

g = Graph()

g.parse("filtrado.ttl", format="turtle")




'''
0- Int_hasCustomer - Esta priori nos las dan
1- hasUser - esto no existe? # en teoría es hasUser pero no hay de eso, al menos en filtrado.ttl. Lo cambio a hasSupportCategory
2- hasTypeInc
3- incident_hasOrigin
4- hasSupportGroup
5- hasTechnician
'''



def buscar_frecuentes_por_opcion(g, filtros_array, opcion, prefix_uri="http://repcon.org/schema#"):
    """
    Filtra incidentes basados en un array de 6 condiciones fijas y devuelve 
    los 3 valores más comunes del campo elegido en 'opcion'.
    """
    
    # 0. Mapeo de índices a nombres de predicados (según tu nueva estructura)
    diccionario_predicados = {
        0: "int_hasCustomer",
        1: "hasSupportCategory",  # en teoría es hasUser pero no hay de eso, al menos en filtrado.ttl. Lo cambio a hasSupportCategory
        2: "hasTypeInc",
        3: "incident_hasOrigin",
        4: "hasSupportGroup",
        5: "hasTechnician"
    }

    nombre_predicado_objetivo = diccionario_predicados.get(opcion)
    if not nombre_predicado_objetivo:
        print(f"Error: La opción {opcion} no es válida.")
        return []


    triple_patterns = ""
    for i, valor in enumerate(filtros_array):
        if valor is not None:
            predicado_filtro = diccionario_predicados[i]
            # Añadimos la restricción al WHERE: ?incident <predicado> <valor> .
            triple_patterns += f"?incident <{prefix_uri}{predicado_filtro}> <{prefix_uri}{valor}> .\n"

    uri_predicado_objetivo = f"<{prefix_uri}{nombre_predicado_objetivo}>"

    # 4. Consulta SPARQL
    # Buscamos incidentes que cumplan todos los patrones de triple_patterns
    # y extraemos su 'targetValue' para el predicado objetivo.
    query = f"""
    SELECT ?targetValue (COUNT(?targetValue) AS ?total)
    WHERE {{
        {triple_patterns}
        ?incident {uri_predicado_objetivo} ?targetValue .
    }}
    GROUP BY ?targetValue
    ORDER BY DESC(?total)
    LIMIT 3
    """

    
    resultados = g.query(query)

    top_resultados = []
    for row in resultados:
        val_uri = str(row.targetValue)
        
        # Extraer ID (shorten)
        if "#" in val_uri:
            id_limpio = val_uri.split("#")[-1]
        elif "/" in val_uri:
            id_limpio = val_uri.rsplit("/", 1)[-1]
        else:
            id_limpio = val_uri

        top_resultados.append(id_limpio)

    return top_resultados



'''
1- Int_hasCustomer - Esta priori nos las dan
2- hasUser - 
3- hasTypeInc
4- incident_hasOrigin
5- hasSupportGroup
6- hasTechnician
'''

def inferir_valor_adecuado(g, filtros_array, opcion, prefix_uri="http://repcon.org/schema#"):
    """
    Rutina de inferencia: Busca en el grafo los valores que más coincidan 
    con los filtros proporcionados, aunque no exista un incidente que 
    los cumpla todos simultáneamente.
    """
    
    diccionario_predicados = {
        0: "int_hasCustomer",
        1: "hasSupportCategory",
        2: "hasTypeInc",
        3: "incident_hasOrigin",
        4: "hasSupportGroup",
        5: "hasTechnician"
    }

    nombre_predicado_objetivo = diccionario_predicados.get(opcion)
    if not nombre_predicado_objetivo:
        return []

    filtros_activos = []
    for i, valor in enumerate(filtros_array):
        if valor is not None and str(valor).upper() != "NULL":
            valor_limpio = valor[0] if isinstance(valor, list) else valor
            filtros_activos.append((diccionario_predicados[i], valor_limpio))

    if not filtros_activos: # no debería activarse pero por si acaso
        query_fallback = f"""
        SELECT ?targetValue (COUNT(?targetValue) AS ?total)
        WHERE {{ ?incident <{prefix_uri}{nombre_predicado_objetivo}> ?targetValue . }}
        GROUP BY ?targetValue ORDER BY DESC(?total) LIMIT 1
        """
        res = g.query(query_fallback)
        return [str(row.targetValue).split("#")[-1] for row in res]

    
    # Buscamos qué 'targetValue' aparece más veces relacionado con CUALQUIERA de nuestros filtros.
    # Esta es la parte clave
    union_patterns = []
    for pred, val in filtros_activos:
        pattern = f"""
        {{
            ?incident <{prefix_uri}{pred}> <{prefix_uri}{val}> .
            ?incident <{prefix_uri}{nombre_predicado_objetivo}> ?targetValue .
        }}"""
        union_patterns.append(pattern)

    query_inference = f"""
    SELECT ?targetValue (COUNT(?targetValue) AS ?score)
    WHERE {{
        {{ {" UNION ".join(union_patterns)} }}
    }}
    GROUP BY ?targetValue
    ORDER BY DESC(?score)
    LIMIT 4
    """

    resultados = g.query(query_inference)
    
    inference_result = []
    for row in resultados:
        val_uri = str(row.targetValue)
        id_limpio = val_uri.split("#")[-1] if "#" in val_uri else val_uri.rsplit("/", 1)[-1]
        inference_result.append(id_limpio)

    
    return inference_result