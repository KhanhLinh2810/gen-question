from src.loaders.database import get_database
from sqlalchemy import select, update, delete
from sqlalchemy.orm import selectinload
from fastapi import HTTPException
from typing import List, Dict

import uuid



from models import Question, Choice, Comment, Rating
from src.utils import vietnamese_to_english, english_to_vietnamese
from src.loaders import summarizer, keyword_extractor, false_ans_gen, question_gen
from src.inferencehandler import inference_handler
from .user import UserRepository

class QuestionRepository:
    def __init__(self):
        self.db = get_database()
        self.user_repo = UserRepository()

    # create
    async def generate_and_store_questions(self, request):
        """Generate questions from user request and store results in Firestore.

        Args:
            request (ModelInput): request from flutter.

        Returns:
            dict: results saved to Firestore
        """
        request.context = vietnamese_to_english(request.context)
        request.name = vietnamese_to_english(request.name)

        await self.user_repo.update_generator_working_status(request, True)
        questions, crct_ans, all_ans = await self.generate_questions_and_answers(request.context)
        await self.user_repo.update_generator_working_status(request, False)

        results = self.send_results_to_db(request, questions, crct_ans, all_ans, request.context)
        return results

    # get one
    async def find_by_pk(self, question_id: int) -> Question | None:
        query = (
            select(Question)
            .where(
                Question.id == question_id
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    # get many
    async def get_many(self, keyword: str) -> List[Question]:
        query = (
            select(Question)
            .where(
                Question.question_text.ilike(f"%{keyword}%")
            )
        )
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_list_question_by_user_and_topic(self, user_id: int, topic: str) -> List[Dict[str, any]]:
        """Lấy câu hỏi từ MySQL dựa trên user id và topic.

        Args:
            user_id (int): ID người dùng.
            topic (str): Tên chủ đề.

        Returns:
            list[dict]: danh sách câu hỏi với các đáp án của chúng.
        """

        # Truy vấn câu hỏi từ cơ sở dữ liệu dựa trên user_id và topic
        query = (
            select(Question)
            .where(Question.user_id == user_id, Question.topic == topic)
            .options(selectinload(Question.choices), selectinload(Question.comments), selectinload(Question.ratings))
            )  # Tải sẵn các choices, comments và ratings
        result = await self.db.execute(query)
        list_question_db: List[Question] = result.scalars().all()  

        result = []
        for question in list_question_db:
            topic = question.topic
            # Lấy các lựa chọn của câu hỏi
            choices: List[Choice] = question.choices
            choices_text = [choice.choice_text for choice in choices] 

            # Lấy các bình luận cho câu hỏi
            comments: List[Comment] = question.comments
            comments_text = [comment.comment_text for comment in comments]
            
            # Lấy các đánh giá cho câu hỏi
            ratings: List[Rating] = question.ratings
            ratings_values = [rating.rating_value for rating in ratings]

            # Tính toán điểm trung bình
            average_rating = sum(ratings_values) / len(ratings_values) if ratings_values else 0

            question_data = {
                'text': question.question_text,
                'choices': choices_text,
                'correct_choice': question.correct_choice,
                'tags': question.tags,
                'comments': comments_text,  
                'ratings': ratings_values,    
                'average_rating': average_rating
            }
            result.append(question_data)

        return result
    
    # update
    async def update_question(self, user_id: int, question_id: int, new_info: dict) -> dict:
        # --- 1. Tách dữ liệu ---
        question_data = {
            key: value for key, value in new_info.items() 
            if key in {"context", "topic", "correct_choice", "question_text", "tags"}
        }
        choice_data = new_info.get("all_ans", [])

        # --- 2. Cập nhật bảng Question ---
        if question_data:
            stmt = (
                update(Question)
                .where(Question.user_id == user_id, Question.id == question_id)
                .values(**question_data)
            )
            result = await self.db.execute(stmt)

            # --- 3. Cập nhật bảng Choice ---
            if result.rowcount >  0 & choice_data:
                # Xóa tất cả choice cũ
                await self.db.execute(delete(Choice).where(Choice.question_id == question_id))

                # Thêm các choice mới
                new_choices = [
                    Choice(question_id=question_id, choice_text=text)
                    for text in choice_data
                ]
                self.db.add_all(new_choices)

        # --- 4. Commit toàn bộ ---
        await self.db.commit()


    

    # delete
    async def delete_by_id(self, user_id: int, question_id: int) -> bool:
        await self.find_and_check_authority(user_id, question_id)
        await self.db.execute(
            delete(Question).where(
                Question.id == question_id
            )
        )
        await self.db.commit()

    # validate
    async def find_or_fail(self, question_id: int):
        question = await self.find_by_pk(question_id)
        if not question:
            raise HTTPException(status_code=400, detail="question.not_found")
        return question
        
    async def find_and_check_authority(self, user_id: int, question_id: int):
        question = await self.find_or_fail(question_id)
        if question.user_id != user_id:
            raise HTTPException(status_code=400, detail="question.not_found")
        return question
    
    # other
    def generate_questions_and_answers(context: str):
        """Generate questions and answers from given context.

        Args:
            context (str): input corpus used to generate question.

        Returns:
            tuple[list[str], list[str], list[list[str]]]:
            questions, correct answers, and all answer choices.
        """
        summary, splitted_text = inference_handler.get_all_summary(
            model=summarizer, context=context
        )
        filtered_kws = keyword_extractor.get_keywords(
            original_list=splitted_text, summarized_list=summary
        )

        crct_ans, all_answers = false_ans_gen.get_output(filtered_kws=filtered_kws)
        questions = inference_handler.get_all_questions(
            model=question_gen, context=summary, answer=crct_ans
        )

        return questions, crct_ans, all_answers
    
    async def send_results_to_db(self, uid: str, topic: str, questions: list, crct_ans: list, all_ans: list, context: str, tags: list):
        """Gửi câu hỏi đã tạo vào cơ sở dữ liệu MySQL"""
        self.__validate(questions=questions, crct_ans=crct_ans, all_ans=all_ans)

        tags_str = ",".join(tags)  # Chuyển danh sách tags thành chuỗi phân cách bởi dấu phẩy

        results = []
        user_data = await self.get_username_from_uid(uid)
        for idx, question in enumerate(questions):
            new_question = Question(
                user_id=uid,
                topic=english_to_vietnamese(topic),
                question_text=english_to_vietnamese(question),
                context=english_to_vietnamese(context),
                correct_choice=english_to_vietnamese(crct_ans[idx]),
                tags=tags_str
            )
            self.db.add(new_question)
            await self.db.flush()  # Để lấy ID của câu hỏi

            # Lưu các lựa chọn câu trả lời
            choices = [
                english_to_vietnamese(all_ans[idx * 4 + i]) for i in range(4)
            ]
            for choice_text in choices:
                new_choice = Choice(
                    question_id=new_question.id,
                    choice_text=choice_text
                )
                self.db.add(new_choice)

            await self.db.commit()

            duplicate_info = await self.check_duplicates(uid, new_question.question_text, choices, new_question.id)
            results.append({
                'username': user_data,
                'question_id': new_question.id,
                'topic': new_question.topic,
                'context': new_question.context,
                'question_text': new_question.question_text,
                'choices': choices,
                'correct_choice': new_question.correct_choice,
                'tags': new_question.tags,
                'duplicate_info': duplicate_info
            })

        return results


        