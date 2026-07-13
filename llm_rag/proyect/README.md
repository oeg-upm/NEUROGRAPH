
# LLM-RAG-Utils



Librería de las funcionalidades 

### generate_examples
Genera ’n’ frases de ejemplo combinando clientes y categorías de soporte extraídos aleatoriamente del grafo.

### find_examples

Procesa una lista de frases y las clasifica según las reglas que activan, dividiéndolas en solo ’df’, solo ’nv’, ambas o ninguna. Recoge hasta ’n’ ejemplos de cada caso y los devuelve en forma de lista.

### next_field_determinate
Completa el siguiente valor None de un array de longitud 6 correspondiente a la incidencia, usando el grafo y las reglas JSON, sin hacer uso del LLM. Toma como parámetros el array a completar y un parámetro opcional para llevar registro de la reglas que activa completar el siguiente atributo.

### next_field_llm
Completa el siguiente valor None de un array de 6 atributos correspondientes a la incidencia usando el grafo y las reglas JSON, haciendo uso del LLM para la lógica de comppletación. Además del array a completar se toma de parámetros de entrada el contexto y el modelo a usar.

### evaluate
Evalúa automáticamente un dataset JSON contra el sistema GraphRAG usando las métricas descritas en el siguiente capítulo. Toma de parámetros de entrada el contexto, el modelo, y como parámetros opcionales el nombre del fichero con el resultado de la evaluación y el directorio donde se guardará.

### chat_test
Inicia el modo 'chat', permitiendo que el usuario escriba por la terminal los dos primeros atributos de búsqueda y devolviendo por pantalla la incidencia con los 6 atributos completos, utilizando el completado del LLM para rellenar la incidencia. También como complemento se genera un log que resgistra la conversación. Toma de parámetros de entrada el contexto, el modelo y el directorio donde se guardarán los logs.


## Instalación

Colocarse en la ruta proyect y ejecutar el comando

```bash
pip install -e .
```

## Inicializacion

```python
import os
from openai import OpenAI, AsyncOpenAI
from tu_modulo_rag.chat import LLMChat

# 1. Definir parámetros de infraestructura externa
API_BASE_URL = "http://localhost:11434/v1"
API_KEY = "ollama"
MODELO_LLM = "llama3.1:70b"

# 2. Instanciar los clientes (síncrono y asíncrono obligatorio para procesamiento batch)
client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY, timeout=None)
async_client = AsyncOpenAI(base_url=API_BASE_URL, api_key=API_KEY, timeout=None)

# 3. Instanciar el asistente GraphRAG
chat_assistant = LLMChat(
    graph_file_path="incident_triplets_convertido.ttl",  # Grafo RDF
    rules_path="./textos/reglas_incidentes.json",        # Reglas JSON
    client=client,                                       # Inyección cliente síncrono
    async_client=async_client,                           # Inyección cliente asíncrono
    model_name=MODELO_LLM,                               # Nombre del modelo
    ttl_format="turtle"                                  # Formato del grafo (por defecto: turtle)
)
```
