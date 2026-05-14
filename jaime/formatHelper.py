import re


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