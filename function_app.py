import asyncio
import azure.functions as func
import logging
import json
from agentiacap.utils.globals import InputSchema
from agentiacap.workflows.main import graph

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

@app.route(route="AgenteIACAP", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
async def AgenteIACAP(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    
    loop = asyncio.get_running_loop()
    loop.set_task_factory(None)

    # Intento obtener los parametros (para GET)
    # asunto = req.params.get('asunto')
    # cuerpo = req.params.get('cuerpo')
    # adjuntos = req.params.get('adjuntos')

    # Si no se encuentran los parámetros en la URL, intentar obtenerlos del cuerpo (para POST)
    try:
        body = req.get_json()  # Si los datos están en el cuerpo de la solicitud
        asunto = body.get('asunto')
        cuerpo = body.get('cuerpo')
        adjuntos = body.get('adjuntos')

    except ValueError as e:
        return func.HttpResponse(f"Body no válido. Error: {e}", status_code=400)

    # Si 'adjuntos' no es una lista, termina.
    if not isinstance(adjuntos, list):
        return func.HttpResponse(
            json.dumps({"error": "Los adjuntos deben ser una lista de objetos con 'file_name' y 'base64_content'."}),
            mimetype="application/json",
            status_code=400
        )
    if len(adjuntos) != 0:
        # adjuntos = json.loads(adjuntos)
        # Validar que adjuntos sea una lista de objetos con "file_name" y "base64_content"
        for item in adjuntos:
            if "file_name" not in item or "base64_content" not in item:
                return func.HttpResponse(
                json.dumps({"error": "Los adjuntos deben ser una lista de objetos con 'file_name' y 'base64_content'."}),
                mimetype="application/json",
                status_code=400
            )

        #if any(
        #    not isinstance(item, list) or
        #    "file_name" not in item or
        #    "base64_content" not in item
        #    for item in adjuntos
        #):
        #    return func.HttpResponse(
        #        json.dumps({"error": "Los adjuntos deben ser una lista de objetos con 'file_name' y 'base64_content'."}),
        #        mimetype="application/json",
        #        status_code=400
        #    )
    
    input_data = InputSchema(asunto=asunto, cuerpo=cuerpo, adjuntos=adjuntos)
    try:
        response = await graph.ainvoke(input=input_data)
    except Exception as e:
        logging.error(f"Error al invocar graph.ainvoke: {str(e)}")
        return func.HttpResponse("Error al procesar la solicitud.", status_code=500)
    
    result = response.get("result", {})

    return func.HttpResponse(
        json.dumps(result, indent=2),
        mimetype="application/json",
        status_code=200
    )