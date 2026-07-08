"""
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

            # ----------------------------------------------------------------------
            # BLOQUE 1 - Sin reglas (casos 1-10)
            # Ninguna condicion de las reglas df ni noValid se cumple.
            # ----------------------------------------------------------------------

            # Caso 1 · sin reglas
            (
                'Hola quiero completar una query. Tengo el supportCategory_149768521762302662 y la empresa company__R20114OGG',
                ['company__R20114OGG', 'supportCategory_149768521762302662', 'typeIncident__2', 'incidentOrigin__2', 'supportGroup_149761521762302662', 'employee__403']
            ),

            # Caso 2 · sin reglas
            (
                'Hola quiero completar una query. Tengo el supportCategory_149768521762302662 y la empresa company__S9KOXVH1M',
                ['company__S9KOXVH1M', 'supportCategory_149768521762302662', 'typeIncident__1', 'incidentOrigin__2', 'supportGroup_149761521762302662', 'employee__39']
            ),

            # Caso 3 · sin reglas
            (
                'Hola quiero completar una query. Tengo el supportCategory_1497610291762302662 y la empresa company__UPFP8CUEG',
                ['company__UPFP8CUEG', 'supportCategory_1497610291762302662', 'typeIncident__1', 'incidentOrigin__2', 'supportGroup_1497610301762302662', 'employee__239']
            ),

            # Caso 4 · sin reglas
            (
                'Hola quiero completar una query. Tengo el supportCategory_149761931762302662 y la empresa company__5B5JVGSPI',
                ['company__5B5JVGSPI', 'supportCategory_149761931762302662', 'typeIncident__1', 'incidentOrigin__2', 'supportGroup_149761941762302662', 'employee__601']
            ),

            # Caso 5 · sin reglas
            (
                'Hola quiero completar una query. Tengo el supportCategory_149767291231762303563 y la empresa company__USJTU0UB8',
                ['company__USJTU0UB8', 'supportCategory_149767291231762303563', 'typeIncident__1', 'incidentOrigin__2', 'supportGroup_149766077241762303391', 'employee__259']
            ),

            # Caso 6 · sin reglas
            (
                'Hola quiero completar una query. Tengo el supportCategory_149768010131762303673 y la empresa company__USJTU0UB8',
                ['company__USJTU0UB8', 'supportCategory_149768010131762303673', 'typeIncident__1', 'incidentOrigin__2', 'supportGroup_149766077241762303391', 'employee__170']
            ),

            # Caso 7 · sin reglas
            (
                'Hola quiero completar una query. Tengo el supportCategory_14976411762302662 y la empresa company__5B5JVGSPI',
                ['company__5B5JVGSPI', 'supportCategory_14976411762302662', 'typeIncident__1', 'incidentOrigin__2', 'supportGroup_149762761762302662', 'employee__294']
            ),

            # Caso 8 · sin reglas
            (
                'Hola quiero completar una query. Tengo el supportCategory_14976369491762302689 y la empresa company__Z78VDAP18',
                ['company__Z78VDAP18', 'supportCategory_14976369491762302689', 'typeIncident__1', 'incidentOrigin__2', 'supportGroup_149766077241762303391', 'employee__442']
            ),

            # Caso 9 · sin reglas
            (
                'Hola quiero completar una query. Tengo el supportCategory_14976251281762302678 y la empresa company__UVZ7OGD2N',
                ['company__UVZ7OGD2N', 'supportCategory_14976251281762302678', 'typeIncident__1', 'incidentOrigin__2', 'supportGroup_149762411762302662', 'employee__201']
            ),

            # Caso 10 · sin reglas
            (
                'Hola quiero completar una query. Tengo el supportCategory_14976110321762302666 y la empresa company__UPFP8CUEG',
                ['company__UPFP8CUEG', 'supportCategory_14976110321762302666', 'typeIncident__1', 'incidentOrigin__2', 'supportGroup_149761461762302662', 'employee__301']
            ),

            # ----------------------------------------------------------------------
            # BLOQUE 2 - Solo reglas df (casos 11-20)
            # Al menos una regla df se activa; ninguna noValid aplica.
            # ----------------------------------------------------------------------

            # Caso 11 · regla(s) df activa(s)
            # DF: incident_hasOrigin=incidentOrigin__3 -> hasSupportGroup=supportGroup_149762881762302662
            (
                'Hola quiero completar una query. Tengo el supportCategory_149766571762302662 y la empresa company__5RD32STIN',
                ['company__5RD32STIN', 'supportCategory_149766571762302662', 'typeIncident__1', 'incidentOrigin__3', 'supportGroup_149762611762302662', 'employee__23']
            ),

            # Caso 12 · regla(s) df activa(s)
            # DF: incident_hasOrigin=incidentOrigin__3 -> hasSupportGroup=supportGroup_149762881762302662
            (
                'Hola quiero completar una query. Tengo el supportCategory_149761881762302662 y la empresa company_149761700091762302830',
                ['company_149761700091762302830', 'supportCategory_149761881762302662', 'typeIncident__2', 'incidentOrigin__3', 'supportGroup_1497611281762302662', 'employee__294']
            ),

            # Caso 13 · regla(s) df activa(s)
            # DF: incident_hasOrigin=incidentOrigin__3 -> hasSupportGroup=supportGroup_149762881762302662
            (
                'Hola quiero completar una query. Tengo el supportCategory_149769391762302662 y la empresa company__7EKE6MKUEU6',
                ['company__7EKE6MKUEU6', 'supportCategory_149769391762302662', 'typeIncident__2', 'incidentOrigin__3', 'supportGroup_149762611762302662', 'employee__601']
            ),

            # Caso 14 · regla(s) df activa(s)
            # DF: incident_hasOrigin=incidentOrigin__3 -> hasSupportGroup=supportGroup_149762881762302662
            (
                'Hola quiero completar una query. Tengo el supportCategory_1497633831762302663 y la empresa company__HXQ7CXAM4',
                ['company__HXQ7CXAM4', 'supportCategory_1497633831762302663', 'typeIncident__1', 'incidentOrigin__3', 'supportGroup_149761661762302662', 'employee__437']
            ),

            # Caso 15 · regla(s) df activa(s)
            # DF: incident_hasOrigin=incidentOrigin__3 -> hasSupportGroup=supportGroup_149762881762302662
            (
                'Hola quiero completar una query. Tengo el supportCategory_149763371762302662 y la empresa company_14976254351762302678',
                ['company_14976254351762302678', 'supportCategory_149763371762302662', 'typeIncident__1', 'incidentOrigin__3', 'supportGroup_149761461762302662', 'employee__499']
            ),

            # Caso 16 · regla(s) df activa(s)
            # DF: incident_hasOrigin=incidentOrigin__3 -> hasSupportGroup=supportGroup_149762881762302662
            (
                'Hola quiero completar una query. Tengo el supportCategory_149763371762302662 y la empresa company__O3WHDQU0N',
                ['company__O3WHDQU0N', 'supportCategory_149763371762302662', 'typeIncident__1', 'incidentOrigin__3', 'supportGroup_149761461762302662', 'employee__301']
            ),

            # Caso 17 · regla(s) df activa(s)
            # DF: incident_hasOrigin=incidentOrigin__3 -> hasSupportGroup=supportGroup_149762881762302662
            (
                'Hola quiero completar una query. Tengo el supportCategory_1497691561762302665 y la empresa company__T0LI7ZR7L',
                ['company__T0LI7ZR7L', 'supportCategory_1497691561762302665', 'typeIncident__2', 'incidentOrigin__3', 'supportGroup_149761661762302662', 'employee__294']
            ),

            # Caso 18 · regla(s) df activa(s)
            # DF: incident_hasOrigin=incidentOrigin__3 -> hasSupportGroup=supportGroup_149762881762302662
            (
                'Hola quiero completar una query. Tengo el supportCategory_14976161441762302669 y la empresa company_14976254351762302678',
                ['company_14976254351762302678', 'supportCategory_14976161441762302669', 'typeIncident__2', 'incidentOrigin__3', 'supportGroup_14976161451762302669', 'employee__246']
            ),

            # Caso 19 · regla(s) df activa(s)
            # DF: incident_hasOrigin=incidentOrigin__3 -> hasSupportGroup=supportGroup_149762881762302662
            (
                'Hola quiero completar una query. Tengo el supportCategory_149761881762302662 y la empresa company_149762803341762302960',
                ['company_149762803341762302960', 'supportCategory_149761881762302662', 'typeIncident__2', 'incidentOrigin__3', 'supportGroup_149768471762302662', 'employee__511']
            ),

            # Caso 20 · regla(s) df activa(s)
            # DF: incident_hasOrigin=incidentOrigin__3 -> hasSupportGroup=supportGroup_149762881762302662
            (
                'Hola quiero completar una query. Tengo el supportCategory_149763629331762303060 y la empresa company_149762803341762302960',
                ['company_149762803341762302960', 'supportCategory_149763629331762303060', 'typeIncident__2', 'incidentOrigin__3', 'supportGroup_149762881762302662', 'employee__294']
            ),

            # ----------------------------------------------------------------------
            # BLOQUE 3 - Solo reglas noValid (casos 21-30)
            # Al menos una regla noValid se activa; ninguna df aplica.
            # ----------------------------------------------------------------------

            # Caso 21 · regla(s) noValid activa(s)
            # NV: incident_hasOrigin=incidentOrigin__1 -> hasTypeInc!=typeIncident__1
            (
                'Hola quiero completar una query. Tengo el supportCategory_149764053791762303121 y la empresa company__KJ6N5XI2A',
                ['company__KJ6N5XI2A', 'supportCategory_149764053791762303121', 'typeIncident__1', 'incidentOrigin__1', 'supportGroup_149761521762302662', 'employee__482']
            ),

            # Caso 22 · regla(s) noValid activa(s)
            # NV: incident_hasOrigin=incidentOrigin__1 -> hasTypeInc!=typeIncident__1
            (
                'Hola quiero completar una query. Tengo el supportCategory_149764053791762303121 y la empresa company__KJ6N5XI2A',
                ['company__KJ6N5XI2A', 'supportCategory_149764053791762303121', 'typeIncident__1', 'incidentOrigin__1', 'supportGroup_149761521762302662', 'employee__482']
            ),

            # Caso 23 · regla(s) noValid activa(s)
            # NV: hasSupportTeam=supportTeam_149762304211762302899 -> hasSupportCategory!=supportCategory_149763514921762303044
            (
                'Hola quiero completar una query. Tengo el supportCategory_149767060481762303533 y la empresa company__5B5JVGSPI',
                ['company__5B5JVGSPI', 'supportCategory_149767060481762303533', 'typeIncident__1', 'incidentOrigin__2', 'supportGroup_149765457361762303308', 'employee__429']
            ),

            # Caso 24 · regla(s) noValid activa(s)
            # NV: incident_hasOrigin=incidentOrigin__1 -> hasTypeInc!=typeIncident__1
            (
                'Hola quiero completar una query. Tengo el supportCategory_14976411762302662 y la empresa company__5B5JVGSPI',
                ['company__5B5JVGSPI', 'supportCategory_14976411762302662', 'typeIncident__1', 'incidentOrigin__1', 'supportGroup_149762761762302662', 'employee__294']
            ),

            # Caso 25 · regla(s) noValid activa(s)
            # NV: incident_hasOrigin=incidentOrigin__1 -> hasTypeInc!=typeIncident__1
            (
                'Hola quiero completar una query. Tengo el supportCategory_149761591762302662 y la empresa company__5B5JVGSPI',
                ['company__5B5JVGSPI', 'supportCategory_149761591762302662', 'typeIncident__2', 'incidentOrigin__1', 'supportGroup_149762921762302662', 'employee__294']
            ),

            # Caso 26 · regla(s) noValid activa(s)
            # NV: hasSupportTeam=supportTeam_149762304211762302899 -> hasSupportCategory!=supportCategory_149763514921762303044
            (
                'Hola quiero completar una query. Tengo el supportCategory_149767060481762303533 y la empresa company__5B5JVGSPI',
                ['company__5B5JVGSPI', 'supportCategory_149767060481762303533', 'typeIncident__1', 'incidentOrigin__2', 'supportGroup_149765457361762303308', 'employee__430']
            ),

            # Caso 27 · regla(s) noValid activa(s)
            # NV: hasSupportTeam=supportTeam_149762304211762302899 -> hasSupportCategory!=supportCategory_149763514921762303044
            (
                'Hola quiero completar una query. Tengo el supportCategory_149767060481762303533 y la empresa company__5B5JVGSPI',
                ['company__5B5JVGSPI', 'supportCategory_149767060481762303533', 'typeIncident__1', 'incidentOrigin__2', 'supportGroup_149765457361762303308', 'employee__430']
            ),

            # Caso 28 · regla(s) noValid activa(s)
            # NV: incident_hasOrigin=incidentOrigin__1 -> hasTypeInc!=typeIncident__1
            (
                'Hola quiero completar una query. Tengo el supportCategory_149761511762302662 y la empresa company__O8AK2SY1E',
                ['company__O8AK2SY1E', 'supportCategory_149761511762302662', 'typeIncident__2', 'incidentOrigin__1', 'supportGroup_149761521762302662', 'employee__39']
            ),

            # Caso 29 · regla(s) noValid activa(s)
            # NV: hasSupportTeam=supportTeam_149762304211762302899 -> hasSupportCategory!=supportCategory_149763514921762303044
            (
                'Hola quiero completar una query. Tengo el supportCategory_14976149461762302668 y la empresa company__UPFP8CUEG',
                ['company__UPFP8CUEG', 'supportCategory_14976149461762302668', 'typeIncident__1', 'incidentOrigin__2', 'supportGroup_1497611281762302662', 'employee__432']
            ),

            # Caso 30 · regla(s) noValid activa(s)
            # NV: incident_hasOrigin=incidentOrigin__1 -> hasTypeInc!=typeIncident__1
            (
                'Hola quiero completar una query. Tengo el supportCategory_149763471762302662 y la empresa company__5B5JVGSPI',
                ['company__5B5JVGSPI', 'supportCategory_149763471762302662', 'typeIncident__2', 'incidentOrigin__1', 'supportGroup_149763481762302662', 'employee__636']
            ),

            # ----------------------------------------------------------------------
            # BLOQUE 4 - Ambas reglas sin contradiccion (casos 31-40)
            # Reglas df y noValid se activan, sobre predicados distintos.
            # ----------------------------------------------------------------------

            # Caso 31 · df + noValid sin contradiccion
            # DF: int_hasCustomer=ss -> hasStateIncident=statusIncident__2
            # DF: int_hasCustomer=ss + hasTypeInc=typeIncident__1 -> hasSupportGroup=supportGroup_14976691762302662
            # NV: int_hasCustomer=ss -> incident_hasOrigin!=incidentOrigin__1
            (
                'Hola quiero completar una query. Tengo el supportCategory_14976256531762302678 y la empresa ss',
                ['ss', 'supportCategory_14976256531762302678', 'typeIncident__1', 'incidentOrigin__2', 'supportGroup_14976212821762302676', 'employee__439']
            ),

            # Caso 32 · df + noValid sin contradiccion
            # DF: incident_hasOrigin=incidentOrigin__3 -> hasSupportGroup=supportGroup_149762881762302662
            # NV: hasSupportTeam=supportTeam_149762304211762302899 -> hasSupportCategory!=supportCategory_149763514921762303044
            (
                'Hola quiero completar una query. Tengo el supportCategory_149762111762302662 y la empresa company__5RD32STIN',
                ['company__5RD32STIN', 'supportCategory_149762111762302662', 'typeIncident__2', 'incidentOrigin__3', 'supportGroup_149762611762302662', 'employee__487']
            ),

            # Caso 33 · df + noValid sin contradiccion
            # DF: int_hasCustomer=ss -> hasStateIncident=statusIncident__2
            # DF: int_hasCustomer=ss + hasTypeInc=typeIncident__1 -> hasSupportGroup=supportGroup_14976691762302662
            # NV: int_hasCustomer=ss -> incident_hasOrigin!=incidentOrigin__1
            (
                'Hola quiero completar una query. Tengo el supportCategory_1497673211762302665 y la empresa ss',
                ['ss', 'supportCategory_1497673211762302665', 'typeIncident__1', 'incidentOrigin__2', 'supportGroup_149761521762302662', 'employee__403']
            ),

            # Caso 34 · df + noValid sin contradiccion
            # DF: int_hasCustomer=ss -> hasStateIncident=statusIncident__2
            # DF: int_hasCustomer=ss + hasTypeInc=typeIncident__1 -> hasSupportGroup=supportGroup_14976691762302662
            # NV: int_hasCustomer=ss -> incident_hasOrigin!=incidentOrigin__1
            (
                'Hola quiero completar una query. Tengo el supportCategory_1497644851762302663 y la empresa ss',
                ['ss', 'supportCategory_1497644851762302663', 'typeIncident__1', 'incidentOrigin__2', 'supportGroup_149761661762302662', 'employee__442']
            ),

            # Caso 35 · df + noValid sin contradiccion
            # DF: int_hasCustomer=ss -> hasStateIncident=statusIncident__2
            # DF: int_hasCustomer=ss + hasTypeInc=typeIncident__1 -> hasSupportGroup=supportGroup_14976691762302662
            # NV: int_hasCustomer=ss -> incident_hasOrigin!=incidentOrigin__1
            (
                'Hola quiero completar una query. Tengo el supportCategory_14976212811762302676 y la empresa ss',
                ['ss', 'supportCategory_14976212811762302676', 'typeIncident__1', 'incidentOrigin__2', 'supportGroup_14976212821762302676', 'employee__108']
            ),

            # Caso 36 · df + noValid sin contradiccion
            # DF: int_hasCustomer=ss -> hasStateIncident=statusIncident__2
            # DF: int_hasCustomer=ss + hasTypeInc=typeIncident__1 -> hasSupportGroup=supportGroup_14976691762302662
            # NV: int_hasCustomer=ss -> incident_hasOrigin!=incidentOrigin__1
            (
                'Hola quiero completar una query. Tengo el supportCategory_14976212811762302676 y la empresa ss',
                ['ss', 'supportCategory_14976212811762302676', 'typeIncident__1', 'incidentOrigin__2', 'supportGroup_14976212821762302676', 'employee__171']
            ),

            # Caso 37 · df + noValid sin contradiccion
            # DF: int_hasCustomer=ss -> hasStateIncident=statusIncident__2
            # DF: int_hasCustomer=ss + hasTypeInc=typeIncident__1 -> hasSupportGroup=supportGroup_14976691762302662
            # NV: int_hasCustomer=ss -> incident_hasOrigin!=incidentOrigin__1
            (
                'Hola quiero completar una query. Tengo el supportCategory_14976212811762302676 y la empresa ss',
                ['ss', 'supportCategory_14976212811762302676', 'typeIncident__1', 'incidentOrigin__2', 'supportGroup_14976212821762302676', 'employee__241']
            ),

            # Caso 38 · df + noValid sin contradiccion
            # DF: int_hasCustomer=ss -> hasStateIncident=statusIncident__2
            # DF: int_hasCustomer=ss + hasTypeInc=typeIncident__1 -> hasSupportGroup=supportGroup_14976691762302662
            # NV: int_hasCustomer=ss -> incident_hasOrigin!=incidentOrigin__1
            (
                'Hola quiero completar una query. Tengo el supportCategory_14976212811762302676 y la empresa ss',
                ['ss', 'supportCategory_14976212811762302676', 'typeIncident__1', 'incidentOrigin__2', 'supportGroup_14976212821762302676', 'employee__266']
            ),

            # Caso 39 · df + noValid sin contradiccion
            # DF: int_hasCustomer=ss -> hasStateIncident=statusIncident__2
            # DF: int_hasCustomer=ss + hasTypeInc=typeIncident__1 -> hasSupportGroup=supportGroup_14976691762302662
            # NV: int_hasCustomer=ss -> incident_hasOrigin!=incidentOrigin__1
            (
                'Hola quiero completar una query. Tengo el supportCategory_14976212811762302676 y la empresa ss',
                ['ss', 'supportCategory_14976212811762302676', 'typeIncident__1', 'incidentOrigin__2', 'supportGroup_14976212821762302676', 'employee__171']
            ),

            # Caso 40 · df + noValid sin contradiccion
            # DF: int_hasCustomer=ss -> hasStateIncident=statusIncident__2
            # DF: int_hasCustomer=ss + hasTypeInc=typeIncident__1 -> hasSupportGroup=supportGroup_14976691762302662
            # NV: int_hasCustomer=ss -> incident_hasOrigin!=incidentOrigin__1
            (
                'Hola quiero completar una query. Tengo el supportCategory_14976212811762302676 y la empresa ss',
                ['ss', 'supportCategory_14976212811762302676', 'typeIncident__1', 'incidentOrigin__2', 'supportGroup_14976212821762302676', 'employee__241']
            ),

            # ----------------------------------------------------------------------
            # BLOQUE 5 - Reglas contradictorias (casos 41-50)
            # Una regla df y una regla noValid actuan sobre el mismo
            # predicado con valores distintos -> contradiccion directa.
            # ----------------------------------------------------------------------

            # Caso 41 · df y noValid contradictorias
            # DF: incident_hasOrigin=incidentOrigin__4 -> hasTypeInc=typeIncident__1
            # NV: incident_hasOrigin=incidentOrigin__4 -> hasTypeInc!=typeIncident__2
            # NV: hasSupportTeam=supportTeam_149762304211762302899 -> hasSupportCategory!=supportCategory_149763514921762303044
            (
                'Hola quiero completar una query. Tengo el supportCategory_149763471762302662 y la empresa company__5B5JVGSPI',
                ['company__5B5JVGSPI', 'supportCategory_149763471762302662', 'typeIncident__1', 'incidentOrigin__4', 'supportGroup_149763481762302662', 'employee__430']
            ),

            # Caso 42 · df y noValid contradictorias
            # DF: incident_hasOrigin=incidentOrigin__4 -> hasTypeInc=typeIncident__1
            # NV: incident_hasOrigin=incidentOrigin__4 -> hasTypeInc!=typeIncident__2
            # NV: hasSupportTeam=supportTeam_149762304211762302899 -> hasSupportCategory!=supportCategory_149763514921762303044
            (
                'Hola quiero completar una query. Tengo el supportCategory_149763471762302662 y la empresa company__5B5JVGSPI',
                ['company__5B5JVGSPI', 'supportCategory_149763471762302662', 'typeIncident__1', 'incidentOrigin__4', 'supportGroup_149763481762302662', 'employee__432']
            ),

            # Caso 43 · df y noValid contradictorias
            # DF: incident_hasOrigin=incidentOrigin__4 -> hasTypeInc=typeIncident__1
            # NV: incident_hasOrigin=incidentOrigin__4 -> hasTypeInc!=typeIncident__2
            (
                'Hola quiero completar una query. Tengo el supportCategory_149761931762302662 y la empresa company__FVIY67KB2',
                ['company__FVIY67KB2', 'supportCategory_149761931762302662', 'typeIncident__1', 'incidentOrigin__4', 'supportGroup_149761941762302662', 'employee__343']
            ),

            # Caso 44 · df y noValid contradictorias
            # DF: incident_hasOrigin=incidentOrigin__4 -> hasTypeInc=typeIncident__1
            # NV: incident_hasOrigin=incidentOrigin__4 -> hasTypeInc!=typeIncident__2
            (
                'Hola quiero completar una query. Tengo el supportCategory_149761591762302662 y la empresa company__5B5JVGSPI',
                ['company__5B5JVGSPI', 'supportCategory_149761591762302662', 'typeIncident__2', 'incidentOrigin__4', 'supportGroup_149762921762302662', 'employee__246']
            ),

            # Caso 45 · df y noValid contradictorias
            # DF: incident_hasOrigin=incidentOrigin__4 -> hasTypeInc=typeIncident__1
            # DF: int_hasCustomer=ss -> hasStateIncident=statusIncident__2
            # NV: incident_hasOrigin=incidentOrigin__4 -> hasTypeInc!=typeIncident__2
            # NV: int_hasCustomer=ss -> incident_hasOrigin!=incidentOrigin__1
            (
                'Hola quiero completar una query. Tengo el supportCategory_1497610028831762303986 y la empresa ss',
                ['ss', 'supportCategory_1497610028831762303986', 'typeIncident__2', 'incidentOrigin__4', 'supportGroup_14976212821762302676', 'employee__631']
            ),

            # Caso 46 · df y noValid contradictorias
            # DF: incident_hasOrigin=incidentOrigin__4 -> hasTypeInc=typeIncident__1
            # DF: int_hasCustomer=ss -> hasStateIncident=statusIncident__2
            # NV: incident_hasOrigin=incidentOrigin__4 -> hasTypeInc!=typeIncident__2
            # NV: int_hasCustomer=ss -> incident_hasOrigin!=incidentOrigin__1
            (
                'Hola quiero completar una query. Tengo el supportCategory_1497610028831762303986 y la empresa ss',
                ['ss', 'supportCategory_1497610028831762303986', 'typeIncident__2', 'incidentOrigin__4', 'supportGroup_14976212821762302676', 'employee__631']
            ),

            # Caso 47 · df y noValid contradictorias
            # DF: incident_hasOrigin=incidentOrigin__4 -> hasTypeInc=typeIncident__1
            # NV: incident_hasOrigin=incidentOrigin__4 -> hasTypeInc!=typeIncident__2
            # NV: hasSupportTeam=supportTeam_149762304211762302899 -> hasSupportCategory!=supportCategory_149763514921762303044
            (
                'Hola quiero completar una query. Tengo el supportCategory_149763471762302662 y la empresa company__5B5JVGSPI',
                ['company__5B5JVGSPI', 'supportCategory_149763471762302662', 'typeIncident__1', 'incidentOrigin__4', 'supportGroup_149763481762302662', 'employee__487']
            ),

            # Caso 48 · df y noValid contradictorias
            # DF: incident_hasOrigin=incidentOrigin__4 -> hasTypeInc=typeIncident__1
            # DF: int_hasCustomer=ss -> hasStateIncident=statusIncident__2
            # NV: incident_hasOrigin=incidentOrigin__4 -> hasTypeInc!=typeIncident__2
            # NV: int_hasCustomer=ss -> incident_hasOrigin!=incidentOrigin__1
            (
                'Hola quiero completar una query. Tengo el supportCategory_1497610028831762303986 y la empresa ss',
                ['ss', 'supportCategory_1497610028831762303986', 'typeIncident__2', 'incidentOrigin__4', 'supportGroup_14976212821762302676', 'employee__631']
            ),

            # Caso 49 · df y noValid contradictorias
            # DF: incident_hasOrigin=incidentOrigin__4 -> hasTypeInc=typeIncident__1
            # NV: incident_hasOrigin=incidentOrigin__4 -> hasTypeInc!=typeIncident__2
            # NV: hasSupportTeam=supportTeam_149762304211762302899 -> hasSupportCategory!=supportCategory_149763514921762303044
            (
                'Hola quiero completar una query. Tengo el supportCategory_149763471762302662 y la empresa company__5B5JVGSPI',
                ['company__5B5JVGSPI', 'supportCategory_149763471762302662', 'typeIncident__1', 'incidentOrigin__4', 'supportGroup_149763481762302662', 'employee__486']
            ),

            # Caso 50 · df y noValid contradictorias
            # DF: incident_hasOrigin=incidentOrigin__4 -> hasTypeInc=typeIncident__1
            # DF: int_hasCustomer=ss -> hasStateIncident=statusIncident__2
            # NV: incident_hasOrigin=incidentOrigin__4 -> hasTypeInc!=typeIncident__2
            # NV: int_hasCustomer=ss -> incident_hasOrigin!=incidentOrigin__1
            (
                'Hola quiero completar una query. Tengo el supportCategory_1497610028831762303986 y la empresa ss',
                ['ss', 'supportCategory_1497610028831762303986', 'typeIncident__2', 'incidentOrigin__4', 'supportGroup_14976212821762302676', 'employee__631']
            ),

        ]

    def test_sin_reglas(self):
        """Casos 1-10: ninguna regla df ni noValid activa."""
        print("Casos 1-10: ninguna regla df ni noValid activa.")
        for i, (query, expected) in enumerate(self.casos_de_prueba[:10], start=1):
            with self.subTest(caso=i, query=query):
                result = procesar_query(query)
                self.assertEqual(
                    result, expected,
                    msg=f"Caso {i} fallido.\nQuery: {query}\nEsperado: {expected}\nObtenido: {result}"
                )

    def test_reglas_df(self):
        """Casos 11-20: solo reglas df se activan."""
        print("Casos 11-20: solo reglas df se activan.")
        for i, (query, expected) in enumerate(self.casos_de_prueba[10:20], start=11):
            with self.subTest(caso=i, query=query):
                result = procesar_query(query)
                self.assertEqual(
                    result, expected,
                    msg=f"Caso {i} fallido.\nQuery: {query}\nEsperado: {expected}\nObtenido: {result}"
                )

    def test_reglas_novalid(self):
        """Casos 21-30: solo reglas noValid se activan."""
        print("Casos 21-30: solo reglas noValid se activan.")
        for i, (query, expected) in enumerate(self.casos_de_prueba[20:30], start=21):
            with self.subTest(caso=i, query=query):
                result = procesar_query(query)
                self.assertEqual(
                    result, expected,
                    msg=f"Caso {i} fallido.\nQuery: {query}\nEsperado: {expected}\nObtenido: {result}"
                )

    def test_ambas_reglas(self):
        """Casos 31-40: reglas df y noValid se activan sin contradiccion."""
        print("Casos 31-40: reglas df y noValid se activan sin contradiccion.")
        for i, (query, expected) in enumerate(self.casos_de_prueba[30:40], start=31):
            with self.subTest(caso=i, query=query):
                result = procesar_query(query)
                self.assertEqual(
                    result, expected,
                    msg=f"Caso {i} fallido.\nQuery: {query}\nEsperado: {expected}\nObtenido: {result}"
                )

    def test_reglas_contradictorias(self):
        """Casos 41-50: df y noValid se contradicen sobre el mismo predicado."""
        print("Casos 41-50: df y noValid se contradicen sobre el mismo predicado.")
        for i, (query, expected) in enumerate(self.casos_de_prueba[40:50], start=41):
            with self.subTest(caso=i, query=query):
                result = procesar_query(query)
                self.assertEqual(
                    result, expected,
                    msg=f"Caso {i} fallido.\nQuery: {query}\nEsperado: {expected}\nObtenido: {result}"
                )


if __name__ == "__main__":
    unittest.main(argv=[""], verbosity=2, exit=False)
