from fastapi.responses import JSONResponse

def res_ok(data: dict = None, code: str = "SUCCESS",
           page: int = None, limit: int = None, total_items: int = None):

    response = {
        "code": code,
        "message": code,
        "data": data or {}
    }

    if page is not None and limit is not None and total_items is not None:
        total_pages = int(total_items/limit)
        response["meta"] = {
            "total_pages": total_pages,
            "total_items": total_items,
            "limit": limit,
            "page": page
        }

    return response
