"""Account-owned visual catalogs. Image bytes remain private to the API."""

import base64
import binascii
import logging
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.database.models import Analysis, Campaign, GeneratedAsset, Product, StudioDraft
from app.database.session import get_session
from app.integrations.image_storage import ImageStorage, get_image_storage
from app.modules.auth.router import current_user_id
from app.modules.studio.router import GenerateImagesRequest, _image_bytes, draft_original_filename, generate_images, stream_image

router = APIRouter(prefix="/api/v1/catalogs", tags=["catalogs"])
logger = logging.getLogger(__name__)
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_ASSET_BYTES = 10 * 1024 * 1024
MAX_ASSET_BASE64 = ((MAX_ASSET_BYTES + 2) // 3) * 4
EXTENSIONS = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}


class CatalogAssetInput(BaseModel):
    label: str = Field(min_length=1, max_length=120)
    image_base64: str = Field(min_length=1, max_length=MAX_ASSET_BASE64)
    favorite: bool = False


class CatalogSourceInput(BaseModel):
    analysis_id: UUID
    product_id: UUID


class CatalogCreate(BaseModel):
    configuration: GenerateImagesRequest
    original_name: str = Field(min_length=1, max_length=160)
    assets: list[CatalogAssetInput] = Field(min_length=1, max_length=4)
    source: CatalogSourceInput | None = None


class CatalogFromDraft(BaseModel):
    draft_id: UUID
    selected_ids: list[UUID] = Field(default_factory=list, max_length=4)
    source: CatalogSourceInput | None = None


class FavoriteUpdate(BaseModel):
    favorite: bool


def _storage(settings: Settings) -> ImageStorage:
    return get_image_storage(settings)


def _campaign(session: Session, user_id: UUID, campaign_id: UUID, *, include_deleted: bool = False) -> Campaign:
    row = session.scalar(select(Campaign).where(Campaign.id == campaign_id, Campaign.user_id == user_id))
    if row is None or (row.status != "active" and not (include_deleted and row.status == "deleted")):
        raise HTTPException(404, "El catálogo no está disponible.")
    return row


def _asset(session: Session, campaign_id: UUID, asset_id: UUID) -> GeneratedAsset:
    row = session.scalar(select(GeneratedAsset).where(
        GeneratedAsset.id == asset_id, GeneratedAsset.campaign_id == campaign_id,
    ))
    if row is None:
        raise HTTPException(404, "La imagen no está disponible.")
    return row


def _asset_bytes(encoded: str) -> bytes:
    try:
        image = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(422, "La imagen generada no se pudo leer.") from None
    if not image.startswith(PNG_SIGNATURE) or len(image) > MAX_ASSET_BYTES:
        raise HTTPException(422, "La imagen generada debe ser PNG y pesar como máximo 10 MB.")
    return image


def _read(session: Session, campaign: Campaign) -> dict:
    assets = session.scalars(select(GeneratedAsset).where(
        GeneratedAsset.campaign_id == campaign.id,
    ).order_by(GeneratedAsset.created_at, GeneratedAsset.id)).all()
    return {
        "id": campaign.id, "name": campaign.name, "product_name": campaign.product_name,
        "configuration": {
            "product_name": campaign.product_name,
            "product_description": campaign.product_description or "",
            "style": campaign.style, "scene": campaign.scene,
            "lighting": campaign.lighting, "aspect_ratio": campaign.aspect_ratio,
            "variations": campaign.variations,
        },
        "original_url": campaign.original_image_url,
        "original_name": campaign.original_image_name,
        "original_mime_type": campaign.original_image_content_type,
        "source": {
            "analysis_id": campaign.source_analysis_id,
            "product_id": campaign.source_product_id,
            "product_title": campaign.source_product_title,
        } if campaign.source_analysis_id and campaign.source_product_title else None,
        "created_at": campaign.created_at,
        "assets": [{
            "id": asset.id, "label": asset.label, "url": asset.image_url,
            "favorite": asset.is_favorite,
        } for asset in assets],
    }


def _persist_catalog(payload: CatalogCreate, user_id: UUID, session: Session,
                     settings: Settings, *, commit: bool) -> dict:
    storage = _storage(settings)
    source_product = None
    if payload.source:
        analysis = session.get(Analysis, payload.source.analysis_id)
        if analysis is None or analysis.user_id != user_id:
            raise HTTPException(404, "La investigación de origen no está disponible.")
        source_product = session.get(Product, payload.source.product_id)
        if source_product is None or source_product.analysis_id != analysis.id:
            raise HTTPException(404, "El producto de origen ya no está disponible en esa investigación.")
    original = _image_bytes(payload.configuration)
    images = [_asset_bytes(asset.image_base64) for asset in payload.assets]
    campaign_id = uuid4()
    original_filename = f"original.{EXTENSIONS[payload.configuration.image_mime_type]}"
    prefix = f"/api/v1/catalogs/{campaign_id}"
    campaign = Campaign(
        id=campaign_id, user_id=user_id,
        source_analysis_id=payload.source.analysis_id if payload.source else None,
        source_product_id=source_product.id if source_product else None,
        source_product_title=source_product.title if source_product else None,
        name=f"{payload.configuration.product_name} · {payload.configuration.style}",
        product_name=payload.configuration.product_name,
        product_description=payload.configuration.product_description,
        style=payload.configuration.style, scene=payload.configuration.scene,
        lighting=payload.configuration.lighting, aspect_ratio=payload.configuration.aspect_ratio,
        variations=payload.configuration.variations,
        original_image_url=f"{prefix}/original",
        original_image_name=payload.original_name,
        original_image_content_type=payload.configuration.image_mime_type,
        status="active",
    )
    files = [(original_filename, original)]
    session.add(campaign)
    for data, image in zip(payload.assets, images, strict=True):
        asset_id = uuid4()
        files.append((f"asset-{asset_id}.png", image))
        session.add(GeneratedAsset(
            id=asset_id, campaign_id=campaign_id, label=data.label,
            image_url=f"{prefix}/assets/{asset_id}/image", is_favorite=data.favorite,
        ))
    written: list[str] = []
    try:
        for filename, image in files:
            storage.put(user_id, campaign_id, filename, image)
            written.append(filename)
        if commit:
            session.commit()
        else:
            session.flush()
    except Exception:
        session.rollback()
        for filename in written:
            try:
                storage.delete(user_id, campaign_id, filename)
            except Exception:
                logger.warning("Could not remove catalog image after a failed save", exc_info=True)
        raise
    return _read(session, campaign)


@router.post("", status_code=201)
def create_catalog(
    payload: CatalogCreate,
    user_id: UUID = Depends(current_user_id),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict:
    if settings.environment == "production":
        raise HTTPException(410, "Actualiza Estudio IA para usar el nuevo flujo de imágenes.")
    return _persist_catalog(payload, user_id, session, settings, commit=True)


@router.post("/from-draft", status_code=201)
def create_catalog_from_draft(
    payload: CatalogFromDraft,
    user_id: UUID = Depends(current_user_id),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict:
    draft = session.get(StudioDraft, payload.draft_id)
    if draft is None or draft.user_id != user_id or draft.status != "generated":
        raise HTTPException(404, "El borrador no está disponible.")
    from datetime import datetime, timezone
    expires = draft.expires_at if draft.expires_at.tzinfo else draft.expires_at.replace(tzinfo=timezone.utc)
    if expires <= datetime.now(timezone.utc):
        raise HTTPException(410, "El borrador venció. Genera las vistas de nuevo.")
    preview_map = {UUID(item["id"]): item for item in draft.preview_ids}
    selected = set(payload.selected_ids)
    if len(selected) != len(payload.selected_ids) or not selected.issubset(preview_map):
        raise HTTPException(422, "Selecciona vistas válidas de este borrador.")
    included = [asset_id for asset_id in preview_map if not selected or asset_id in selected]
    if not included:
        raise HTTPException(422, "El borrador no tiene vistas para guardar.")
    storage = _storage(settings)
    original = storage.read(user_id, draft.id, draft_original_filename(draft))
    assets = [CatalogAssetInput(
        label=preview_map[asset_id]["label"],
        image_base64=base64.b64encode(storage.read(user_id, draft.id, f"asset-{asset_id}.png")).decode(),
        favorite=asset_id in selected,
    ) for asset_id in included]
    config = draft.configuration or {}
    saved = _persist_catalog(CatalogCreate(
        configuration=GenerateImagesRequest(
            image_base64=base64.b64encode(original).decode(), image_mime_type=draft.original_mime_type,
            **config,
        ), original_name=draft.original_name, assets=assets, source=payload.source,
    ), user_id, session, settings, commit=False)
    try:
        draft.status = "saved"
        session.commit()
    except Exception:
        session.rollback()
        filenames = [draft_original_filename(draft)]
        filenames.extend(f"asset-{item['id']}.png" for item in saved["assets"])
        for filename in filenames:
            try:
                storage.delete(user_id, saved["id"], filename)
            except Exception:
                logger.warning("Could not clean failed catalog save", exc_info=True)
        raise
    for filename in [draft_original_filename(draft), *(f"asset-{item['id']}.png" for item in draft.preview_ids)]:
        try:
            storage.delete(user_id, draft.id, filename)
        except Exception:
            logger.warning("Could not clean saved Studio draft", exc_info=True)
    return saved


@router.get("")
def list_catalogs(
    user_id: UUID = Depends(current_user_id),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> list[dict]:
    _storage(settings)
    campaigns = session.scalars(select(Campaign).where(
        Campaign.user_id == user_id, Campaign.status == "active",
    ).order_by(Campaign.created_at.desc(), Campaign.id.desc())).all()
    return [_read(session, campaign) for campaign in campaigns]


@router.get("/{campaign_id}")
def get_catalog(
    campaign_id: UUID,
    user_id: UUID = Depends(current_user_id),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict:
    _storage(settings)
    return _read(session, _campaign(session, user_id, campaign_id))


@router.get("/{campaign_id}/original")
def get_original(
    campaign_id: UUID,
    user_id: UUID = Depends(current_user_id),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> Response:
    campaign = _campaign(session, user_id, campaign_id)
    storage = _storage(settings)
    filename = f"original.{EXTENSIONS[campaign.original_image_content_type]}"
    return stream_image(storage.read(user_id, campaign_id, filename), campaign.original_image_content_type)


@router.get("/{campaign_id}/assets/{asset_id}/image")
def get_asset_image(
    campaign_id: UUID, asset_id: UUID,
    user_id: UUID = Depends(current_user_id),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> Response:
    _campaign(session, user_id, campaign_id)
    _asset(session, campaign_id, asset_id)
    return stream_image(_storage(settings).read(user_id, campaign_id, f"asset-{asset_id}.png"), "image/png")


@router.put("/{campaign_id}/assets/{asset_id}/favorite")
def update_favorite(
    campaign_id: UUID, asset_id: UUID, payload: FavoriteUpdate,
    user_id: UUID = Depends(current_user_id),
    session: Session = Depends(get_session),
) -> dict:
    _campaign(session, user_id, campaign_id)
    asset = _asset(session, campaign_id, asset_id)
    asset.is_favorite = payload.favorite
    session.commit()
    return {"favorite": asset.is_favorite}


@router.delete("/{campaign_id}", status_code=204)
def delete_catalog(
    campaign_id: UUID, user_id: UUID = Depends(current_user_id),
    session: Session = Depends(get_session),
) -> None:
    campaign = _campaign(session, user_id, campaign_id)
    campaign.status = "deleted"
    session.commit()


@router.post("/{campaign_id}/restore")
def restore_catalog(
    campaign_id: UUID, user_id: UUID = Depends(current_user_id),
    session: Session = Depends(get_session),
) -> dict:
    campaign = _campaign(session, user_id, campaign_id, include_deleted=True)
    campaign.status = "active"
    session.commit()
    return _read(session, campaign)


def _generate_for_campaign(campaign: Campaign, user_id: UUID, storage: ImageStorage, settings: Settings) -> bytes:
    filename = f"original.{EXTENSIONS[campaign.original_image_content_type]}"
    original = storage.read(user_id, campaign.id, filename)
    request = GenerateImagesRequest(
        image_base64=base64.b64encode(original).decode(),
        image_mime_type=campaign.original_image_content_type,
        product_name=campaign.product_name,
        product_description=campaign.product_description or "",
        style=campaign.style, scene=campaign.scene, lighting=campaign.lighting,
        aspect_ratio=campaign.aspect_ratio, variations=1,
    )
    generated = generate_images(request, settings)
    return _asset_bytes(generated.images[0].image_base64)


@router.post("/{campaign_id}/assets")
def add_asset(
    campaign_id: UUID, user_id: UUID = Depends(current_user_id),
    session: Session = Depends(get_session), settings: Settings = Depends(get_settings),
) -> dict:
    campaign = _campaign(session, user_id, campaign_id)
    assets = session.scalars(select(GeneratedAsset).where(GeneratedAsset.campaign_id == campaign_id)).all()
    if len(assets) >= 4:
        raise HTTPException(409, "Este catálogo ya tiene cuatro imágenes.")
    storage = _storage(settings)
    image = _generate_for_campaign(campaign, user_id, storage, settings)
    asset_id = uuid4()
    filename = f"asset-{asset_id}.png"
    prefix = f"/api/v1/catalogs/{campaign_id}"
    storage.put(user_id, campaign_id, filename, image)
    session.add(GeneratedAsset(
        id=asset_id, campaign_id=campaign_id, label=f"Escena {len(assets) + 1}",
        image_url=f"{prefix}/assets/{asset_id}/image", is_favorite=False,
    ))
    try:
        session.commit()
    except Exception:
        session.rollback()
        try:
            storage.delete(user_id, campaign_id, filename)
        except Exception:
            logger.warning("Could not remove catalog image after a failed save", exc_info=True)
        raise
    return _read(session, campaign)


@router.post("/{campaign_id}/assets/{asset_id}/regenerate")
def regenerate_asset(
    campaign_id: UUID, asset_id: UUID,
    user_id: UUID = Depends(current_user_id), session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict:
    campaign = _campaign(session, user_id, campaign_id)
    _asset(session, campaign_id, asset_id)
    storage = _storage(settings)
    image = _generate_for_campaign(campaign, user_id, storage, settings)
    storage.put(user_id, campaign_id, f"asset-{asset_id}.png", image)
    return _read(session, campaign)
