import xml.etree.ElementTree as ET

# Hàm tạo XML format cho Moodle
def create_moodle_xml(questions):
    """Create Moodle XML from question list.

    Args:
        questions (list[dict]): list of questions.

    Returns:
        str: XML content as string.
    """
    quiz = ET.Element('quiz')

    for question in questions:
        question_el = ET.SubElement(quiz, 'question', type='multichoice')
        
        name_el = ET.SubElement(question_el, 'name')
        text_name_el = ET.SubElement(name_el, 'text')
        text_name_el.text = question['text']

        questiontext_el = ET.SubElement(question_el, 'questiontext', format='html')
        text_questiontext_el = ET.SubElement(questiontext_el, 'text')
        text_questiontext_el.text = f"<![CDATA[{question['text']}]]>"

        # Thêm các câu trả lời
        for answer in question['choices']:
            fraction = "100" if answer == question['correct_choice'] else "0"
            answer_el = ET.SubElement(question_el, 'answer', fraction=fraction)
            text_answer_el = ET.SubElement(answer_el, 'text')
            text_answer_el.text = answer
            feedback_el = ET.SubElement(answer_el, 'feedback')
            text_feedback_el = ET.SubElement(feedback_el, 'text')
            text_feedback_el.text = "Correct!" if answer == question['correct_choice'] else "Incorrect."

    # Tạo nội dung XML từ ElementTree
    xml_str = ET.tostring(quiz, encoding='unicode')
    return xml_str
