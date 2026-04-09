from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient


BASE_DIR = Path(__file__).resolve().parent
PDFS_DIR = BASE_DIR / "data" / "pdfs"
RAW_OUTPUT_DIR = BASE_DIR / "data" / "raw_azure"

ENV_ENDPOINT = "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"
ENV_KEY = "AZURE_DOCUMENT_INTELLIGENCE_KEY"

MODEL_ID = "prebuilt-layout"
SUPPORTED_EXTENSIONS = {".pdf"}


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


def get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Missing environment variable: {name}. Set it before running the script."
        )
    return value


def ensure_directories() -> None:
    PDFS_DIR.mkdir(parents=True, exist_ok=True)
    RAW_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def list_pdf_files() -> list[Path]:
    return sorted(
        p for p in PDFS_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    )


def to_jsonable(obj: Any) -> Any:
    if obj is None:
        return None

    if isinstance(obj, (str, int, float, bool)):
        return obj

    if isinstance(obj, list):
        return [to_jsonable(x) for x in obj]

    if isinstance(obj, tuple):
        return [to_jsonable(x) for x in obj]

    if isinstance(obj, dict):
        return {k: to_jsonable(v) for k, v in obj.items()}

    if hasattr(obj, "as_dict") and callable(obj.as_dict):
        return to_jsonable(obj.as_dict())

    if hasattr(obj, "__dict__"):
        return {
            k: to_jsonable(v)
            for k, v in vars(obj).items()
            if not k.startswith("_")
        }

    return str(obj)


def build_output_path(pdf_path: Path) -> Path:
    return RAW_OUTPUT_DIR / f"{pdf_path.stem}_layout.json"


def analyze_pdf(client: DocumentIntelligenceClient, pdf_path: Path) -> dict[str, Any]:
    logger.info("Analyzing %s", pdf_path.name)

    with pdf_path.open("rb") as f:
        file_bytes = f.read()

    poller = client.begin_analyze_document(
        model_id=MODEL_ID,
        body=file_bytes,
        content_type="application/pdf",
    )
    result = poller.result()

    return {
        "source_file": pdf_path.name,
        "source_path": str(pdf_path),
        "model_id": MODEL_ID,
        "result": to_jsonable(result),
    }


def save_json(data: dict[str, Any], output_path: Path) -> None:
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main() -> int:
    try:
        ensure_directories()

        endpoint = get_required_env(ENV_ENDPOINT)
        key = get_required_env(ENV_KEY)

        pdf_files = list_pdf_files()
        if not pdf_files:
            logger.warning("No PDF files found in %s", PDFS_DIR.resolve())
            return 0

        client = DocumentIntelligenceClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(key),
        )

        successes = 0
        failures = 0

        for pdf_path in pdf_files:
            output_path = build_output_path(pdf_path)

            if output_path.exists():
                logger.info("Skipping %s because %s already exists", pdf_path.name, output_path.name)
                continue

            try:
                result_data = analyze_pdf(client, pdf_path)
                save_json(result_data, output_path)
                logger.info("Saved %s", output_path)
                successes += 1
            except Exception as exc:
                failures += 1
                logger.exception("Failed on %s: %s", pdf_path.name, exc)

        logger.info("Finished. Successes=%s Failures=%s", successes, failures)
        return 0 if failures == 0 else 1

    except Exception as exc:
        logger.exception("Fatal error: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())