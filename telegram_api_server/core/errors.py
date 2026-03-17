from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse


class BusinessError(Exception):
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(BusinessError)
    async def _business(_: Request, exc: BusinessError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"success": False, "error": exc.message})

    @app.exception_handler(HTTPException)
    async def _http(_: Request, exc: HTTPException) -> JSONResponse:
        if exc.status_code == 401 and isinstance(exc.detail, dict):
            return JSONResponse(status_code=401, content=exc.detail)
        return JSONResponse(status_code=exc.status_code, content={"success": False, "error": str(exc.detail)})

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=500, content={"success": False, "error": str(exc)})
