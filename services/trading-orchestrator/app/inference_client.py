import httpx

from app.models import Prediction


async def predict(inference_api_url: str, symbol: str, features: dict) -> Prediction:
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            f"{inference_api_url.rstrip('/')}/predict",
            json={"symbol": symbol, "features": features},
        )
        response.raise_for_status()
        return Prediction.model_validate(response.json())
