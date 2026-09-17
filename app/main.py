import time
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.chat import router as chat_router


app = FastAPI()
app.include_router(chat_router)


@app.middleware("http")
async def request_logging_middleware(request : Request, call_next):
    print('methog:', request.method)
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    response.headers["X-Request-ID"] = str(uuid.uuid4())
    print('status code:', response.status_code)
    return response


@app.middleware("http")
async def error_middleware(request : Request, call_next):
    
    try : 
        response = await call_next(request)
        return response
    except Exception as e :
        return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})
    


@app.get("/health")
def health_check():
    return {"status": "ok"}


    raise Exception("Something went wrong")