"""
generar_tests.py
=================

Genera automáticamente un fichero `test_query_processor_generado.py` con 50
casos de prueba (unittest), siguiendo el mismo esquema que usa
`chatevaltesteoDeterminista.ipynb` (clase TestQueryProcessor, función
`procesar_query`, lista `self.casos_de_prueba` con tuplas
(texto_query, lista_esperada_de_6_elementos)).

Los 50 casos se dividen en 5 bloques de 10:

  Bloque 1 (1-10):   NINGUNA regla (df ni noValid) se activa.
  Bloque 2 (11-20):  Se activa AL MENOS UNA regla "df"  (y ninguna noValid).
  Bloque 3 (21-30):  Se activa AL MENOS UNA regla "noValid" (y ninguna df).
  Bloque 4 (31-40):  Se activan reglas df Y noValid simultáneamente,
                     pero SIN contradicción (predicados distintos).
  Bloque 5 (41-50):  Reglas df y noValid CONTRADICTORIAS: una regla df
                     fija un valor para un predicado y una regla noValid
                     prohíbe ese mismo valor para el mismo predicado.

Estructura de "mis_datos" / lista esperada (6 posiciones):
    0 - int_hasCustomer       (Cliente)
    1 - hasSupportCategory    (SupportCategory)
    2 - hasTypeInc            (TypeInc)
    3 - incident_hasOrigin    (Origin)
    4 - hasSupportGroup       (SupportGroup)
    5 - hasTechnician         (Technician)

El texto de la query sigue el formato usado en el notebook:
    "Hola quiero completar una query. Tengo el {supportCategory} y la
     empresa {cliente}"

Uso:
    python3 generar_tests.py
        --ttl filtrado.ttl
        --reglas reglas_incidentes.json
        --out test_query_processor_generado.py
"""

import argparse
import json
import re
from collections import defaultdict


PREFIX = "http://repcon.org/schema#"

CAMPOS = [
    "int_hasCustomer",      # 0
    "hasSupportCategory",   # 1
    "hasTypeInc",           # 2
    "incident_hasOrigin",   # 3
    "hasSupportGroup",      # 4
    "hasTechnician",        # 5
]

LABELS = [
    "Cliente",
    "SupportCategory",
    "TypeInc",
    "Origin",
    "SupportGroup",
    "Technician",
]


# ----------------------------------------------------------------------
# 1. PARSEO DEL GRAFO TTL
# ----------------------------------------------------------------------

def parse_ttl(path):
    """
    Parser ligero de Turtle, específico para el formato regular generado
    para este grafo (un bloque por incidente, terminado en
    `rdf:type repcon:incident .`).

    Devuelve una lista de dicts, uno por incidente, con las claves de
    CAMPOS (+ hasExternalTechnician / hasStateIncident / hasSupportTeam
    si aparecen) y sus valores (sin el prefijo `repcon:`).
    """
    incidentes = []
    actual = {}

    # Cada línea tiene forma:  repcon:hasX repcon:valor ;   o   rdf:type repcon:incident .
    # El bloque empieza con   repcon:incident_XXXX repcon:hasStateIncident ...
    line_re = re.compile(
        r'repcon:(\w+)\s+repcon:(\S+?)\s*[;.]\s*$'
    )
    subject_re = re.compile(
        r'^repcon:(incident_\S+)\s+repcon:(\w+)\s+repcon:(\S+?)\s*[;.]\s*$'
    )

    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("@prefix"):
                continue

            m_subj = subject_re.match(line)
            if m_subj:
                # Nueva entidad: guardamos la anterior si tenía datos
                if actual:
                    incidentes.append(actual)
                actual = {}
                pred, val = m_subj.group(2), m_subj.group(3)
                actual[pred] = val
                continue

            m = line_re.match(line)
            if m:
                pred, val = m.group(1), m.group(2)
                if pred == "type":
                    continue
                actual[pred] = val

    if actual:
        incidentes.append(actual)

    return incidentes


# ----------------------------------------------------------------------
# 2. PARSEO DE REGLAS
# ----------------------------------------------------------------------

def cargar_reglas(path):
    with open(path, encoding="utf-8") as f:
        reglas = json.load(f)

    # Eliminamos duplicados exactos conservando el orden
    vistas = set()
    unicas = []
    for r in reglas:
        clave = json.dumps(r, sort_keys=True)
        if clave not in vistas:
            vistas.add(clave)
            unicas.append(r)

    df_rules = [r for r in unicas if r["ruleType"] == "df"]
    nv_rules = [r for r in unicas if r["ruleType"] == "noValid"]
    return df_rules, nv_rules


def incidente_cumple_condicion(inc, condicion):
    """¿El incidente cumple TODOS los pares clave/valor de `condicion`?"""
    for campo, valor in condicion.items():
        if inc.get(campo) != valor:
            return False
    return True


def reglas_df_activadas(inc, df_rules):
    """Lista de reglas df cuyo `if` se cumple en el incidente."""
    return [r for r in df_rules if incidente_cumple_condicion(inc, r["if"])]


def reglas_nv_activadas(inc, nv_rules):
    """Lista de reglas noValid cuyo `if` se cumple en el incidente."""
    return [r for r in nv_rules if incidente_cumple_condicion(inc, r["if"])]


def hay_contradiccion(inc, df_activas, nv_activas):
    """
    Contradicción = una regla df activada fija {campo: valor_df} para un
    predicado, y una regla noValid activada (sobre el MISMO incidente)
    prohíbe un valor distinto {campo: valor_nv} para ESE MISMO predicado
    (valor_df != valor_nv). Ambas reglas "compiten" por decidir el valor
    del mismo predicado: una lo recomienda (df) y otra invalida una
    alternativa (noValid) -> contradicción de criterios.
    """
    for df in df_activas:
        for campo_df, val_df in df["then"].items():
            for nv in nv_activas:
                for campo_nv, val_nv in nv["then"].items():
                    if campo_df == campo_nv and val_df != val_nv:
                        return True
    return False


# ----------------------------------------------------------------------
# 3. CLASIFICACIÓN DE INCIDENTES EN LOS 5 BLOQUES
# ----------------------------------------------------------------------

def clasificar_incidentes(incidentes, df_rules, nv_rules):
    bloques = defaultdict(list)

    for inc in incidentes:
        # Solo nos interesan incidentes "completos" en los 6 campos
        if not all(c in inc for c in CAMPOS):
            continue
        if not inc.get("hasSupportCategory"):
            continue

        df_act = reglas_df_activadas(inc, df_rules)
        nv_act = reglas_nv_activadas(inc, nv_rules)

        if not df_act and not nv_act:
            bloques["sin_reglas"].append((inc, df_act, nv_act))
        elif df_act and not nv_act:
            bloques["solo_df"].append((inc, df_act, nv_act))
        elif nv_act and not df_act:
            bloques["solo_nv"].append((inc, df_act, nv_act))
        else:
            # Ambas activas: distinguir contradicción / sin contradicción
            if hay_contradiccion(inc, df_act, nv_act):
                bloques["contradictorias"].append((inc, df_act, nv_act))
            else:
                bloques["ambas"].append((inc, df_act, nv_act))

    return bloques


# ----------------------------------------------------------------------
# 4. CONSTRUCCIÓN DE CASOS DE PRUEBA
# ----------------------------------------------------------------------

def construir_caso(inc):
    """
    A partir de un incidente del grafo construye:
      - el texto de la query (usando supportCategory + cliente)
      - la lista esperada de 6 elementos (mis_datos final)
    """
    cliente = inc.get("int_hasCustomer")
    support_cat = inc.get("hasSupportCategory")

    texto = (
        f"Hola quiero completar una query. "
        f"Tengo el {support_cat} y la empresa {cliente}"
    )

    esperado = [
        inc.get("int_hasCustomer"),
        inc.get("hasSupportCategory"),
        inc.get("hasTypeInc"),
        inc.get("incident_hasOrigin"),
        inc.get("hasSupportGroup"),
        inc.get("hasTechnician"),  # puede no existir -> None
    ]
    # Normalizar ausencias a None (rdflib/dict.get ya devuelve None)
    esperado = [v if v is not None else None for v in esperado]

    return texto, esperado


def comentario_reglas(inc, df_act, nv_act):
    """Genera el bloque de comentarios explicativo (igual estilo notebook)."""
    lineas = []
    for r in df_act:
        cond = " + ".join(f"{k}={v}" for k, v in r["if"].items())
        cons = ", ".join(f"{k}={v}" for k, v in r["then"].items())
        lineas.append(f"# DF: {cond} -> {cons}")
    for r in nv_act:
        cond = " + ".join(f"{k}={v}" for k, v in r["if"].items())
        cons = ", ".join(f"{k}!={v}" for k, v in r["then"].items())
        lineas.append(f"# NV: {cond} -> {cons}")
    return lineas


# ----------------------------------------------------------------------
# 5. GENERACIÓN DEL FICHERO DE TEST
# ----------------------------------------------------------------------

HEADER = '''"""
test_query_processor_generado.py
==================================

Fichero de tests AUTOGENERADO por generar_tests.py a partir de:
  - filtrado.ttl              (grafo de incidentes)
  - reglas_incidentes.json     (reglas df / noValid)

Sigue el mismo esquema que chatevaltesteoDeterminista.ipynb:
  - función procesar_query(texto) que llama a procesar_mensaje_usuario
  - clase TestQueryProcessor(unittest.TestCase) con 50 casos repartidos
    en 5 bloques de 10 (sin reglas, solo df, solo noValid, ambas sin
    contradiccion, ambas contradictorias).

IMPORTANTE: este fichero asume que el entorno (graph, mis_datos,
procesar_mensaje_usuario, contadores, etc.) ya está definido, igual que
en el notebook original (CELDAS 1-7). Debe ejecutarse en ese mismo
contexto (p.ej. pegando estas celdas al final del notebook, o
importando ese setup antes de ejecutar este fichero).
"""

import unittest


def procesar_query(texto):
    """Reutiliza la lógica determinista del notebook."""
    global mis_datos

    veces = 0
    primero = True

    while True:
        if primero:
            entrada = texto

        primero = False

        continuar = procesar_mensaje_usuario(entrada)

        if veces >= 10:
            continuar = False

        veces += 1
        if not continuar:
            break

    return mis_datos


class TestQueryProcessor(unittest.TestCase):
    def setUp(self):
        self.casos_de_prueba = [
'''

FOOTER_TEMPLATE = '''        ]

    def test_sin_reglas(self):
        """Casos 1-10: ninguna regla df ni noValid activa."""
        print("Casos 1-10: ninguna regla df ni noValid activa.")
        for i, (query, expected) in enumerate(self.casos_de_prueba[:10], start=1):
            with self.subTest(caso=i, query=query):
                result = procesar_query(query)
                self.assertEqual(
                    result, expected,
                    msg=f"Caso {i} fallido.\\nQuery: {query}\\nEsperado: {expected}\\nObtenido: {result}"
                )

    def test_reglas_df(self):
        """Casos 11-20: solo reglas df se activan."""
        print("Casos 11-20: solo reglas df se activan.")
        for i, (query, expected) in enumerate(self.casos_de_prueba[10:20], start=11):
            with self.subTest(caso=i, query=query):
                result = procesar_query(query)
                self.assertEqual(
                    result, expected,
                    msg=f"Caso {i} fallido.\\nQuery: {query}\\nEsperado: {expected}\\nObtenido: {result}"
                )

    def test_reglas_novalid(self):
        """Casos 21-30: solo reglas noValid se activan."""
        print("Casos 21-30: solo reglas noValid se activan.")
        for i, (query, expected) in enumerate(self.casos_de_prueba[20:30], start=21):
            with self.subTest(caso=i, query=query):
                result = procesar_query(query)
                self.assertEqual(
                    result, expected,
                    msg=f"Caso {i} fallido.\\nQuery: {query}\\nEsperado: {expected}\\nObtenido: {result}"
                )

    def test_ambas_reglas(self):
        """Casos 31-40: reglas df y noValid se activan sin contradiccion."""
        print("Casos 31-40: reglas df y noValid se activan sin contradiccion.")
        for i, (query, expected) in enumerate(self.casos_de_prueba[30:40], start=31):
            with self.subTest(caso=i, query=query):
                result = procesar_query(query)
                self.assertEqual(
                    result, expected,
                    msg=f"Caso {i} fallido.\\nQuery: {query}\\nEsperado: {expected}\\nObtenido: {result}"
                )

    def test_reglas_contradictorias(self):
        """Casos 41-50: df y noValid se contradicen sobre el mismo predicado."""
        print("Casos 41-50: df y noValid se contradicen sobre el mismo predicado.")
        for i, (query, expected) in enumerate(self.casos_de_prueba[40:50], start=41):
            with self.subTest(caso=i, query=query):
                result = procesar_query(query)
                self.assertEqual(
                    result, expected,
                    msg=f"Caso {i} fallido.\\nQuery: {query}\\nEsperado: {expected}\\nObtenido: {result}"
                )


if __name__ == "__main__":
    unittest.main(argv=[""], verbosity=2, exit=False)
'''


def pyval(v):
    """Representación Python de un valor (string o None)."""
    if v is None:
        return "None"
    return repr(v)


def escribir_caso(buf, idx, inc, df_act, nv_act, titulo):
    texto, esperado = construir_caso(inc)

    buf.append(f"            # Caso {idx} · {titulo}")
    for c in comentario_reglas(inc, df_act, nv_act):
        buf.append(f"            {c}")

    buf.append("            (")
    buf.append(f"                {pyval(texto)},")

    items = ", ".join(pyval(v) for v in esperado)
    buf.append(f"                [{items}]")
    buf.append("            ),")
    buf.append("")


def generar(ttl_path, reglas_path, out_path, semilla=None):
    print("Cargando grafo TTL ...")
    incidentes = parse_ttl(ttl_path)
    print(f"  -> {len(incidentes)} incidentes leidos")

    print("Cargando reglas ...")
    df_rules, nv_rules = cargar_reglas(reglas_path)
    print(f"  -> {len(df_rules)} reglas df, {len(nv_rules)} reglas noValid")

    print("Clasificando incidentes ...")
    bloques = clasificar_incidentes(incidentes, df_rules, nv_rules)
    for k, v in bloques.items():
        print(f"  -> {k}: {len(v)} candidatos")

    NECESARIOS = {
        "sin_reglas": 10,
        "solo_df": 10,
        "solo_nv": 10,
        "ambas": 10,
        "contradictorias": 10,
    }

    for k, n in NECESARIOS.items():
        if len(bloques[k]) < n:
            print(
                f"AVISO: solo hay {len(bloques[k])} candidatos para "
                f"'{k}', se necesitan {n}. Se repetiran casos si es necesario."
            )

    buf = []
    buf.append(HEADER)

    idx = 1

    buf.append("            # " + "-" * 70)
    buf.append("            # BLOQUE 1 - Sin reglas (casos 1-10)")
    buf.append("            # Ninguna condicion de las reglas df ni noValid se cumple.")
    buf.append("            # " + "-" * 70)
    buf.append("")
    for i in range(10):
        inc, df_act, nv_act = bloques["sin_reglas"][i % max(1, len(bloques["sin_reglas"]))]
        escribir_caso(buf, idx, inc, df_act, nv_act, "sin reglas")
        idx += 1

    buf.append("            # " + "-" * 70)
    buf.append("            # BLOQUE 2 - Solo reglas df (casos 11-20)")
    buf.append("            # Al menos una regla df se activa; ninguna noValid aplica.")
    buf.append("            # " + "-" * 70)
    buf.append("")
    for i in range(10):
        inc, df_act, nv_act = bloques["solo_df"][i % max(1, len(bloques["solo_df"]))]
        escribir_caso(buf, idx, inc, df_act, nv_act, "regla(s) df activa(s)")
        idx += 1

    buf.append("            # " + "-" * 70)
    buf.append("            # BLOQUE 3 - Solo reglas noValid (casos 21-30)")
    buf.append("            # Al menos una regla noValid se activa; ninguna df aplica.")
    buf.append("            # " + "-" * 70)
    buf.append("")
    for i in range(10):
        inc, df_act, nv_act = bloques["solo_nv"][i % max(1, len(bloques["solo_nv"]))]
        escribir_caso(buf, idx, inc, df_act, nv_act, "regla(s) noValid activa(s)")
        idx += 1

    buf.append("            # " + "-" * 70)
    buf.append("            # BLOQUE 4 - Ambas reglas sin contradiccion (casos 31-40)")
    buf.append("            # Reglas df y noValid se activan, sobre predicados distintos.")
    buf.append("            # " + "-" * 70)
    buf.append("")
    for i in range(10):
        inc, df_act, nv_act = bloques["ambas"][i % max(1, len(bloques["ambas"]))]
        escribir_caso(buf, idx, inc, df_act, nv_act, "df + noValid sin contradiccion")
        idx += 1

    buf.append("            # " + "-" * 70)
    buf.append("            # BLOQUE 5 - Reglas contradictorias (casos 41-50)")
    buf.append("            # Una regla df y una regla noValid actuan sobre el mismo")
    buf.append("            # predicado con valores distintos -> contradiccion directa.")
    buf.append("            # " + "-" * 70)
    buf.append("")
    for i in range(10):
        inc, df_act, nv_act = bloques["contradictorias"][i % max(1, len(bloques["contradictorias"]))]
        escribir_caso(buf, idx, inc, df_act, nv_act, "df y noValid contradictorias")
        idx += 1

    buf.append(FOOTER_TEMPLATE)

    contenido = "\n".join(buf)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(contenido)

    print(f"\nFichero generado: {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Genera 50 casos de test (5 bloques de 10) a partir del "
                     "grafo TTL y las reglas de incidentes."
    )
    parser.add_argument("--ttl", default="filtrado.ttl", help="Ruta al grafo TTL")
    parser.add_argument("--reglas", default="reglas_incidentes.json", help="Ruta al JSON de reglas")
    parser.add_argument("--out", default="test_query_processor_generado.py", help="Fichero de salida")
    args = parser.parse_args()

    generar(args.ttl, args.reglas, args.out)
