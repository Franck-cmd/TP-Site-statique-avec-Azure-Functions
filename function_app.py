import azure.functions as func
from azure.storage.blob import BlobServiceClient
from PIL import Image
import io
import os
import uuid
import json
import logging

app = func.FunctionApp()

# ---------- UPLOAD ----------
@app.route(route="upload", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
def upload(req: func.HttpRequest) -> func.HttpResponse:
    try:
        file = req.files.get("file")
        if not file:
            return func.HttpResponse("No file provided", status_code=400)

        blob_service = BlobServiceClient.from_connection_string(
            os.environ["AzureWebJobsStorage"]
        )

        container = blob_service.get_container_client("images")

        filename = f"{uuid.uuid4()}-{file.filename}"
        blob = container.get_blob_client(filename)
        blob.upload_blob(file.stream, overwrite=True)

        return func.HttpResponse(blob.url, status_code=200)

    except Exception as e:
        return func.HttpResponse(str(e), status_code=500)


# ---------- LIST ----------
@app.route(route="list", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def list_images(req: func.HttpRequest) -> func.HttpResponse:
    try:
        blob_service = BlobServiceClient.from_connection_string(
            os.environ["AzureWebJobsStorage"]
        )

        container = blob_service.get_container_client("thumbnails")

        images = [
            {
                "name": blob.name,
                "url": f"https://imagetp.blob.core.windows.net/thumbnails/{blob.name}"
            }
            for blob in container.list_blobs()
        ]

        return func.HttpResponse(
            json.dumps(images),
            mimetype="application/json"
        )

    except Exception as e:
        return func.HttpResponse(str(e), status_code=500)


# ---------- RESIZE (BLOB TRIGGER) ----------
@app.function_name(name="resize")
@app.blob_trigger(
    arg_name="blob",
    path="images/{name}",
    connection="AzureWebJobsStorage"
)
def resize(blob: func.InputStream):
    logging.info(f"Resize triggered for: {blob.name}")

    blob_service = BlobServiceClient.from_connection_string(
        os.environ["AzureWebJobsStorage"]
    )

    thumbnails_container = blob_service.get_container_client("thumbnails")

    image = Image.open(blob)
    image.thumbnail((256, 256))

    output = io.BytesIO()
    image.save(output, format=image.format)
    output.seek(0)

    filename = blob.name.split("/")[-1]

    thumbnails_container.upload_blob(
        name=filename,
        data=output,
        overwrite=True
    )

    logging.info(f"Thumbnail created: {filename}")
