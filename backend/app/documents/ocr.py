"""OCR Providers - abstract interface with multiple backends."""
import io
import logging
import os
import tempfile
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger("2to-eos.documents.ocr")


class OCRProvider(ABC):
    """Abstract OCR provider."""

    @abstractmethod
    def extract_text(self, file_content: bytes, mime_type: str) -> str:
        """Extract text from file content."""
        pass

    @abstractmethod
    def extract_structured(self, file_content: bytes, mime_type: str) -> dict[str, Any]:
        """Extract structured data (text, tables, key-value pairs)."""
        pass

    def is_available(self) -> bool:
        return True


class TesseractOCR(OCRProvider):
    """Tesseract OCR - local installation."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}
        self.lang = self.config.get("lang", "eng+ara")
        self._check_available()

    def _check_available(self):
        try:
            import pytesseract
            pytesseract.get_tesseract_version()
            self._available = True
        except Exception as e:
            logger.warning("Tesseract not available: %s", e)
            self._available = False

    def is_available(self) -> bool:
        return self._available

    def extract_text(self, file_content: bytes, mime_type: str) -> str:
        if not self._available:
            return ""

        try:
            import pytesseract
            from PIL import Image

            if mime_type == "application/pdf":
                return self._extract_pdf(file_content)

            image = Image.open(io.BytesIO(file_content))
            return pytesseract.image_to_string(image, lang=self.lang)
        except Exception as e:
            logger.error("Tesseract extraction failed: %s", e)
            return ""

    def _extract_pdf(self, file_content: bytes) -> str:
        try:
            import fitz  # PyMuPDF
            import pytesseract
            from PIL import Image

            doc = fitz.open(stream=file_content, filetype="pdf")
            text_parts = []

            for page_num in range(len(doc)):
                page = doc[page_num]
                pix = page.get_pixmap(dpi=200)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                text = pytesseract.image_to_string(img, lang=self.lang)
                text_parts.append(f"--- Page {page_num + 1} ---\n{text}")

            doc.close()
            return "\n\n".join(text_parts)
        except Exception as e:
            logger.error("PDF OCR failed: %s", e)
            return ""

    def extract_structured(self, file_content: bytes, mime_type: str) -> dict[str, Any]:
        if not self._available:
            return {"text": "", "tables": [], "key_values": {}}

        try:
            import pytesseract
            from PIL import Image

            if mime_type == "application/pdf":
                text = self._extract_pdf(file_content)
            else:
                image = Image.open(io.BytesIO(file_content))
                text = pytesseract.image_to_string(image, lang=self.lang)

            # Simple table detection from text
            tables = self._detect_tables(text)

            return {
                "text": text,
                "tables": tables,
                "key_values": self._extract_key_values(text),
            }
        except Exception as e:
            logger.error("Structured extraction failed: %s", e)
            return {"text": "", "tables": [], "key_values": {}}

    def _detect_tables(self, text: str) -> list[dict]:
        """Simple table detection from text lines."""
        lines = text.split("\n")
        tables = []
        current_table = []

        for line in lines:
            # Heuristic: lines with multiple columns separated by spaces/tabs
            parts = [p.strip() for p in line.split("  ") if p.strip()]
            if len(parts) >= 3:
                current_table.append(parts)
            elif current_table:
                if len(current_table) >= 2:
                    tables.append({
                        "rows": current_table,
                        "row_count": len(current_table),
                        "col_count": max(len(r) for r in current_table),
                    })
                current_table = []

        if current_table and len(current_table) >= 2:
            tables.append({
                "rows": current_table,
                "row_count": len(current_table),
                "col_count": max(len(r) for r in current_table),
            })

        return tables

    def _extract_key_values(self, text: str) -> dict[str, str]:
        """Extract key-value pairs from text."""
        import re
        kv = {}
        lines = text.split("\n")

        for line in lines:
            # Pattern: "Key: Value" or "Key Value"
            match = re.match(r"^([A-Za-z][A-Za-z0-9\s]{1,30}):\s*(.+)$", line.strip())
            if match:
                key = match.group(1).strip().lower().replace(" ", "_")
                value = match.group(2).strip()
                if value:
                    kv[key] = value

        return kv


class CloudOCRProvider(OCRProvider):
    """Base class for cloud OCR providers."""

    def __init__(self, config: dict[str, Any]):
        self.config = config
        self._available = bool(config.get("api_key") or config.get("credentials_path"))

    def is_available(self) -> bool:
        return self._available


class AWSTextract(CloudOCRProvider):
    """AWS Textract OCR."""

    def extract_text(self, file_content: bytes, mime_type: str) -> str:
        if not self._available:
            return ""

        try:
            import boto3

            client = boto3.client(
                "textract",
                region_name=self.config.get("region", "us-east-1"),
                aws_access_key_id=self.config.get("access_key_id"),
                aws_secret_access_key=self.config.get("secret_access_key"),
            )

            response = client.detect_document_text(Document={"Bytes": file_content})

            text_lines = []
            for block in response.get("Blocks", []):
                if block["BlockType"] == "LINE":
                    text_lines.append(block["Text"])

            return "\n".join(text_lines)
        except Exception as e:
            logger.error("AWS Textract failed: %s", e)
            return ""

    def extract_structured(self, file_content: bytes, mime_type: str) -> dict[str, Any]:
        if not self._available:
            return {"text": "", "tables": [], "key_values": {}}

        try:
            import boto3

            client = boto3.client(
                "textract",
                region_name=self.config.get("region", "us-east-1"),
                aws_access_key_id=self.config.get("access_key_id"),
                aws_secret_access_key=self.config.get("secret_access_key"),
            )

            # Use analyze_document for tables and forms
            response = client.analyze_document(
                Document={"Bytes": file_content},
                FeatureTypes=["TABLES", "FORMS"],
            )

            text_lines = []
            tables = []
            key_values = {}

            blocks = {b["Id"]: b for b in response.get("Blocks", [])}

            for block in response.get("Blocks", []):
                if block["BlockType"] == "LINE":
                    text_lines.append(block["Text"])
                elif block["BlockType"] == "TABLE":
                    table_data = self._parse_table(block, blocks)
                    tables.append(table_data)
                elif block["BlockType"] == "KEY_VALUE_SET":
                    if block.get("EntityTypes", []) == ["KEY"]:
                        value_block = self._find_value_block(block, blocks)
                        if value_block:
                            key = self._get_text(block, blocks)
                            value = self._get_text(value_block, blocks)
                            key_values[key.lower().replace(" ", "_")] = value

            return {
                "text": "\n".join(text_lines),
                "tables": tables,
                "key_values": key_values,
            }
        except Exception as e:
            logger.error("AWS Textract structured failed: %s", e)
            return {"text": "", "tables": [], "key_values": {}}

    def _parse_table(self, table_block: dict, all_blocks: dict) -> dict:
        rows = {}
        for rel in table_block.get("Relationships", []):
            if rel["Type"] == "CHILD":
                for cell_id in rel["Ids"]:
                    cell = all_blocks.get(cell_id)
                    if cell and cell["BlockType"] == "CELL":
                        row_idx = cell.get("RowIndex", 0)
                        col_idx = cell.get("ColumnIndex", 0)
                        text = self._get_text(cell, all_blocks)
                        if row_idx not in rows:
                            rows[row_idx] = {}
                        rows[row_idx][col_idx] = text

        # Convert to list of lists
        table_rows = []
        for r in sorted(rows.keys()):
            row_data = []
            for c in sorted(rows[r].keys()):
                row_data.append(rows[r][c])
            table_rows.append(row_data)

        return {
            "rows": table_rows,
            "row_count": len(table_rows),
            "col_count": max(len(r) for r in table_rows) if table_rows else 0,
        }

    def _find_value_block(self, key_block: dict, all_blocks: dict) -> dict | None:
        for rel in key_block.get("Relationships", []):
            if rel["Type"] == "VALUE":
                for value_id in rel["Ids"]:
                    return all_blocks.get(value_id)
        return None

    def _get_text(self, block: dict, all_blocks: dict) -> str:
        texts = []
        for rel in block.get("Relationships", []):
            if rel["Type"] == "CHILD":
                for child_id in rel["Ids"]:
                    child = all_blocks.get(child_id)
                    if child and child["BlockType"] == "WORD":
                        texts.append(child["Text"])
        return " ".join(texts)


class GoogleDocumentAI(CloudOCRProvider):
    """Google Document AI OCR."""

    def extract_text(self, file_content: bytes, mime_type: str) -> str:
        if not self._available:
            return ""

        try:
            from google.cloud import documentai_v1 as documentai

            client = documentai.DocumentProcessorServiceClient()
            processor_name = self.config.get("processor_name")

            raw_document = documentai.RawDocument(
                content=file_content,
                mime_type=mime_type,
            )

            request = documentai.ProcessRequest(
                name=processor_name,
                raw_document=raw_document,
            )

            result = client.process_document(request=request)
            return result.document.text
        except Exception as e:
            logger.error("Google Document AI failed: %s", e)
            return ""

    def extract_structured(self, file_content: bytes, mime_type: str) -> dict[str, Any]:
        if not self._available:
            return {"text": "", "tables": [], "key_values": {}}

        try:
            from google.cloud import documentai_v1 as documentai

            client = documentai.DocumentProcessorServiceClient()
            processor_name = self.config.get("processor_name")

            raw_document = documentai.RawDocument(
                content=file_content,
                mime_type=mime_type,
            )

            request = documentai.ProcessRequest(
                name=processor_name,
                raw_document=raw_document,
            )

            result = client.process_document(request=request)
            doc = result.document

            tables = []
            for page in doc.pages:
                for table in page.tables:
                    table_data = []
                    for row in table.body_rows:
                        row_data = []
                        for cell in row.cells:
                            cell_text = " ".join(
                                token.text for token in cell.tokens if token.text
                            )
                            row_data.append(cell_text)
                        table_data.append(row_data)
                    tables.append({
                        "rows": table_data,
                        "row_count": len(table_data),
                        "col_count": max(len(r) for r in table_data) if table_data else 0,
                    })

            # Extract form fields (key-value pairs)
            key_values = {}
            for page in doc.pages:
                for field in page.form_fields:
                    key = field.field_name.text_anchor.content if field.field_name.text_anchor else ""
                    value = field.field_value.text_anchor.content if field.field_value.text_anchor else ""
                    if key and value:
                        key_values[key.lower().replace(" ", "_")] = value

            return {
                "text": doc.text,
                "tables": tables,
                "key_values": key_values,
            }
        except Exception as e:
            logger.error("Google Document AI structured failed: %s", e)
            return {"text": "", "tables": [], "key_values": {}}


class AzureFormRecognizer(CloudOCRProvider):
    """Azure Form Recognizer OCR."""

    def extract_text(self, file_content: bytes, mime_type: str) -> str:
        if not self._available:
            return ""

        try:
            from azure.ai.formrecognizer import DocumentAnalysisClient
            from azure.core.credentials import AzureKeyCredential

            endpoint = self.config.get("endpoint")
            key = self.config.get("key")

            client = DocumentAnalysisClient(endpoint, AzureKeyCredential(key))

            poller = client.begin_analyze_document("prebuilt-read", file_content)
            result = poller.result()

            text_lines = []
            for page in result.pages:
                for line in page.lines:
                    text_lines.append(line.content)

            return "\n".join(text_lines)
        except Exception as e:
            logger.error("Azure Form Recognizer failed: %s", e)
            return ""

    def extract_structured(self, file_content: bytes, mime_type: str) -> dict[str, Any]:
        if not self._available:
            return {"text": "", "tables": [], "key_values": {}}

        try:
            from azure.ai.formrecognizer import DocumentAnalysisClient
            from azure.core.credentials import AzureKeyCredential

            endpoint = self.config.get("endpoint")
            key = self.config.get("key")

            client = DocumentAnalysisClient(endpoint, AzureKeyCredential(key))

            poller = client.begin_analyze_document("prebuilt-document", file_content)
            result = poller.result()

            text_lines = []
            tables = []
            key_values = {}

            for page in result.pages:
                for line in page.lines:
                    text_lines.append(line.content)

            for table in result.tables:
                table_data = []
                row_data = []
                current_row = -1
                for cell in table.cells:
                    if cell.row_index != current_row:
                        if row_data:
                            table_data.append(row_data)
                        row_data = [cell.content]
                        current_row = cell.row_index
                    else:
                        row_data.append(cell.content)
                if row_data:
                    table_data.append(row_data)

                tables.append({
                    "rows": table_data,
                    "row_count": len(table_data),
                    "col_count": table.column_count,
                })

            for doc in result.documents:
                for name, field in doc.fields.items():
                    if field.value:
                        key_values[name.lower().replace(" ", "_")] = str(field.value)

            return {
                "text": "\n".join(text_lines),
                "tables": tables,
                "key_values": key_values,
            }
        except Exception as e:
            logger.error("Azure Form Recognizer structured failed: %s", e)
            return {"text": "", "tables": [], "key_values": {}}


# Provider registry
def get_ocr_provider(provider: str, config: dict[str, Any] | None = None) -> OCRProvider:
    """Get OCR provider by name."""
    providers = {
        "tesseract": TesseractOCR,
        "aws_textract": AWSTextract,
        "google_document_ai": GoogleDocumentAI,
        "azure_form_recognizer": AzureFormRecognizer,
    }

    provider_class = providers.get(provider)
    if not provider_class:
        logger.warning("Unknown OCR provider: %s, falling back to Tesseract", provider)
        return TesseractOCR(config)

    return provider_class(config or {})


def get_best_available_ocr(config: dict[str, Any] | None = None) -> OCRProvider:
    """Get the best available OCR provider based on configuration."""
    config = config or {}

    # Check cloud providers first (higher quality)
    for provider_name in ["aws_textract", "google_document_ai", "azure_form_recognizer"]:
        provider_config = config.get(provider_name, {})
        provider = get_ocr_provider(provider_name, provider_config)
        if provider.is_available():
            logger.info("Using %s for OCR", provider_name)
            return provider

    # Fall back to Tesseract
    tesseract = TesseractOCR(config.get("tesseract", {}))
    if tesseract.is_available():
        logger.info("Using Tesseract for OCR")
        return tesseract

    # Last resort - dummy provider that returns empty
    logger.warning("No OCR provider available!")
    return DummyOCR()


class DummyOCR(OCRProvider):
    """Dummy OCR for when no provider is available."""

    def extract_text(self, file_content: bytes, mime_type: str) -> str:
        return ""

    def extract_structured(self, file_content: bytes, mime_type: str) -> dict[str, Any]:
        return {"text": "", "tables": [], "key_values": {}}
