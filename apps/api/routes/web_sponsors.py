from fastapi import APIRouter

router = APIRouter()


@router.get("/sponsors")
def get_sponsors():
    return {"ok": True, "resource": "sponsors", "tiers": [], "wall": []}
