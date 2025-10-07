from src.loaders.database import get_database
from sqlalchemy import select, update, delete


from models import Question

class TopicRepository:
    def __init__(self):
        self.db = get_database()

    # update
    async def update_topic_of_list_question(self, user_id: int, old_topic: str, new_topic: str):
        update_query = (
                update(Question)
                .where(Question.topic == old_topic, Question.user_id == user_id)
                .values(topic=new_topic)
            )
        await self.db.execute(update_query)
        await self.db.commit()

    # delete
    async def delete_question_by_topic(self, user_id: int, topic: str) -> bool:
        await self.db.execute(
            delete(Question).where(Question.user_id == user_id, Question.topic == topic)
        )
        await self.db.commit()
   
    # validate
    