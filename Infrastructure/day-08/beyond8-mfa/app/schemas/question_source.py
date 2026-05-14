from pydantic import BaseModel, Field, model_validator


class UploadSourceResponse(BaseModel):
    sourceId: str
    subjectSlug: str
    subjectCode: str
    examCode: str
    fileName: str
    checksum: str
    questionCount: int
    warnings: list[str]
    deduplicated: bool = False


class SubjectSummary(BaseModel):
    slug: str
    code: str
    hint: str
    bankQuestionCount: int = Field(
        default=0,
        description="Tổng số câu trong ngân hàng (source `cau-hoi-tong-hop`; nếu chưa có thì fallback như GET bank).",
    )


class AdminEnsureSubjectRequest(BaseModel):
    """Create subject by slug if missing (idempotent); same codes as list subjects."""

    slug: str = Field(min_length=1, max_length=64)


class AdminSourceSummary(BaseModel):
    sourceId: str
    examCode: str
    fileName: str
    questionCount: int
    isAggregatedBank: bool
    uploadedAt: str | None = None


class SourceStateQuestion(BaseModel):
    id: int
    stem: str
    options: list[dict]
    answer: str


class DeckQuestionsPage(BaseModel):
    """Paginated slice of deck questions; `id` on each item is 1-based index in deck order (same as non-paginated GET)."""

    items: list[SourceStateQuestion]
    page: int
    limit: int
    total: int
    totalPages: int
    hasNext: bool
    hasPrevious: bool


class SourceFileMeta(BaseModel):
    class SourceRange(BaseModel):
        start: int
        end: int

    fileName: str
    isEmpty: bool
    questionCount: int
    range: SourceRange


class SourceStateResponse(BaseModel):
    bankQuestions: list[SourceStateQuestion]
    deckQuestions: list[SourceStateQuestion]
    files: list[SourceFileMeta]
    hocTheoDeLayout: str


class DeckProgressStats(BaseModel):
    total: int
    inProgress: int
    completed: int
    learnedCount: int
    completionRatePercent: int


class SubjectDeck(BaseModel):
    deckId: str
    examCode: str
    fileName: str
    questionCount: int
    stats: DeckProgressStats
    uploadedAt: str | None = None


class SourceQuestionOptionInput(BaseModel):
    label: str
    text: str


class SourceQuestionUpdateInput(BaseModel):
    stem: str
    options: list[SourceQuestionOptionInput]
    answer: str


class SourceQuestionBulkUpdateRequest(BaseModel):
    questions: list[SourceQuestionUpdateInput]


class AdminPatchQuestionRequest(BaseModel):
    """At least one field must be set."""

    stem: str | None = None
    options: list[SourceQuestionOptionInput] | None = None
    answer: str | None = None

    @model_validator(mode="after")
    def at_least_one_field(self) -> "AdminPatchQuestionRequest":
        if self.stem is None and self.options is None and self.answer is None:
            raise ValueError("At least one of stem, options, or answer is required.")
        return self


class DeckStatsUpdateRequest(BaseModel):
    inProgress: int = Field(ge=0, le=10000)
    completed: int = Field(ge=0, le=10000)


class DeckProgressUpdateRequest(BaseModel):
    currentQuestion: int = Field(ge=0, le=10000)
    attemptedQuestionOrdinals: list[int] = Field(default_factory=list, max_length=10000)


class DeckProgressResponse(BaseModel):
    currentQuestion: int
    attemptedQuestionOrdinals: list[int]
    updatedAt: str | None = None


class AnswerCheckRequest(BaseModel):
    selectedAnswer: str = Field(min_length=1)


class AnswerCheckResponse(BaseModel):
    questionId: int
    selectedAnswer: str
    correctAnswers: list[str]
    isCorrect: bool


class MergeBankPreviewResponse(BaseModel):
    """Dry-run merge of a deck source into the aggregated bank (no DB writes)."""

    subjectSlug: str
    deckSourceId: str
    added: int
    skippedDuplicate: int
    bankQuestionCountAfter: int
    wouldCreateBank: bool = False


class MergeIntoBankResponse(BaseModel):
    """Committed merge of deck questions into `cau-hoi-tong-hop` source for the subject."""

    subjectSlug: str
    bankSourceId: str
    deckSourceId: str
    added: int
    skippedDuplicate: int
    bankQuestionCount: int


class BankCheckDuplicateRequest(BaseModel):
    """One question payload; hash is computed server-side to match `cau-hoi-tong-hop` dedupe."""

    stem: str
    options: list[SourceQuestionOptionInput]
    answer: str


class BankCheckDuplicateResponse(BaseModel):
    normalizedHash: str
    existsInBank: bool


class AdminAppendQuestionResponse(BaseModel):
    sourceId: str
    subjectSlug: str
    examCode: str
    fileName: str
    ordinal: int
    questionCount: int
    warnings: list[str]


class AdminDeleteQuestionResponse(BaseModel):
    sourceId: str
    subjectSlug: str
    examCode: str
    fileName: str
    questionCount: int
