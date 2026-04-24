from fastapi import FastAPI

app = FastAPI(title="AI System API")


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "FastAPI server is running"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
