from deep_translator import GoogleTranslator

# Dịch vietnamese -> english
def vietnamese_to_english(text):
    translator = GoogleTranslator(source='vi', target='en')
    translated_text = translator.translate(text)
    return translated_text

def english_to_vietnamese(text):
    translator = GoogleTranslator(source='en', target='vi')
    translated_text = translator.translate(text)
    return translated_text