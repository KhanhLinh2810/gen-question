from src.loaders.database import get_database
from sqlalchemy import select, update, delete
from sqlalchemy.exc import IntegrityError



from models import Rating
from src.interface import ICreateRating

class RatingRepository:
    def __init__(self):
        self.db = get_database()

    # create
    async def create_rating(self, user_id: int, params: ICreateRating):
        new_rating = Rating(
            user_id=user_id,
            question_id=params.question_id,
            rating_value=params.rating_value,
        )
        await self.db.add()
        self.db.add(new_rating)
        try:
            await self.db.commit()
            await self.db.refresh(new_rating)
            return new_rating
        except IntegrityError:
            await self.db.rollback()
            raise ValueError("rating.exist_rating")

    # get many
    async def get_one(self, user_id: int, question_id: int):
        query = (
            select(Rating)
            .where(
                Rating.user_id == user_id,
                Rating.question_id == question_id
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    # update
    async def update(self, user_id: int, params: ICreateRating):
        query = (
            update(Rating)
            .where(
                Rating.user_id == user_id,
                Rating.question_id == params.question_id
            )
            .values(
                rating_value=params.rating_value,
            )
        )

        await self.db.execute(query)
        await self.db.commit()

    # delete
    async def delete_by_user_and_question(self, user_id: int, question_id: int) -> bool:
        await self.db.execute(
            delete(Rating)
            .where(
                Rating.user_id == user_id,
                Rating.question_id == question_id
            )
        )
        await self.db.commit()
   
    # validate
    