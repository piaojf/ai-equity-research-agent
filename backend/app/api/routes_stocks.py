from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.request_id import get_request_id
from app.schemas.common import ApiResponse
from app.schemas.market import StockOverview, StockSearchItem
from app.services.market import MarketService, get_market_service
from app.services.universe import StockUniverseService, get_stock_universe_service

router = APIRouter(prefix="/api/stocks", tags=["market"])


@router.get(
    "/search",
    response_model=ApiResponse[list[StockSearchItem]],
)
async def search_stocks(
    service: Annotated[StockUniverseService, Depends(get_stock_universe_service)],
    q: str = Query(default="", max_length=64),
    limit: int = Query(default=10, ge=1, le=20),
) -> ApiResponse[list[StockSearchItem]]:
    return ApiResponse(
        request_id=get_request_id(),
        data=await service.search(q, limit),
    )


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
