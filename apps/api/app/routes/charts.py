"""Chart style catalog routes."""

from fastapi import APIRouter, Security
from seal_charts.styles import get_style_catalog

from app.schemas import ChartColorSchemeInfo, ChartStylesResponse, ChartStyleTemplateInfo
from app.security import require_api_key

router = APIRouter()


@router.get("/charts/styles", response_model=ChartStylesResponse)
async def list_chart_styles(_: None = Security(require_api_key)) -> ChartStylesResponse:
    """Return available chart templates and color schemes."""
    catalog = get_style_catalog()
    return ChartStylesResponse(
        templates=[ChartStyleTemplateInfo(**t) for t in catalog["templates"]],
        color_schemes=[ChartColorSchemeInfo(**s) for s in catalog["color_schemes"]],
    )
