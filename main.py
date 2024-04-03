from contextlib import asynccontextmanager
import time

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

import utils_resource
from containers import Container
from offers import offers_resource
from products import product_resource
from recipes import recipe_resource
from shopping_list import shopping_list_resource
from stores import store_resource


def create_app() -> FastAPI:
    container = Container()
    container.wire(modules=[__name__, product_resource, store_resource, recipe_resource, utils_resource, offers_resource, shopping_list_resource])

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await container.init_resources()
        grocy_index = await container.grocy_index()
        if (time.time() - grocy_index.product_ix.last_modified()) > 900:
            await grocy_index.update_product_index()
        if (time.time() - grocy_index.qu_ix.last_modified()) > 900:
            await grocy_index.update_qu_index()
        yield
        # Clean up the ML models and release the resources
        await container.shutdown_resources()

    app = FastAPI(docs_url="/api/docs", redoc_url="/api/redoc", openapi_url="/api/openapi.json", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"],
                       allow_headers=["*"], )
    app.container = container

    app.mount("/static", StaticFiles(directory="static"), name="static")
    app.include_router(product_resource.router, prefix="/api/products", tags=['Products'])
    app.include_router(store_resource.router, prefix="/api/stores", tags=['Stores'])
    app.include_router(recipe_resource.router, prefix="/api/recipes", tags=['Recipes'])
    app.include_router(utils_resource.router, prefix="/api/utils", tags=['Utils'])
    app.include_router(offers_resource.router, prefix="/api/offers", tags=['Offers'])
    app.include_router(shopping_list_resource.router, prefix="/api/shopping_list", tags=['Shopping List'])
    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    app = create_app()
    uvicorn.run(app=app, host="0.0.0.0", port=8000, reload=True)
