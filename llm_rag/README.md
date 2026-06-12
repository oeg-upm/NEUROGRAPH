
# LLM-RAG




### Instalación y configuración

Clonar repositorio e instalar requirements.txt en un entorno virtual preferentemente.  



```bash
git clone https://github.com/oeg-upm/NEUROGRAPH.git
```

```bash
python3 -m venv venv
source venv/bin/activate
```

```bash
cd llm_rag
pip install -r requirements.txt
```


Con rdflib se analiza el conjunto de tripletas que se utiliza, que actualmente es el fichero llamado "filtrado.ttl", si se quiere utilizar otro o cambiar la ruta en el fichero de configuración.

Es importante que la carpeta 'textos' esté en el mismo directorio que chat o que en su defecto se actualicen las rutas en el código.

En la carpeta textos se encuentran las reglas en formato json. Si se quieren cambiar las reglas deben seguir el mismo formato del fichero.

En caso de usar un LLM asegurarse que se tiene instalado en modelo en local y que el nombre del modelo y el puerto del para accederlo sea el correcto. Por defecto se utiliza mistral con ollama. Si se quiere modificar cambiar el fichero config.py


### Pipeline


```
fichero_datos.ttl
        │
        ▼
┌───────────────────────────────────┐
│  Fase 1 — Creación del grafo      │  chat.py
│                                   │
└───────────────────────────────────┘
        │  
        ▼
┌───────────────────────────────────┐
│  Fase 2 — Análisis Input          │  ──▶ formatHelper.py
│  del usuario. Extracción campos   │  
└───────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────┐
│  Fase 3 — Generación de query del │ ──▶ searchInGraph.py
│  campo faltante. Consulta grafo   │ 
└───────────────────────────────────┘
        │ (generación valor nuevo con LLM) ──▶ contextoeval2.txt
        ├─────────────────────────────┐
        ▼                             ▼
┌─────────────────────┐   ┌─────────────────────────────┐
│  Fase 4a Aceptado   │   │  Fase 4b — ERROR si         │
│  Volver a 3         │   │  contradice regla nV        │
│  Si no hay más      │   │  Volver a generar con L     │
│  campos fin         │   │  segunda opción             │
│                     │   │                             │
└─────────────────────┘   └─────────────────────────────┘
        │
        ▼
┌────────────────────────────────┐
│ Fase 5                         │
│ Guardar conversación en logs   │ 
└────────────────────────────────┘
```




### Ejecución

Ejecutar el programa 'chatAIcompletion.py'.

Se podrá escribir por la terminal y se extraerán los datos de company y support category. El resto se irán rellenando automáticamente. El programa acabará cuando la query tenga todos los campos pertinentes.
