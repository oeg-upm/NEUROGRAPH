from c_clause import QAHandler, Loader
from clause import Options

# 1. Definir opciones
opts = Options()
# 'noisyor' es una función de agregación común para combinar puntuaciones de reglas
opts.set("qa_handler.aggregation_function", "noisyor")

# 2. Inicializar el cargador y cargar los datos del archivo
loader = Loader(options=opts.get("loader"))
# Cargamos directamente el archivo procesado (formato: sujeto predicado objeto)
loader.load_data("grafo_procesado.txt")

# 3. Definir reglas basadas en los predicados de tus datos
# Nota: En un escenario real, estas reglas se aprenden automáticamente o las define un experto
#rules = [
#     "hasSupportCategory(X,Y) <= hasSupportGroup(X,Z)",
#     "hasStateIncident(X,statusIncident__2) <= hasTypeInc(X,typeIncident__1)",
#     "int_hasCustomer(X,C) <= hasSupportGroup(X,G)"
#]

#rules = ["hasTechnician(X, employee__429) <= int_hasCustomer(X, company_3S8A2Y7FV)"]
rules = ["hasTechnician(X,employee__429) <= int_hasCustomer(X,company_149763729881762303079)"]
# 4. Definir estadísticas de las reglas: [número de predicciones, soporte]
# Estas cifras afectan la confianza (score) de los resultados
stats = [
    [100, 80]
    #,
    #[50, 45],
    #[200, 10],
]

# Cargar las reglas en el modelo
loader.load_rules(rules=rules, stats=stats)

# 5. Configurar el manejador de consultas (QAHandler)
qa = QAHandler(options=opts.get("qa_handler"))


def get_filtered_answers(incident_id, property_name):
    """
    Obtiene respuestas y aplica las restricciones de negocio solicitadas.
    """
    # 1. Calcular respuestas normales
    qa.calculate_answers(queries=[(incident_id, property_name)], loader=loader, direction="tail")
    answers = qa.get_answers(as_string=True)[0]  # Lista de (valor, score)

    filtered_results = []

    # 2. Obtener contexto del incidente para validar las restricciones
    # (Buscamos en el loader qué otras propiedades tiene este incidente actualmente)
    # Nota: Usamos una consulta rápida para saber su estado o su origen
    qa.calculate_answers(queries=[(incident_id, "hasStateIncident")], loader=loader, direction="tail")
    current_state = [a[0] for a in qa.get_answers(as_string=True)[0]]

    qa.calculate_answers(queries=[(incident_id, "incident_hasOrigin")], loader=loader, direction="tail")
    current_origin = [a[0] for a in qa.get_answers(as_string=True)[0]]

    # 3. Aplicar lógica de filtrado
    for value, score in answers:
        is_valid = True

        # REGLA 1: No es opción válida 0 para hasDedicationTimeMin si hasStateIncident es stateIncident_2
        if property_name == "hasDedicationTimeMin" and value == "0":
            if "stateIncident_2" in current_state:
                is_valid = False

        # REGLA 2: No es opción válida company_F7UMNAXNO para int_hasCustomer si incident_hasOrigin es incidentOrigin_2
        if property_name == "int_hasCustomer" and value == "company_F7UMNAXNO":
            if "incidentOrigin_2" in current_origin:
                is_valid = False

        if is_valid:
            filtered_results.append((value, score))

    return filtered_results




# --- Ejemplo de Consulta 1: ¿Qué categoría de soporte tiene un incidente específico? ---
# Usamos un ID que existe en tu archivo: incident_1497610379091762304042
#queries_tail = [("incident_1497610379091762304042", "hasSupportCategory")]
#
#print(f"Calculando respuestas para (sujeto, predicado, ?): {queries_tail[0]}")
#qa.calculate_answers(queries=queries_tail, loader=loader, direction="tail")
#ans_tail = qa.get_answers(as_string=True)
#if ans_tail:
#    print("Resultados encontrados:", ans_tail[0])
#
## --- Ejemplo de Consulta 2: ¿Qué incidentes pertenecen a una categoría específica? ---
#queries_head = [("supportCategory_14976369491762302689", "hasSupportCategory")]
#
#print(f"\nCalculando respuestas para (?, predicado, objeto): {queries_head[0]}")
#qa.calculate_answers(queries=queries_head, loader=loader, direction="head")
#ans_head = qa.get_answers(as_string=True)
#if ans_head:
#    print("Resultados encontrados:", ans_head[0])

# --- Ejemplo de uso ---
incidente_ejemplo = "incident_1497610379091762304042"

print(f"Resultados para {incidente_ejemplo} (filtrados):")
resultados = get_filtered_answers(incidente_ejemplo, "hasStateIncident")
for val, score in resultados:
    print(f" - {val}: {score}")