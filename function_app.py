import asyncio
import azure.functions as func
import logging
import json
from agentiacap.configs.classes import Input
from agentiacap.workflows.main import graph

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.route(route="AgenteIACAP")
async def AgenteIACAP(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    
    loop = asyncio.get_running_loop()
    loop.set_task_factory(None)

    # Intento obtener los parametros (para GET)
    asunto = req.params.get('asunto')
    cuerpo = req.params.get('cuerpo')
    adjuntos = req.params.get('adjuntos')

    # Si no se encuentran los parámetros en la URL, intentar obtenerlos del cuerpo (para POST)
    if not asunto or not cuerpo:
        try:
            body = req.get_json()  # Si los datos están en el cuerpo de la solicitud
            asunto = body.get('asunto')
            cuerpo = body.get('cuerpo')
            adjuntos = body.get('adjuntos')

        except ValueError:
            return func.HttpResponse("Body no válido.", status_code=400)

    adjuntos = json.loads(adjuntos)
    # Validar que adjuntos sea una lista de objetos con "file_name" y "base64_content"
    if not isinstance(adjuntos, list) or any(
        not isinstance(item, dict) or
        "file_name" not in item or
        "base64_content" not in item
        for item in adjuntos
    ):
        return func.HttpResponse(
            json.dumps({"error": "Los adjuntos deben ser una lista de objetos con 'file_name' y 'base64_content'."}),
            mimetype="application/json",
            status_code=400
        )
    
    input_data = Input(asunto=asunto, cuerpo=cuerpo, adjuntos=adjuntos)
    try:
        response = await graph.ainvoke(input=input_data)
    except Exception as e:
        logging.error(f"Error al invocar graph.ainvoke: {str(e)}")
        return func.HttpResponse("Error al procesar la solicitud.", status_code=500)
    
    result = response.get("result", {})
    category = result.get("category", {})
    extractions = result.get("extractions", {})
    tokens = result.get("tokens", {})

    # Construir la respuesta
    response_data = {
        "category": category,
        "extractions": extractions,
        "tokens": tokens
    }

    return func.HttpResponse(
        json.dumps(response_data, indent=2),
        mimetype="application/json",
        status_code=200
    )
