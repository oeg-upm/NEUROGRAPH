# NEUROGRAPH
Implementación de los módulos de recomendación desarrollados. Se han desarrollado dos módulos diferentes para generar el sistema de configuración:

## LLM-RAG

Utiliza el grafo existente como un elemento de consulta, sobre el cual el usuario mediante una interfaz conversacional puede indicar los valores de los campos a configurar. La documentación y el código de este módulo se aloja en la carpeta _llm_rag_

## LLM-KGE

Implementa un sistema neurosimbólico end-to-end, empleando una inferencia en cascada donde se prioriza siempre el modelo de mayor fiabilidad (las reglas) y, en caso de que estas no arrojen respuesta, se pasa a un segundo nivel donde se emplea una combinación de un modelo de razonamiento basado en casos junto con un modelo de _embeddings_, permitiendo que siempre se genere al menos una respuesta y que cada respuesta sea trazable.

La información de este método y el código para su ejecución está desarrollado en la carpeta _llm_kge_

## ‼️INFORMACIÓN IMPORTANTE
En ambas aproximaciones, se recibe como entrada el fichero _filtrado.ttl_ que contiene las tripletas proporcionadas. Este fichero debe ser proporcionado por el usuario, ya que se ha omitido deliberadamente de este repositorio por motivos de confidencialidad. 

En caso de existir un fichero de reglas compatible con PyClause, este se podrá incluir como entrada al sistema de _llm_kge_. En caso de no proporcionarse reglas, estas serán inferidas a partir de los hechos usando la aproximación [AnyBurl](https://web.informatik.uni-mannheim.de/AnyBURL/#run)






