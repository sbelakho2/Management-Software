"""Sensei API v1 Router."""

from fastapi import APIRouter

from sensei.api.v1.endpoints import (
    health,
    auth,
    users,
    accounts,
    contacts,
    products,
    rfqs,
    opportunities,
    quotes,
    work_centers,
    work_orders,
    production_cells,
)

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(accounts.router, prefix="/accounts", tags=["Accounts"])
api_router.include_router(contacts.router, prefix="/contacts", tags=["Contacts"])
api_router.include_router(products.router, prefix="/products", tags=["Products"])
api_router.include_router(rfqs.router, prefix="/rfqs", tags=["RFQs"])
api_router.include_router(opportunities.router, prefix="/opportunities", tags=["Opportunities"])
api_router.include_router(quotes.router, prefix="/quotes", tags=["Quotes"])
api_router.include_router(work_centers.router, prefix="/work-centers", tags=["Work Centers"])
api_router.include_router(work_orders.router, prefix="/work-orders", tags=["Work Orders"])
api_router.include_router(production_cells.router, prefix="/production-cells", tags=["Production Cells"])
