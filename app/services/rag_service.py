import os
import pandas as pd
import re
from dotenv import load_dotenv
from llama_index.core import (
    VectorStoreIndex, 
    SimpleDirectoryReader, 
    Settings,
)
from llama_index.llms.gemini import Gemini
from llama_index.embeddings.gemini import GeminiEmbedding
from llama_index.experimental.query_engine import PandasQueryEngine
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.core.query_engine import RouterQueryEngine
from llama_index.core.selectors import LLMSingleSelector
from llama_index.core.readers.base import BaseReader
from llama_index.core.schema import Document
import PIL.Image
import google.generativeai as genai

load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=API_KEY)
Settings.llm = Gemini(api_key=API_KEY, model_name="models/gemini-2.5-flash-lite")
Settings.embed_model = GeminiEmbedding(api_key=API_KEY, model_name="models/gemini-embedding-001")

RAW_FILES_DIR = "./data_storage/raw_files"

class GeminiImageReader(BaseReader):
    """Lector personalizado que usa Gemini Vision en lugar de Tesseract"""
    def load_data(self, file, extra_info=None):
        try:
            print(f"Gemini está leyendo la imagen: {file}")
            img = PIL.Image.open(file)
            model = genai.GenerativeModel('models/gemini-2.5-flash-lite') 
            
            prompt = "Extrae todo el texto de esta imagen de forma estructurada. Incluye fechas, requisitos, promedios y lugares exactamente como aparecen."
            response = model.generate_content([prompt, img])
            return [Document(text=response.text, extra_info=extra_info or {})]
        except Exception as e:
            print(f"Error leyendo imagen con Gemini: {e}")
            return []

class UTTECBrain:
    def __init__(self):
        self.router_engine = None
        self.df_estudiantes = None
        self.initialize_brain()

    def initialize_brain(self):
        print("🔄 Sincronizando base de conocimientos...")
        
        if not os.path.exists(RAW_FILES_DIR):
            os.makedirs(RAW_FILES_DIR)

        tools = []
        archivos_en_carpeta = os.listdir(RAW_FILES_DIR)

        try:
            image_reader = GeminiImageReader()
            
            file_extractor = {
                ".jpg": image_reader,
                ".png": image_reader,
                ".jpeg": image_reader,
            }

            documents = SimpleDirectoryReader(
                RAW_FILES_DIR, 
                exclude=["*.csv"],
                file_extractor=file_extractor
            ).load_data()

            if documents:
                vector_index = VectorStoreIndex.from_documents(documents)
                vector_engine = vector_index.as_query_engine(similarity_top_k=3)
                tools.append(QueryEngineTool(
                    query_engine=vector_engine,
                    metadata=ToolMetadata(
                        name="documentos_institucionales",
                        description="Reglamentos, becas, intercambio, movilidad al extranjero, fechas, convocatorias y avisos."
                    )
                ))
        except Exception as e:
            print(f"Info Motor Vectorial: No se encontraron PDFs/TXTs/Imágenes o hubo un detalle: {e}")
        archivos_csv = [f for f in archivos_en_carpeta if f.endswith('.csv')]
        if archivos_csv:
            try:
                csv_path = os.path.join(RAW_FILES_DIR, archivos_csv[0])
                if os.path.getsize(csv_path) > 0:
                    df = pd.read_csv(csv_path)
                    self.df_estudiantes = df  # NUEVO: guardar referencia
                    
                    if 'Matricula' in df.columns:
                        df['Matricula'] = df['Matricula'].astype(str).str.strip()
                        
                    if not df.empty:
                        instruccion_pandas = (
                            "Eres un experto en Python y Pandas. Tu única tarea es generar código para filtrar el dataframe 'df'.\n"
                            "COLUMNAS REALES DISPONIBLES: ['Matricula', 'Nombre del Alumno', 'Grupo Ingles', 'Docente', 'Horario', 'Salon', 'Codigo Classroom', 'Codigo Oxford', 'Grado', 'Nivel'].\n"
                            "REGLAS OBLIGATORIAS:\n"
                            "1. NO USES 'grupo_code', 'group_code' ni ningún otro nombre inventado.\n"
                            "2. Si buscas el grupo, usa ÚNICAMENTE 'Grupo Ingles'.\n"
                            "3. Si la columna no existe exactamente como se escribió, responde: 'COLUMNA_NO_EXISTE'.\n"
                            "4. Si no hay coincidencias, responde: 'SIN_RESULTADOS'.\n"
                            "5. Nunca inventes datos. Solo retorna lo que existe en el dataframe.\n"
                            "6. Si hay 'N/A' o 'No asignado', inclúyelo tal cual."
                        )

                        pandas_engine = PandasQueryEngine(
                            df=df, 
                            verbose=False, 
                            synthesize_response=False,
                            instruction_str=instruccion_pandas
                        )
                        
                        tools.append(QueryEngineTool(
                            query_engine=pandas_engine,
                            metadata=ToolMetadata(
                                name="listas_estudiantes",
                                description="Datos de alumnos: Matricula, Nombre, Grupo Ingles, Docente, Horario, Salon."
                            )
                        ))
            except Exception as e:
                print(f"Error cargando el archivo CSV: {e}")

        if tools:
            self.router_engine = RouterQueryEngine(
                selector=LLMSingleSelector.from_defaults(),
                query_engine_tools=tools
            )
            print("Cerebro actualizado y listo.")
        else:
            self.router_engine = None
            print("El cerebro está vivo, pero no tiene documentos para leer.")
    def buscar_en_csv(self, criterio: str, valor: str) -> dict:
        """
        Búsqueda directa en el CSV sin usar LLM.
        criterio: 'matricula', 'nombre', 'grupo'
        valor: valor a buscar
        """
        if self.df_estudiantes is None:
            return {"encontrado": False, "datos": None, "mensaje": "Base de datos no disponible"}
        
        try:
            valor_normalizado = str(valor).strip().upper()
            
            if criterio.lower() == 'matricula':
                resultado = self.df_estudiantes[
                    self.df_estudiantes['Matricula'].astype(str).str.strip() == valor_normalizado
                ]
            elif criterio.lower() == 'nombre':
                resultado = self.df_estudiantes[
                    self.df_estudiantes['Nombre del Alumno'].str.upper().str.contains(valor_normalizado, na=False)
                ]
            elif criterio.lower() == 'grupo':
                resultado = self.df_estudiantes[
                    self.df_estudiantes['Grupo Ingles'].str.upper().str.strip() == valor_normalizado
                ]
            else:
                return {"encontrado": False, "datos": None, "mensaje": "Criterio no válido"}
            
            if resultado.empty:
                return {"encontrado": False, "datos": None, "mensaje": f"No se encontraron resultados para {criterio}: {valor}"}
            datos = resultado.to_dict('records')
            for registro in datos:
                for key, val in registro.items():
                    if pd.isna(val):
                        registro[key] = "No asignado"
                    elif str(val).lower() == 'n/a':
                        registro[key] = "No asignado"
            
            return {
                "encontrado": True,
                "datos": datos,
                "cantidad": len(datos),
                "mensaje": None
            }
        
        except Exception as e:
            return {"encontrado": False, "datos": None, "mensaje": f"Error en búsqueda: {str(e)}"}


brain = UTTECBrain()
memoria_sesiones = {}


def _extraer_matricula_de_contexto(pregunta: str, historial: str) -> str:
    """NUEVA FUNCIÓN: Extrae matrícula de pregunta o historial"""
    patron = r'\b\d{10}\b'
    
    coincidencias_pregunta = re.findall(patron, pregunta)
    if coincidencias_pregunta:
        return coincidencias_pregunta[0]
    
    coincidencias_historial = re.findall(patron, historial)
    if coincidencias_historial:
        return coincidencias_historial[-1]
    
    return None

def buscar_informacion(pregunta: str, usuario_id: str, prompt_maestro: str):
    """Maneja la lógica de la sesión y la respuesta inteligente."""
    if usuario_id not in memoria_sesiones:
        memoria_sesiones[usuario_id] = {
            "historial": [],
            "estudiante_datos": None,
            "nombre_alumno": None
        }
    sesion = memoria_sesiones[usuario_id]
    if not sesion["estudiante_datos"]:
        matricula = _extraer_matricula_de_contexto(pregunta, str(sesion["historial"]))
        
        if matricula:
            resultado = brain.buscar_en_csv('matricula', matricula)
            if resultado["encontrado"]:
                sesion["estudiante_datos"] = resultado["datos"][0]
                sesion["nombre_alumno"] = sesion["estudiante_datos"]["Nombre del Alumno"]
        else:
            if len(pregunta.split()) >= 2: 
                resultado = brain.buscar_en_csv('nombre', pregunta)
                if resultado["encontrado"] and resultado["cantidad"] == 1:
                    sesion["estudiante_datos"] = resultado["datos"][0]
                    sesion["nombre_alumno"] = sesion["estudiante_datos"]["Nombre del Alumno"]

    if sesion["estudiante_datos"]:
        contexto_datos = "DATOS DEL ALUMNO IDENTIFICADO:\n"
        for k, v in sesion["estudiante_datos"].items():
            contexto_datos += f"- {k}: {v}\n"
        status_identificacion = "ALUMNO YA IDENTIFICADO. No vuelvas a pedir su matrícula."
    else:
        contexto_datos = "EL ALUMNO AÚN NO HA SIDO IDENTIFICADO."
        status_identificacion = "DEBES PEDIR LA MATRÍCULA AMABLEMENTE."
    texto_historial = "\n".join([f"A: {i['pregunta']}\nB: {i['respuesta']}" for i in sesion["historial"][-3:]])
    
    instruccion_dinamica = (
        f"{prompt_maestro}\n\n"
        f"--- ESTADO DE LA SESIÓN ---\n"
        f"{status_identificacion}\n"
        f"{contexto_datos}\n\n"
        f"--- HISTORIAL RECIENTE ---\n"
        f"{texto_historial}\n\n"
        f"--- PREGUNTA ACTUAL ---\n"
        f"{pregunta}\n\n"
        f"INSTRUCCIÓN FINAL: Responde a la pregunta actual. Si ya tienes los datos arriba, utilízalos directamente. "
        f"Sé breve, no repitas la matrícula si no es necesario."
    )

    try:
        if not sesion["estudiante_datos"] and "beca" in pregunta.lower():
             respuesta_ai = brain.router_engine.query(pregunta)
             texto_final = str(respuesta_ai)
        else:
             respuesta_ai = Settings.llm.complete(instruccion_dinamica)
             texto_final = respuesta_ai.text
        sesion["historial"].append({"pregunta": pregunta, "respuesta": texto_final})
        
        return {"respuesta": texto_final, "is_recognized": True}

    except Exception as e:
        print(f"Error: {e}")
        return {"respuesta": "Hoo-hoo... Me dio un pequeño mareo. ¿Podrías repetirme eso?", "is_recognized": False}