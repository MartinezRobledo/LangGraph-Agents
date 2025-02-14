import asyncio
import logging
import json
import requests
import azure.functions as func
from agentiacap.utils.globals import InputSchema
from agentiacap.workflows.main import graph

# Configuración de Blob Storage
BLOB_BASE_URL = "https://agentiacapattachments.blob.core.windows.net/attachments"
SAS_TOKEN = "sp=racwdl&st=2025-02-14T15:56:40Z&se=2026-01-01T23:56:40Z&sv=2022-11-02&sr=c&sig=oPmanx%2FZci4N1g%2BSNLWcnVm2jN%2Bpk2taiTKzkWivxrQ%3D"
LIST_BLOBS_URL = f"{BLOB_BASE_URL}?restype=container&comp=list&{SAS_TOKEN}"


def listar_archivos_blob():
    """Obtiene la lista de archivos disponibles en el Blob Storage."""
    try:
        response = requests.get(LIST_BLOBS_URL)
        if response.status_code != 200:
            logging.error(f"Error al obtener la lista de blobs: {response.text}")
            return []

        # Extraer nombres de archivos del XML devuelto por Azure
        import xml.etree.ElementTree as ET
        root = ET.fromstring(response.text)
        archivos = [blob.find("Name").text for blob in root.findall(".//Blob")]

        logging.info(f"Archivos en el Blob Storage: {archivos}")
        return archivos

    except Exception as e:
        logging.error(f"Error al listar archivos del Blob Storage: {str(e)}")
        return []

def obtener_blob_por_id(blob_id: str):
    """Busca un archivo en Azure Blob Storage por su ID y devuelve su contenido y nombre real."""
    try:
        # Obtener lista de blobs disponibles
        blobs = listar_archivos_blob()

        for blob_name in blobs:
            # Construir URL del blob
            blob_url = f"{BLOB_BASE_URL}/{blob_name}?{SAS_TOKEN}"

            # Aquí estamos suponiendo que el ID está en los metadatos o en el nombre del archivo
            # Necesitarías adaptar esto si el ID es parte del nombre del archivo o si está en los metadatos
            if blob_id in blob_name:  # Comprobamos si el ID está en el nombre del archivo
                logging.info(f"✅ Archivo encontrado: {blob_name}")
                # Descargar el archivo usando la URL
                response = requests.get(blob_url)
                if response.status_code == 200:
                    return {"file_name": blob_name, "content": response.content}
                else:
                    logging.error(f"❌ Error al descargar {blob_name}: {response.text}")
                    return None

        logging.warning(f"⚠️ No se encontró ningún archivo con ID: {blob_id}")
        return None
    except Exception as e:
        logging.error(f"❌ Error al obtener archivo por ID: {e}")
        return None

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.route(route="AgenteIACAP", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
async def AgenteIACAP(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Python HTTP trigger function processed a request.")

    loop = asyncio.get_running_loop()
    loop.set_task_factory(None)

    try:
        body = req.get_json()
        asunto = body.get("asunto")
        cuerpo = body.get("cuerpo")
        ids_adjuntos = body.get("adjuntos")  # Recibimos los IDs de los archivos

    except ValueError as e:
        return func.HttpResponse(f"Body no válido. Error: {e}", status_code=400)

    # Validar que 'adjuntos' sea una lista de IDs
    if not isinstance(ids_adjuntos, list):
        return func.HttpResponse(
            json.dumps({"error": "Los adjuntos deben ser una lista de IDs de archivos."}),
            mimetype="application/json",
            status_code=400
        )

    adjuntos = []
    for file_id in ids_adjuntos:
        archivo = await obtener_blob_por_id(file_id)
        if archivo:
            adjuntos.append(archivo)
        else:
            logging.warning(f"⚠️ No se pudo obtener el archivo con ID {file_id}")

    # Crear el objeto de entrada para el flujo
    input_data = InputSchema(asunto=asunto, cuerpo=cuerpo, adjuntos=adjuntos)
    
    try:
        response = await graph.ainvoke(input=input_data)
    except Exception as e:
        logging.error(f"❌ Error al invocar graph.ainvoke: {e}")
        return func.HttpResponse("Error al procesar la solicitud.", status_code=500)

    result = response.get("result", {})

    return func.HttpResponse(
        json.dumps(result, indent=2),
        mimetype="application/json",
        status_code=200
    )




# import asyncio
# import base64
# import os
# import azure.functions as func
# import logging
# import json
# from agentiacap.utils.globals import InputSchema
# from agentiacap.workflows.main import graph

# app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# @app.route(route="AgenteIACAP", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
# async def AgenteIACAP(req: func.HttpRequest) -> func.HttpResponse:
#     logging.info('Python HTTP trigger function processed a request.')
    
#     loop = asyncio.get_running_loop()
#     loop.set_task_factory(None)

#     try:
#         body = req.get_json()  # Si los datos están en el cuerpo de la solicitud
#         asunto = body.get('asunto')
#         cuerpo = body.get('cuerpo')
#         adjuntos = body.get('adjuntos')

#     except ValueError as e:
#         return func.HttpResponse(f"Body no válido. Error: {e}", status_code=400)

#     # Si 'adjuntos' no es una lista, termina.
#     if not isinstance(adjuntos, list):
#         return func.HttpResponse(
#             json.dumps({"error": "Los adjuntos deben ser una lista de objetos con 'file_name' y 'base64_content'."}),
#             mimetype="application/json",
#             status_code=400
#         )
#     if len(adjuntos) != 0:
#         # Validar que adjuntos sea una lista de objetos con "file_name" y "base64_content"
#         for item in adjuntos:
#             if "file_name" not in item or "base64_content" not in item:
#                 return func.HttpResponse(
#                 json.dumps({"error": "Los adjuntos deben ser una lista de objetos con 'file_name' y 'base64_content'."}),
#                 mimetype="application/json",
#                 status_code=400
#             )

#         if any(
#            not isinstance(item, list) or
#            "file_name" not in item or
#            "base64_content" not in item
#            for item in adjuntos
#         ):
#            return func.HttpResponse(
#                json.dumps({"error": "Los adjuntos deben ser una lista de objetos con 'file_name' y 'base64_content'."}),
#                mimetype="application/json",
#                status_code=400
#            )
    
#     input_data = InputSchema(asunto=asunto, cuerpo=cuerpo, adjuntos=adjuntos)
#     try:
#         response = await graph.ainvoke(input=input_data)
#     except Exception as e:
#         logging.error(f"Error al invocar graph.ainvoke: {str(e)}")
#         return func.HttpResponse("Error al procesar la solicitud.", status_code=500)
    
#     result = response.get("result", {})

#     return func.HttpResponse(
#         json.dumps(result, indent=2),
#         mimetype="application/json",
#         status_code=200
#     )