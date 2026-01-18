import os
import uuid
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse

from speer_core import process_invoice, export_outputs

UPLOAD_DIR = "uploads"
OUTPUT_DIR = "output"

os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI(title="Speer")

last_run_id = None
last_records = []


@app.get("/", response_class=HTMLResponse)
def index():
    return """
    <h2>Speer</h2>
    <p>Minimal, auditable invoice ingestion.</p>
    <form action="/upload" method="post" enctype="multipart/form-data">
        <input type="file" name="files" multiple />
        <button type="submit">Upload invoices</button>
    </form>
    <br/>
    <a href="/export">Export results</a>
    """


@app.post("/upload")
async def upload(files: list[UploadFile] = File(...)):
    global last_run_id, last_records

    run_id = uuid.uuid4().hex[:8]
    records = []

    for file in files:
        path = os.path.join(UPLOAD_DIR, file.filename)
        with open(path, "wb") as handle:
            handle.write(await file.read())

        records.append(process_invoice(path, run_id))

    export_outputs(records, OUTPUT_DIR, run_id)

    last_run_id = run_id
    last_records = records

    return {
        "run_id": run_id,
        "processed": len(records),
        "ok": sum(1 for r in records if r["status"] == "ok"),
        "needs_review": sum(1 for r in records if r["status"] == "needs_review"),
        "records": records,
    }


@app.get("/export")
def export():
    return {
        "message": "Files generated in /output",
        "run_id": last_run_id,
    }

