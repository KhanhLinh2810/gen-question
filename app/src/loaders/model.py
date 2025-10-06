from src.ansgenerator.false_answer_generator import FalseAnswerGenerator
from src.model.abstractive_summarizer import AbstractiveSummarizer
from src.model.question_generator import QuestionGenerator
from src.model.keyword_extractor import KeywordExtractor

# initialize question and ans models
summarizer = AbstractiveSummarizer()
question_gen = QuestionGenerator()
false_ans_gen = FalseAnswerGenerator()
keyword_extractor = KeywordExtractor()