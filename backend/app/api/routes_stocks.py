from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.request_id import get_request_id
from app.schemas.common import ApiResponse
from app.schemas.market import StockOverview
from app.services.market import MarketService, get_market_service

router = APIRouter(prefix="/api/stocks", tags=["market"])


@router.get(
    "/{ticker}",
    response_model=ApiResponse[StockOverview],
)
async def get_stock_overview(
    ticker: str,
    service: Annotated[MarketService, Depends(get_market_service)],
) -> ApiResponse[StockOverview]:
    return ApiResponse(
        request_id=get_request_id(),
        data=await service.get_stock_overview(ticker),
    )
