"""
This module contains all tasks related to transformer model
Refactored to use Hugging Face Flan-T5 (no fastT5 dependency)

@Author: Karthick T. Sharma
@Modified: LinhGPT
"""

import os
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM


class Model:
    """Generalized T5/Flan-T5 model for text generation."""

    def __init__(self, model_name: str = "google/flan-t5-base"):
        """
        Load model and tokenizer into memory.

        Args:
            model_name (str): Name or path of the Hugging Face model.
        """
        os.environ["TOKENIZERS_PARALLELISM"] = "false"

        print(f"🔹 Loading model: {model_name} ...")
        self.__tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.__model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
        print("✅ Model and tokenizer loaded successfully.\n")

    def tokenize_corpus(self, text: str, max_length: int):
        """Tokenize model input text."""
        encode = self.__tokenizer.encode_plus(
            text,
            return_tensors="pt",
            max_length=max_length,
            truncation=True,
            padding="max_length",
        )
        return encode["input_ids"], encode["attention_mask"]

    def __extract_dict(self, input_dict):
        """Extract key-value pairs into a string format."""
        return " ".join(f"{k}: {v}" for k, v in input_dict.items())

    def inference(
        self,
        num_beams: int = 4,
        no_repeat_ngram_size: int = 2,
        model_max_length: int = 128,
        num_return_sequences: int = 1,
        token_max_length: int = 256,
        **kwargs,
    ):
        """
        Generate model output text.
        """
        text = self.__extract_dict(kwargs)
        input_ids, attention_mask = self.tokenize_corpus(text, token_max_length)

        outputs = self.__model.generate(
            input_ids=input_ids,
            attention_mask=attention_mask,
            num_beams=num_beams,
            num_return_sequences=num_return_sequences,
            no_repeat_ngram_size=no_repeat_ngram_size,
            max_length=model_max_length,
            early_stopping=True,
        )

        decoded = [
            self.__tokenizer.decode(
                output, skip_special_tokens=True, clean_up_tokenization_spaces=True
            )
            for output in outputs
        ]

        return decoded[0] if num_return_sequences == 1 else decoded
