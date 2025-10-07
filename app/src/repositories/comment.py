from src.loaders.database import get_database
from sqlalchemy import select, update, delete
from fastapi import HTTPException


from models import Comment
from src.interface import ICreateComment

class CommentRepository:
    def __init__(self):
        self.db = get_database()

    # create
    async def create_comment(self, user_id: int, params: ICreateComment):
        new_comment = Comment(
            user_id=user_id,
            question_id=params.question_id,
            comment_text=params.comment_text,
        )
        await self.db.add()
        self.db.add(new_comment)
        await self.db.commit()
        await self.db.refresh(new_comment)
        return new_comment

    # get one
    async def find_by_pk(self, comment_id: int) -> Comment | None:
        query = (
            select(Comment)
            .where(
                Comment.id == comment_id
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    # update
    async def update(self, comment_id: int, comment_text: str):
        query = (
            update(Comment)
            .where(
                Comment.id == comment_id
            )
            .values(
                comment_text=comment_text
            )
        )

        await self.db.execute(query)
        await self.db.commit()

    # delete
    async def delete_by_id(self, comment_id: int) -> bool:
        result = await self.db.execute(
            delete(Comment)
            .where(
                Comment.id == comment_id
            )
        )
        await self.db.commit()
        return result
   
    # validate
    async def find_or_fail(self, comment_id: int):
        comment = await self.find_by_pk(comment_id)
        if not comment:
            raise HTTPException(status_code=400, detail="comment.not_found")
        return comment
        
    async def find_and_check_authority(self, user_id: int, comment_id: int):
        comment = await self.find_or_fail(comment_id)
        if comment.user_id != user_id:
            raise HTTPException(status_code=400, detail="comment.not_found")
        return comment