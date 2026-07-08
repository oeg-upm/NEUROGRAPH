# ============================================
# CLASE LLMChat - GraphRAG con Ollama + RDF
# Combina: generadorEjemplos.ipynb,
#          chatAIcompletion.py,
#          chatAIcompletion-v2testeo.py
# ============================================

import os
import json
import re
import random
import asyncio
import datetime
from time import time, sleep
from uuid import uuid4

from openai import OpenAI, AsyncOpenAI
from rdflib import Graph

from searchInGraph import (
    buscar_frecuentes_por_opcion,
    inferir_valor_adecuado,
)
from formatHelper import (
    extraer_support_category,
    extraer_cliente,
    formatear_para_llm,
    arreglar_lista_llm,
    extraer_respuesta_limpia_llm,
    merge_lista_y_parametro,
    formatear_datos_existentes_LLM,
    aplicar_reglas,
)
import config


class LLMChat:
    """
    Clase unificada que encapsula la lógica de GraphRAG con Ollama + RDF.

    Responsabilidades:
      - Cargar y mantener el grafo RDF.
      - Generar ejemplos de queries (generate_examples).
      - Completar el siguiente campo de una query incompleta (next_field_determinate).
      - Buscar y clasificar ejemplos según qué reglas activan (find_examples).
      - Evaluar un dataset en modo batch/test (evaluate).
      - Ejecutar el bucle interactivo con un usuario (test).
    """

    # ------------------------------------------------------------------
    # INICIALIZACIÓN
    # ------------------------------------------------------------------

    def __init__(self, graph_file_path: str, rules_path: str):
        """
        Parámetros
        ----------
        graph_file_path : str
            Ruta al fichero .ttl del grafo RDF.
        rules_path : str
            Ruta al fichero JSON de reglas de incidentes.
        """
        self.graph_file_path = graph_file_path
        self.rules_path = rules_path

        # Carga del grafo RDF
        self.graph = Graph()
        self.graph.parse(graph_file_path, format=config.TTL_FORMAT)
        print(f"Grafo cargado correctamente ({len(self.graph)} triples)")

        # Clientes OpenAI / Ollama (síncrono y asíncrono)
        self.client = config.client
        self.async_client = config.async_client

        # Contadores globales de reglas activadas (se resetean en find_examples)
        self._contadores: dict = {"vecesdf": 0, "vecesnv": 0}

    # ------------------------------------------------------------------
    # UTILIDADES PRIVADAS
    # ------------------------------------------------------------------

    @staticmethod
    def _open_file(filepath: str) -> str:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()

    @staticmethod
    def _save_file(filepath: str, content: str) -> None:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

    @staticmethod
    def _timestamp_to_datetime(unix_time: float) -> str:
        return datetime.datetime.fromtimestamp(unix_time).strftime(
            "%A, %B %d, %Y at %I:%M%p %Z"
        )

    @staticmethod
    def _elemento_mas_comun(array: list):
        """Devuelve el elemento más frecuente de la lista."""
        return max(array, key=array.count)

    # ------------------------------------------------------------------
    # FUNCIONES LLM (SÍNCRONAS Y ASÍNCRONAS)
    # ------------------------------------------------------------------

    def _text_completion(self, prompt: str, engine: str = config.MI_MODELO) -> str:
        max_retry, retry = 5, 0
        while True:
            try:
                response = self.client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model=engine,
                )
                text = response.choices[0].message.content
                text = re.sub(r"[\r\n]+", "\n", text)
                text = re.sub(r"[\t ]+", " ", text)
                return text
            except Exception as exc:
                retry += 1
                if retry >= max_retry:
                    return f"Model error: {exc}"
                print(f"Error comunicando con el modelo: {exc}")
                sleep(config.RETRY_DELAY_SECONDS)

    async def _text_completion_async(
        self, prompt: str, engine: str = config.MI_MODELO
    ) -> str:
        max_retry, retry = 5, 0
        while True:
            try:
                response = await self.async_client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model=engine,
                )
                text = response.choices[0].message.content
                text = re.sub(r"[\r\n]+", "\n", text)
                text = re.sub(r"[\t ]+", " ", text)
                return text
            except Exception as exc:
                retry += 1
                if retry >= max_retry:
                    return f"Model error: {exc}"
                print(f"Error comunicando con el modelo (Intento {retry}/{max_retry}): {exc}")
                await asyncio.sleep(config.RETRY_DELAY_SECONDS)

    async def _text_completion_batch(
        self, prompts_list: list[str], engine: str = config.MI_MODELO
    ) -> list[str]:
        tasks = [self._text_completion_async(p, engine) for p in prompts_list]
        return await asyncio.gather(*tasks)

    # ------------------------------------------------------------------
    # CONSULTA AL GRAFO: prompt → mis_datos actualizado
    # ------------------------------------------------------------------

    def _llamar_llm_para_campo(
        self,
        mis_datos: list,
        cat_buscar: int,
        mi_opcion: str,
        context_path: str,
        model: str,
    ) -> list:
        """
        Construye el prompt para el campo `cat_buscar`, llama al LLM 3 veces
        en paralelo y fusiona el resultado en `mis_datos`.
        Devuelve `mis_datos` actualizado.
        """
        data = (
                f"El campo a rellenar es "
                f"{config.DICCIONARIO_PREFIJOS[cat_buscar]}"
                f" y estas son las opciones:\n\nrepcon:"
                f"{config.DICCIONARIO_PREFIJOS[cat_buscar]}"
                f" repcon:{mi_opcion}"
            )

        reglas = formatear_para_llm(
            self.rules_path,
            tipo_cond=config.DICCIONARIO_PREDICADOS[cat_buscar],
        )
        prompt_base = self._open_file(context_path)
        mensajeinstruc = (
            "Se espera que extraigas el campo "
            + config.DICCIONARIO_PREFIJOS[cat_buscar]
        )
        datos_existentes = formatear_datos_existentes_LLM(mis_datos)

        prompt = (
            prompt_base
            .replace("<<DATOS>>", data)
            .replace("<<CONVERSACIÓN>>", datos_existentes)
            .replace("<<MENSAJE>>", mensajeinstruc)
            .replace("<<REGLAS>>", "\n".join(reglas))
        )

        outputs = asyncio.run(self._text_completion_batch([prompt, prompt, prompt], engine=model))

        cleaned = []
        for x in outputs:
            limpio = extraer_respuesta_limpia_llm(arreglar_lista_llm(x)).replace("repcon:", "")
            cleaned.append(limpio.replace('"ERROR"', "ERROR").replace("'ERROR'", "ERROR"))

        
        output = self._elemento_mas_comun(cleaned) 
        return output

    # ------------------------------------------------------------------
    # 1. generate_examples
    # ------------------------------------------------------------------

    def generate_examples(
        self,
        n: int = 500,
        prefix_uri: str = "http://repcon.org/schema#",
    ) -> list[str]:
        """
        Genera `n` frases de ejemplo combinando clientes y categorías de
        soporte extraídos aleatoriamente del grafo.

        Equivale a las celdas del notebook:
          obtener_100_clientes_aleatorios +
          obtener_100_categorias_soporte_aleatorias +
          generar_combinaciones_query
        """

        def _sparql_distinct_random(predicado_local: str, var_name: str) -> list[str]:
            uri = f"<{prefix_uri}{predicado_local}>"
            q = f"""
            SELECT DISTINCT ?{var_name}
            WHERE {{
                ?incident {uri} ?{var_name} .
            }}
            ORDER BY RAND()
            LIMIT 100
            """
            resultados = self.graph.query(q)
            valores = []
            for row in resultados:
                val_uri = str(getattr(row, var_name))
                if "#" in val_uri:
                    id_limpio = val_uri.split("#")[-1]
                elif "/" in val_uri:
                    id_limpio = val_uri.rsplit("/", 1)[-1]
                else:
                    id_limpio = val_uri
                valores.append(id_limpio)
            return valores

        clientes = _sparql_distinct_random("int_hasCustomer", "customer")
        categorias = _sparql_distinct_random("hasSupportCategory", "category")

        if not clientes or not categorias:
            print("Error: No se pudieron obtener clientes o categorías del grafo.")
            return []

        combinaciones = []
        for _ in range(n):
            cat = random.choice(categorias)
            emp = random.choice(clientes)
            frase = (
                f"Hola quiero completar una query. "
                f"Tengo el {cat} y la empresa {emp}"
            )
            combinaciones.append(frase)

        return combinaciones

    # ------------------------------------------------------------------
    # 2. next_field_determinate   (sin LLM: usa reglas + grafo)
    # ------------------------------------------------------------------

    def next_field_determinate(
        self,
        mis_datos: list,
        flags: dict | None = None,
    ) -> tuple[bool, list, dict, int]:
        """
        Completa el siguiente campo None de `mis_datos` usando el grafo RDF
        y las reglas JSON (sin invocar el LLM).

        Equivale a `completar_siguiente_campo` del notebook.

        Devuelve
        --------
        continuar       : bool  — False si ya no hay None en mis_datos
        mis_datos       : list  — estado actualizado
        flags           : dict  — contadores de reglas activadas
        regla_aplicada  : int   — índice de la regla aplicada (-1 si ninguna)
        """
        if flags is None:
            flags = {"vecesdf": 0, "vecesnv": 0}

        regla_aplicada = -1

        if None not in mis_datos and "None" not in mis_datos:
            return False, mis_datos, flags, regla_aplicada

        try:
            cat_buscar = mis_datos.index(None)
        except ValueError:
            cat_buscar = mis_datos.index("None")

        graph_data = buscar_frecuentes_por_opcion(self.graph, mis_datos, cat_buscar)
        if not graph_data:
            graph_data = inferir_valor_adecuado(self.graph, mis_datos, cat_buscar)

        graph_data, regla_aplicada = aplicar_reglas(
            self.rules_path,
            mis_datos,
            cat_buscar,
            graph_data,
            flags,
        )

        if graph_data:
            mis_datos[cat_buscar] = graph_data[0]

        return True, mis_datos, flags, regla_aplicada

    # ------------------------------------------------------------------
    # 3. find_examples
    # ------------------------------------------------------------------

    def find_examples(
        self,
        examples_list: list[str],
        df_number: int,
        nv_number: int,
        both_number: int,
    ) -> tuple[list, list, list, list]:
        """
        Procesa una lista de frases y las clasifica según las reglas que
        activan: sólo 'df', sólo 'nv', ambas o ninguna.

        Recoge hasta `df_number` casos df, `nv_number` casos nv,
        `both_number` casos que activan ambas reglas.

        Equivale al bucle principal del notebook más `procesar_query` y
        `generar_caso`.

        Devuelve
        --------
        casos_df, casos_nv, casos_ambos, casos_ninguno : listas de dicts
        generados por `_generar_caso`.
        """
        casos_df: list = []
        casos_nv: list = []
        casos_ambos: list = []
        casos_ninguno: list = []
        self._contadores = {"vecesdf": 0, "vecesnv": 0}

        for frase in examples_list:
            df_ant = self._contadores["vecesdf"]
            nv_ant = self._contadores["vecesnv"]

            resultado, ambas, regla_aplicada = self._procesar_query_notebook(frase)
            caso = self._generar_caso(frase, regla_aplicada, resultado)

            if ambas:
                if len(casos_ambos) < both_number:
                    casos_ambos.insert(0, caso)
            elif (
                self._contadores["vecesdf"] == df_ant + 1
                and self._contadores["vecesnv"] == nv_ant + 1
            ):
                if len(casos_ambos) < both_number:
                    casos_ambos.insert(0, caso)
            elif self._contadores["vecesnv"] == nv_ant + 1:
                if len(casos_nv) < nv_number:
                    casos_nv.insert(0, caso)
            elif self._contadores["vecesdf"] == df_ant + 1:
                if len(casos_df) < df_number:
                    casos_df.insert(0, caso)
            else:
                casos_ninguno.insert(0, caso)

            if (
                len(casos_df) >= df_number
                and len(casos_nv) >= nv_number
                and len(casos_ambos) >= both_number
            ):
                break

        return casos_df, casos_nv, casos_ambos, casos_ninguno

    # Helpers internos de find_examples --------------------------------

    def _procesar_query_notebook(
        self, texto: str
    ) -> tuple[list, bool, int]:
        """
        Versión basada en reglas (sin LLM) del notebook.
        Devuelve (mis_datos, ambas, regla_de_verdad).
        """
        flags = {"vecesdf": 0, "vecesnv": 0}
        mis_datos = [None, None, None, None, None, None]
        ambas = False
        regla_de_verdad = -1

        mis_datos[0] = extraer_cliente(texto)
        mis_datos[1] = extraer_support_category(texto)

        while True:
            continuar, mis_datos, flags, regla_aplicada = self.next_field_determinate(
                mis_datos, flags
            )
            if regla_aplicada != -1:
                regla_de_verdad = regla_aplicada

            if not continuar:
                if flags["vecesdf"] == 2 and flags["vecesnv"] == 2:
                    self._contadores["vecesdf"] += 1
                    self._contadores["vecesnv"] += 1
                    ambas = True
                else:
                    if flags["vecesdf"] > 0:
                        self._contadores["vecesdf"] += 1
                    if flags["vecesnv"] > 0:
                        self._contadores["vecesnv"] += 1
                break

        print(f"GraphRAG: query acabada → {mis_datos}")
        return mis_datos, ambas, regla_de_verdad

    def _generar_caso(
        self, query: str, numregla: int, resultado: list
    ) -> dict | None:
        """
        Lee la regla `numregla` del fichero JSON y construye el dict de caso.
        Equivale a `generar_caso` del notebook.
        """
        try:
            with open(self.rules_path, "r", encoding="utf-8") as f:
                reglas = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            print(f"Error leyendo reglas: {exc}")
            return None

        indice = int(numregla) - 1
        if indice < 0 or indice >= len(reglas):
            print(f"Error: regla {numregla} no existe.")
            return None

        regla_obj = reglas[indice]
        rule_type = regla_obj.get("ruleType", "")
        then_dict = regla_obj.get("then", {})
        rule_field = list(then_dict.keys())[0] if then_dict else ""
        rule_value = list(then_dict.values())[0] if then_dict else ""

        return {
            "query": query,
            "expected": resultado,
            "rule": str(numregla),
            "ruletype": rule_type,
            "ruleField": rule_field,
            "ruleValue": rule_value,
        }



    #def next_field_LLM(self)
        
    # ------------------------------------------------------------------
    # 4. evaluate   (batch / automático — v2testeo)
    # ------------------------------------------------------------------

    def evaluate(
        self,
        context_path: str,
        dataset_path: str,
        model: str = config.MI_MODELO, # Asegúrate de importar config si no lo está
        output_dir: str | None = None,
        output_filename: str | None = None,
    ) -> dict:
        """
        Evalúa automáticamente un dataset JSON contra el sistema GraphRAG + LLM.

        Equivale al `__main__` de chatAIcompletion-v2testeo.py.

        Parámetros
        ----------
        context_path    : ruta al fichero de contexto/prompt base.
        dataset_path    : ruta al JSON con los casos de prueba.
        model           : modelo LLM a usar.
        output_dir      : directorio donde guardar el fichero de resultados.
                          Si es None no se guarda ningún fichero.
        output_filename : nombre del fichero de resultados (sin extensión).
                          Si es None se usa 'resultados_<timestamp>'.
                          Se generan dos ficheros: un .json con los datos
                          y un .txt con el reporte legible.

        Devuelve un dict con el resumen de resultados.
        """
        try:
            with open(dataset_path, "r", encoding="utf-8") as f:
                dataset = json.load(f)
        except FileNotFoundError:
            print(f"Error: no se encontró '{dataset_path}'.")
            return {}

        total = len(dataset)
        aciertos_globales = 0
        registro_ruletype: dict = {}
        registro_ruleField: dict = {}
        
        # Lista para acumular los logs individuales de cada query
        logs_detallados = []

        logs_detallados.append("=" * 50)
        logs_detallados.append(f" INICIANDO EVALUACIÓN DE {total} QUERIES ")
        logs_detallados.append("=" * 50)
        
        print("=" * 50)
        print(f" INICIANDO EVALUACIÓN DE {total} QUERIES ")
        print("=" * 50)

        for item in dataset:
            # Capturamos el 4º valor de retorno: log_item
            acierto, r_type, r_field, log_item = self._procesar_item_testeo(
                item, context_path, model
            )
            
            # Guardamos el log del ítem
            logs_detallados.append(log_item)

            registro_ruletype.setdefault(r_type, {"aciertos": 0, "fallos": 0})
            registro_ruleField.setdefault(r_field, {"aciertos": 0, "fallos": 0})

            if acierto:
                registro_ruletype[r_type]["aciertos"] += 1
                registro_ruleField[r_field]["aciertos"] += 1
                aciertos_globales += 1
            else:
                registro_ruletype[r_type]["fallos"] += 1
                registro_ruleField[r_field]["fallos"] += 1

        precision = (aciertos_globales / total * 100) if total else 0

        # Reporte en consola
        lineas_reporte = [
            "=" * 44,
            "            RESUMEN DE PRUEBAS             ",
            "=" * 44,
            f"Total queries  : {total}",
            f"Aciertos       : {aciertos_globales}",
            f"Fallos         : {total - aciertos_globales}",
            f"Precisión      : {precision:.2f}%",
            "",
            "--- Por 'ruletype' ---",
        ]
        for rt, c in registro_ruletype.items():
            t = c["aciertos"] + c["fallos"]
            p = (c["aciertos"] / t * 100) if t else 0
            lineas_reporte.append(
                f"  {rt.ljust(10)}: {c['aciertos']} aciertos, {c['fallos']} fallos ({p:.1f}%)"
            )
        lineas_reporte.append("\n--- Por 'ruleField' ---")
        for rf, c in registro_ruleField.items():
            t = c["aciertos"] + c["fallos"]
            p = (c["aciertos"] / t * 100) if t else 0
            lineas_reporte.append(
                f"  {rf.ljust(20)}: {c['aciertos']} aciertos, {c['fallos']} fallos ({p:.1f}%)"
            )

        reporte_texto = "\n".join(lineas_reporte)
        print(reporte_texto)

        resultado = {
            "total": total,
            "aciertos": aciertos_globales,
            "fallos": total - aciertos_globales,
            "precision": precision,
            "por_ruletype": registro_ruletype,
            "por_ruleField": registro_ruleField,
        }

        # Guardar ficheros si se indicó un directorio de salida
        if output_dir is not None:
            os.makedirs(output_dir, exist_ok=True)

            if output_filename is None:
                # Asegúrate de haber importado datetime
                ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                output_filename = f"resultados_{ts}"

            # Eliminar extensión si el usuario la incluyó accidentalmente
            base_name = os.path.splitext(output_filename)[0]

            #ruta_json = os.path.join(output_dir, f"{base_name}.json")
            ruta_txt  = os.path.join(output_dir, f"{base_name}.txt")

            #with open(ruta_json, "w", encoding="utf-8") as f:
            #    json.dump(resultado, f, ensure_ascii=False, indent=2)

            # Combinar los logs de los ítems con el resumen final
            texto_completo_fichero = "\n".join(logs_detallados) + "\n" + reporte_texto

            with open(ruta_txt, "w", encoding="utf-8") as f:
                f.write(texto_completo_fichero)

            print(f"\nResultados guardados en:\n  {ruta_txt}")

        return resultado

    # Helper interno de test (bucle interactivo) -----------------------

    # ------------------------------------------------------------------
    # 6. next_field_llm   
    # ------------------------------------------------------------------
    
    def next_field_llm(
        self,
        mis_datos: list,
        context_path: str,
        model: str,
    ) -> list:
        """
        Completa el siguiente campo None de `mis_datos` usando el LLM.
        Versión para el bucle interactivo (test): reintenta indefinidamente
        hasta obtener una respuesta válida distinta de ERROR.
        """
        if None not in mis_datos and "None" not in mis_datos:
            print(f"GraphRAG: query acabada → {mis_datos}")
            return mis_datos

        try:
            cat_buscar = mis_datos.index(None)
        except ValueError:
            cat_buscar = mis_datos.index("None")

        graph_data = buscar_frecuentes_por_opcion(self.graph, mis_datos, cat_buscar)
        if not graph_data:
            graph_data = inferir_valor_adecuado(self.graph, mis_datos, cat_buscar)

        retry = True

        max_a_probar = len(graph_data) if graph_data else 0
        siguiente_a_probar = 1
        
        while retry:
            retry = False


            mi_opcion = graph_data[0] 
            
            if retry and siguiente_a_probar < max_a_probar:
                    mi_opcion = graph_data[siguiente_a_probar]
                    siguiente_a_probar += 1
            
            output = self._llamar_llm_para_campo(
                mis_datos, cat_buscar, mi_opcion, context_path, model
            )
            #output = self._obtener_mas_comun(cleaned)
            mis_datos = merge_lista_y_parametro(mis_datos, output)

            print("--- Estado actualizado de mis_datos ---")
            print(mis_datos)

            if output == "ERROR":
                retry = True  # sigue intentando hasta resolver

        return mis_datos

    # Helper interno de evaluate ----------------------------------------

    def _completar_siguiente_campo_llm_evaluate(
        self,
        mis_datos: list,
        context_path: str,
        model: str,
    ) -> list | str:
        """
        Completa el siguiente campo None de `mis_datos` usando el LLM.
        Versión para evaluate: si el LLM detecta una contradicción de regla
        o no puede resolver el campo (output == ERROR o None), NO reintenta
        y devuelve la cadena "ERROR" para que el caso se contabilice como
        fallo de inmediato.

        Devuelve
        --------
        list  — mis_datos actualizado si el campo se resolvió correctamente.
        "ERROR" — si el LLM devolvió ERROR o una respuesta inválida.
        """
        if None not in mis_datos and "None" not in mis_datos:
            print(f"GraphRAG: query acabada → {mis_datos}")
            return mis_datos

        try:
            cat_buscar = mis_datos.index(None)
        except ValueError:
            cat_buscar = mis_datos.index("None")

        graph_data = buscar_frecuentes_por_opcion(self.graph, mis_datos, cat_buscar)
        if not graph_data:
            graph_data = inferir_valor_adecuado(self.graph, mis_datos, cat_buscar)


        mi_opcion = graph_data[0] 
        
        output = self._llamar_llm_para_campo(
            mis_datos, cat_buscar, mi_opcion, context_path, model
        )

        mis_datos = merge_lista_y_parametro(mis_datos, output)
        
        if output == "ERROR":
            mis_datos[cat_buscar] = output

        #mis_datos = merge_lista_y_parametro(mis_datos, output)

        #print("--- Estado actualizado de mis_datos ---")
        #print(mis_datos)

        return mis_datos

    def _preprocesado(self, mis_datos: list) -> tuple[list, list]:
        MAX_LEN = 6
        expected = mis_datos + [None] * (MAX_LEN - len(mis_datos))
        mis_datospre = mis_datos[:-1] + [None] * (MAX_LEN - len(mis_datos[:-1]))
        return mis_datospre, expected

    def _procesar_item_testeo(
        self,
        item_json: dict,
        context_path: str,
        model: str,
    ) -> tuple[bool, str, str, str]: # <-- Añadimos un str al tipado de retorno
        """
        Evalúa un único caso del dataset usando
        _completar_siguiente_campo_llm_evaluate.
        Si en cualquier paso el LLM devuelve ERROR, el caso se marca
        como fallo sin intentar completar los campos restantes.
        Devuelve (acierto, ruletype, ruleField, log_item).
        """
        query_text = item_json.get("query", "")
        mis_datos = item_json.get("expected", [])
        ruletype = item_json.get("ruletype", "Desconocido")
        ruleField = item_json.get("ruleField", "Desconocido")

        mis_datospre, expected = self._preprocesado(mis_datos)

        # Completar campo a campo; abortar en cuanto aparezca ERROR
        #MAL
        #result = mis_datospre
        #while isinstance(result, list) and (None in result or "None" in result):
            
        result = self._completar_siguiente_campo_llm_evaluate(
                mis_datospre, context_path, model
            )
            #if result == "ERROR":
            #    break

        acierto = (result == expected)
        estado = "✅ ACIERTO" if acierto else "❌ FALLO"
        
        # Construimos el log para este ítem
        log_lines = []
        log_lines.append(f"{estado} | RuleType: {ruletype} | RuleField: {ruleField}")
        if not acierto:
            log_lines.append(f"   Esperado: {expected}")
            log_lines.append(f"   Obtenido: {result}")
        log_lines.append(f'GraphRAG: query: "{query_text}"\n')
        
        log_item = "\n".join(log_lines)
        
        # Mantenemos la salida por consola
        print(log_item)

        return acierto, ruletype, ruleField, log_item

    # ------------------------------------------------------------------
    # 5. test   (bucle interactivo — chatAIcompletion.py)
    # ------------------------------------------------------------------

    def chat_test(
        self,
        context_path: str,
        examples_path: str,
        model: str = config.MI_MODELO,
    ) -> None:
        """
        Bucle interactivo con el usuario. Lee input por consola y va
        completando `mis_datos` campo a campo usando el LLM.

        Equivale al `__main__` de chatAIcompletion.py.

        Parámetros
        ----------
        context_path  : ruta al fichero de contexto/prompt base.
        examples_path : ruta al directorio de logs (se crea un fichero por sesión).
        model         : modelo LLM a usar.
        """
        print("\n" + "=" * 40)
        print(" SISTEMA GraphRAG + Ollama INICIADO")
        print("=" * 40)
        print("Escribe 'q' para salir\n")

        unique_conv_id = str(uuid4())
        log_file_path = os.path.join(examples_path, f"{unique_conv_id}_log.txt")
        self._save_file(log_file_path, "")

        mis_datos = [None, None, None, None, None, None]
        primera = True
        user_input = ""

        while True:
            if None not in mis_datos and "None" not in mis_datos:
                print("\nGraphRAG: query acabada. La query completada es:")
                print(mis_datos)
                break

            if primera:
                user_input = input("\nUSER: ")
            primera = False

            if user_input.lower() == "q":
                print("\nFinalizando conversación...")
                break

            timestamp = time()
            timestring = self._timestamp_to_datetime(timestamp)
            message = f"USER: {timestring} - {user_input}"

            # Extraer campos iniciales (cliente y categoría) del texto libre
            if mis_datos[0] is None:
                cliente = extraer_cliente(user_input)
                if cliente:
                    print(f"Cliente extraído: {cliente}")
                mis_datos[0] = cliente

            if mis_datos[1] is None:
                mis_datos[1] = extraer_support_category(user_input)




            mis_datos = self.next_field_llm(mis_datos, context_path, model)
            
            # Buscar el siguiente campo None
            #try:
            #    cat_buscar = mis_datos.index(None)
            #except ValueError:
            #    cat_buscar = mis_datos.index("None")
#
            #graph_data = buscar_frecuentes_por_opcion(self.graph, mis_datos, cat_buscar)
            #if not graph_data:
            #    graph_data = inferir_valor_adecuado(self.graph, mis_datos, cat_buscar)
#
            #retry = True
            ##output = "ERROR"
            #
            #while retry:
            #    
            #    retry = False
            prev_conv = self._open_file(log_file_path)
#
            #    _completar_siguiente_campo_llm
            #    _completar_siguiente_campo_llm(
            #        self,
            #        mis_datos: list,
            #        context_path: str,
            #        model: str,
            #    )
            #    
            #    cleaned = self._llamar_llm_para_campo(
            #        mis_datos, cat_buscar, mi_opcion, context_path, model
            #    )
            #    output = self._elemento_mas_comun(cleaned)
            #    mis_datos = merge_lista_y_parametro(mis_datos, output)
#
            #    print("\n--- Estado actualizado de mis_datos ---")
            #    print(mis_datos)
#
            #    if output == "ERROR":
            #        retry = True

            # Guardar log
            
            try:
                cat_buscar = mis_datos.index(None)
            except ValueError:
                cat_buscar = len(mis_datos)
                
            output = mis_datos[cat_buscar-1]

                        #try:
            #    cat_buscar = mis_datos.index(None)
            #except ValueError:
            #    cat_buscar = mis_datos.index("None")
            
            timestamp = time()
            timestring = self._timestamp_to_datetime(timestamp)
            msg_bot = f"[Asistente]: {timestring} - {output}"
            print(f"\n[Asistente]: {output}")
            self._save_file(log_file_path, prev_conv + "\n" + message + "\n" + msg_bot)


# ------------------------------------------------------------------
# USO DE EJEMPLO
# ------------------------------------------------------------------
if __name__ == "__main__":
    chat = LLMChat(
        graph_file_path=config.TTL_FILE_PATH,
        rules_path="./textos/reglas_incidentes.json",
    )
    
    
    # Generar ejemplos y buscar casos de prueba
    
    #ejemplos = chat.generate_examples(n=200)
    #casos_df, casos_nv, casos_ambos, casos_ninguno = chat.find_examples(
    #    ejemplos, df_number=0, nv_number=0, both_number=0
    #)
    #print(f"Casos df={len(casos_df)}, nv={len(casos_nv)}, ambos={len(casos_ambos)}")

    # Evaluar dataset
    resultados = chat.evaluate(
        context_path=config.CONTEXTO_FILE_PATH,
        dataset_path="./textos/datasetsantolimpio3.json", output_dir="./results", output_filename="res_evafin2"
    )

    # Bucle interactivo
    #chat.chat_test(
    #     context_path=config.CONTEXTO_FILE_PATH,
    #     examples_path=config.LOGS_DIR,
    # )