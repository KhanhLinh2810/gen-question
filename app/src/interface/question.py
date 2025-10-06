from pydantic import BaseModel
from typing import Optional

class AllAns(BaseModel):
    """All answers model."""
    ans1: str
    ans2: str
    ans3: str
    ans4: str

class IUpdateQuestion(BaseModel):
    """Update question model."""
    all_ans: AllAns
    context: str
    crct_ans: str
    question: str

# body classes for req n' res
# pylint: disable=too-few-public-methods
class ModelInput(BaseModel):
    """General request model structure for flutter incoming req."""
    uid: Optional[str] = None
    context: str
    name: str

class ICreateQuestion(BaseModel):
    context: str
    name: str

class IExportQuestion(BaseModel):
    """Request model for exporting questions."""
    uid: Optional[str] = None
    name: str