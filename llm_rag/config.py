import os
from openai import OpenAI, AsyncOpenAI

# ==========================================
# CONFIGURACIÓN DEL GRAFO (RDF / GraphRAG)
# ==========================================
TTL_FILE_PATH = "incident_triplets_convertido.ttl"
#TTL_FILE_PATH = "filtrado.ttl"
TTL_FORMAT = "turtle"

# ==========================================
# CONFIGURACIÓN DEL MODELO DE LENGUAJE (LLM)
# ==========================================
#MI_MODELO = "llama3.1:70b"
MI_MODELO = "llama3"
# Configuración del cliente API (Ollama local o servicios en la nube)
#"http://localhost:11434/v1"
API_BASE_URL = "http://localhost:11434/v1"

API_KEY = "ollama"

# Inicialización del cliente de OpenAI
client = OpenAI(
    base_url=API_BASE_URL,
    api_key=API_KEY,
    timeout=None
)

async_client = AsyncOpenAI(
    base_url=API_BASE_URL,
    api_key=API_KEY,
    timeout=None
)

# Configuración de reintentos para la generación de texto
MAX_RETRIES = 5
RETRY_DELAY_SECONDS = 1

# ==========================================
# CONFIGURACIÓN DE RUTAS Y LOGS
# ==========================================
LOGS_DIR = os.path.join("textos", "logs")
CONTEXTO_FILE_PATH = os.path.join("textos", "contextoeval2.txt")

# ==========================================
# DICCIONARIOS Y PARÁMETROS DEL ASISTENTE
# ==========================================
DICCIONARIO_PREDICADOS = {
    0: "int_hasCustomer",
    1: "hasSupportCategory",  
    2: "hasTypeInc",
    3: "incident_hasOrigin",
    4: "hasSupportGroup",
    5: "hasTechnician"
}

DICCIONARIO_PREFIJOS = {
    0: "company",         
    1: "supportCategory", 
    2: "typeIncident",    
    3: "incidentOrigin",  
    4: "supportGroup",    
    5: "employee"         
}