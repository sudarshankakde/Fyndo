import io
import json
import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from fastapi import UploadFile

from app.admin.templating import parse_kyc_docs
from app.core.database import async_session_factory, ensure_compatibility_schema
from app.main import app
from app.services.media_service import sniff_media_kind, resolve_extension, store_upload, MediaValidationError


def unique_phone() -> str:
    return f"+9197{uuid.uuid4().int % 100_000_000:08d}"


@pytest.fixture
async def client():
    await ensure_compatibility_schema()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _login(client: AsyncClient, phone: str, role: str = "merchant") -> dict:
    send = await client.post("/api/v1/auth/otp/send", json={"phone": phone, "role": role})
    assert send.status_code == 200
    otp = send.json()["data"]["test_otp"]
    verify = await client.post(
        "/api/v1/auth/otp/verify",
        json={"phone": phone, "otp": otp, "role": role, "preferred_language": "en"}
    )
    assert verify.status_code == 200
    return verify.json()["data"]


def test_parse_kyc_docs_filter():
    """Tests parse_kyc_docs handles JSON lists, CSVs, single URLs, and detects PDFs."""
    # Empty
    assert parse_kyc_docs(None) == []
    assert parse_kyc_docs("") == []
    assert parse_kyc_docs("   ") == []

    # Single image URL
    single = parse_kyc_docs("https://res.cloudinary.com/fyndo/kyc/doc1.jpg")
    assert len(single) == 1
    assert single[0]["label"] == "Doc 1"
    assert single[0]["is_pdf"] is False

    # Single PDF URL
    single_pdf = parse_kyc_docs("https://res.cloudinary.com/fyndo/kyc/license.pdf")
    assert len(single_pdf) == 1
    assert single_pdf[0]["label"] == "Doc 1 (PDF)"
    assert single_pdf[0]["is_pdf"] is True

    # Comma-separated URLs
    csv_docs = parse_kyc_docs("https://cdn/doc1.jpg, https://cdn/doc2.pdf")
    assert len(csv_docs) == 2
    assert csv_docs[0]["label"] == "Doc 1"
    assert csv_docs[0]["is_pdf"] is False
    assert csv_docs[1]["label"] == "Doc 2 (PDF)"
    assert csv_docs[1]["is_pdf"] is True

    # JSON array
    json_str = json.dumps(["https://cdn/a.webp", "https://cdn/b.pdf", "https://cdn/c.png"])
    json_docs = parse_kyc_docs(json_str)
    assert len(json_docs) == 3
    assert json_docs[0]["label"] == "Doc 1"
    assert json_docs[1]["label"] == "Doc 2 (PDF)"
    assert json_docs[2]["label"] == "Doc 3"


def test_sniff_media_kind_pdf():
    """Tests detection of PDF magic bytes."""
    header = b"%PDF-1.4\n%..."
    assert sniff_media_kind(header) == "document"
    assert resolve_extension("doc.pdf", "application/pdf") == ".pdf"


def test_store_upload_pdf(tmp_path, monkeypatch):
    """Tests local upload pipeline for PDF files."""
    monkeypatch.setattr("app.services.media_service.upload_root", lambda: str(tmp_path))
    pdf_bytes = b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
    upload = UploadFile(
        filename="registration_cert.pdf",
        file=io.BytesIO(pdf_bytes),
        headers={"content-type": "application/pdf"}
    )
    res = store_upload(upload, folder="kyc", sync_cdn=False)
    assert res["url"].endswith(".pdf")
    assert res["content_type"] == "application/pdf"


@pytest.mark.asyncio
async def test_draft_with_shop_act_and_udyam(client: AsyncClient):
    """Tests draft saving and retrieval with shop_act and udyam optional fields."""
    phone = unique_phone()
    auth = await _login(client, phone, role="merchant")
    token = auth["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    draft_payload = {
        "step": 3,
        "business_name": "Nagpur Electronics Hub",
        "sector": "ELECTRONICS",
        "description": "Premium electronics store",
        "address_text": "Sitabuldi Main Road",
        "city": "Nagpur",
        "pincode": "440012",
        "latitude": 21.1458,
        "longitude": 79.0882,
        "gstin": "27AAAAA0000A1Z5",
        "shop_act": "MH-NAG-12345/2024",
        "udyam": "UDYAM-MH-26-0012345",
        "kyc_doc_url": json.dumps(["https://cdn/doc1.jpg", "https://cdn/doc2.pdf"]),
    }

    # Save draft
    put_res = await client.put("/api/v1/merchants/onboard/draft", json=draft_payload, headers=headers)
    assert put_res.status_code == 200, put_res.text
    saved = put_res.json()["data"]
    assert saved["shop_act"] == "MH-NAG-12345/2024"
    assert saved["udyam"] == "UDYAM-MH-26-0012345"

    # Retrieve draft
    get_res = await client.get("/api/v1/merchants/onboard/draft", headers=headers)
    assert get_res.status_code == 200
    retrieved = get_res.json()["data"]
    assert retrieved["has_draft"] is True
    assert retrieved["shop_act"] == "MH-NAG-12345/2024"
    assert retrieved["udyam"] == "UDYAM-MH-26-0012345"
    assert "https://cdn/doc2.pdf" in retrieved["kyc_doc_url"]


@pytest.mark.asyncio
async def test_onboard_merchant_with_shop_act_and_udyam(client: AsyncClient):
    """Tests onboarding a merchant with shop_act and udyam, and checking profile."""
    phone = unique_phone()
    auth = await _login(client, phone, role="merchant")
    token = auth["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    kyc_urls = json.dumps([
        "https://res.cloudinary.com/fyndo/kyc/gumasta.pdf",
        "https://res.cloudinary.com/fyndo/kyc/shopfront.jpg"
    ])

    onboard_payload = {
        "business_name": "Shree Ganesh Textiles",
        "sector": "FASHION_CLOTHING",
        "address_text": "Gandhibagh Market",
        "city": "Nagpur",
        "latitude": 21.1500,
        "longitude": 79.1000,
        "gstin": "27ABCDE1234F1Z5",
        "shop_act": "SHOP-ACT-998877",
        "udyam": "UDYAM-MH-01-9988776",
        "kyc_doc_url": kyc_urls,
        "description": "Traditional sarees and fabrics",
    }

    res = await client.post("/api/v1/merchants/onboard", json=onboard_payload, headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()["data"]
    assert data["business_name"] == "Shree Ganesh Textiles"
    assert data["shop_act"] == "SHOP-ACT-998877"
    assert data["udyam"] == "UDYAM-MH-01-9988776"
    assert data["kyc_doc_url"] == kyc_urls

    # Check profile endpoint returns shop_act and udyam
    prof_res = await client.get("/api/v1/merchants/profile", headers=headers)
    assert prof_res.status_code == 200
    prof = prof_res.json()["data"]
    assert prof["shop_act"] == "SHOP-ACT-998877"
    assert prof["udyam"] == "UDYAM-MH-01-9988776"

    # Check profile patch can update shop_act and udyam
    patch_res = await client.patch(
        "/api/v1/merchants/profile",
        json={"shop_act": "UPDATED-ACT-123", "udyam": "UPDATED-UDYAM-456"},
        headers=headers,
    )
    assert patch_res.status_code == 200
    updated = patch_res.json()["data"]
    assert updated["shop_act"] == "UPDATED-ACT-123"
    assert updated["udyam"] == "UPDATED-UDYAM-456"

    # Verify AdminService includes shop_act and udyam in merchant detail
    from app.services.admin_service import AdminService
    async with async_session_factory() as session:
        admin_detail = await AdminService.get_merchant(uuid.UUID(data["id"]), session)
        assert admin_detail is not None
        assert admin_detail.shop_act == "UPDATED-ACT-123"
        assert admin_detail.udyam == "UPDATED-UDYAM-456"


@pytest.mark.asyncio
async def test_onboard_validation_errors(client: AsyncClient):
    """Tests validation constraints for shop_act, udyam, and multi-doc KYC limits."""
    phone = unique_phone()
    auth = await _login(client, phone, role="merchant")
    token = auth["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    base_payload = {
        "business_name": "Test Shop",
        "sector": "ELECTRONICS",
        "address_text": "Sitabuldi Market",
        "city": "Nagpur",
        "latitude": 21.1458,
        "longitude": 79.0882,
        "kyc_doc_url": "https://res.cloudinary.com/fyndo/kyc/doc.pdf",
    }

    # 1. >50 chars shop_act rejected with 422
    res_long = await client.post(
        "/api/v1/merchants/onboard",
        json={**base_payload, "shop_act": "A" * 51},
        headers=headers,
    )
    assert res_long.status_code == 422

    # 2. Invalid symbols in udyam rejected with 422
    res_sym = await client.post(
        "/api/v1/merchants/onboard",
        json={**base_payload, "udyam": "UDYAM$#@!*&^"},
        headers=headers,
    )
    assert res_sym.status_code == 422

    # 3. Empty document list string [] rejected with 422
    res_empty_doc = await client.post(
        "/api/v1/merchants/onboard",
        json={**base_payload, "kyc_doc_url": "[]"},
        headers=headers,
    )
    assert res_empty_doc.status_code == 422

    # 4. More than 3 documents rejected with 422
    too_many_docs = json.dumps([
        "https://cdn/1.pdf",
        "https://cdn/2.pdf",
        "https://cdn/3.pdf",
        "https://cdn/4.pdf",
    ])
    res_many_docs = await client.post(
        "/api/v1/merchants/onboard",
        json={**base_payload, "kyc_doc_url": too_many_docs},
        headers=headers,
    )
    assert res_many_docs.status_code == 422

