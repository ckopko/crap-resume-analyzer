from pydantic import BaseModel, Field
from typing import List, Literal, Optional

class Job(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    dates: Optional[str] = None
    location: Optional[str] = None
    bullets: List[str] = Field(default_factory=list)

class Education(BaseModel):
    degree: Optional[str] = None
    school: Optional[str] = None
    graduation_date: Optional[str] = None

class ResumeSection(BaseModel):
    section_title: str
    section_type: Literal["experience", "education", "skills_list", "summary", "projects", "unknown"]
    body: List[Job] | List[Education] | List[str] | str

class ParsedResume(BaseModel):
    file_name: Optional[str] = None
    sections: List[ResumeSection] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list, description="A list of warnings for text that could not be cleanly parsed.")

class ChangeInstruction(BaseModel):
    type: Literal["edit", "add", "remove"]
    path: str = Field(..., description="A path to the item to be changed, e.g., 'sections[0].body[1].bullets[2]'")
    original_text: Optional[str] = None
    suggested_text: Optional[str] = None
    reason: str = Field(..., description="The AI's justification for the change.")

class AIAnalysis(BaseModel):
    overall_summary: str = Field(..., description="A brief, high-level summary of the resume's strengths and weaknesses.")
    instructions: List[ChangeInstruction] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list, description="A list of warnings from the parsing and analysis stages.")