
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


En caso de usar un LLM asegurarse que se tiene instalado en modelo en local y que el nombre del modelo y el puerto del para accederlo sea el correcto. Por defecto se utiliza mistral con ollama. Si se quiere modificar cambiar el fichero config.py


### Pipeline


```
filtrado.ttl
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
        │ (+verbalización pregunta) ──▶ contexto.txt
        ├─────────────────────────────┐
        ▼                             ▼
┌─────────────────────┐   ┌─────────────────────────────┐
│  Fase 4a Aceptado   │   │  Fase 4b — Negado por user  │
│  Volver a 3         │   │                             │
│  Si no hay más      │   │  Generar query PARCIAL      │
│  campos fin         │   │  Consultar usuario          │
│                     │   │  nuevamente hasta aceptar   │
└─────────────────────┘   └─────────────────────────────┘
        │
        ▼
┌────────────────────────────────┐
│ Fase 5                         │
│ Guardar conversación en logs   │ 
└────────────────────────────────┘
```




### Ejecución

Ejecutar el programa 'chat.py'.

Ir completando la query marcando las opciones como se plantean por pantalla. El programa acabará cuando la query tenga todos los campos pertinentes.
