import asyncio
import azure.functions as func
import logging
import json
from src.configs.classes import Input
from src.workflows.main import graph

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.route(route="http_trigger", auth_level=func.AuthLevel.ANONYMOUS)
async def http_trigger(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    
    loop = asyncio.get_running_loop()
    loop.set_task_factory(None)

    asunto = req.params.get('asunto')
    cuerpo = req.params.get('cuerpo')

    # Si no se encuentran los parámetros en la URL, intentar obtenerlos del cuerpo (para GET)
    if not asunto or not cuerpo:
        try:
            body = req.get_json()  # Si los datos están en el cuerpo de la solicitud
            asunto = body.get('asunto')
            cuerpo = body.get('cuerpo')
        except ValueError:
            return func.HttpResponse("Body no válido.", status_code=400)

    input_data = Input(asunto=asunto, cuerpo=cuerpo, adjuntos=[])
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