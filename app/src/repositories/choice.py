from src.loaders.database import get_database
from sqlalchemy import select, update, delete
from sqlalchemy.exc import IntegrityError
from typing import List



from models import Choice
from src.interface import ICreateRating

class ChoiceRepository:
    def __init__(self):
        self.db = get_database()

    # get many
    async def get_many_by_question_id(self, question_id: int) -> List[Choice]:
        query = (
            select(Choice)
            .where(
                Choice.question_id == question_id
            )
        )
        result = await self.db.execute(query)
        return result.scalar().all()