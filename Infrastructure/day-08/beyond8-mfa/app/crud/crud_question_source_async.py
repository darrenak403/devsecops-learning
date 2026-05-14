from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.crud_question_source import CRUDQuestionSource
from app.models.question import Question
from app.models.question_source import ParseStatus, QuestionSource
from app.models.subject import Subject


class CRUDQuestionSourceAsync:
    def __init__(self) -> None:
        self._sync_crud = CRUDQuestionSource()

    async def list_subjects_async(self, db: AsyncSession) -> list[Subject]:
        result = await db.execute(select(Subject).where(Subject.is_active.is_(True)).order_by(Subject.code.asc()))
        return list(result.scalars().all())

    async def get_source_state_async(self, db: AsyncSession, slug: str) -> tuple[list[QuestionSource], dict[str, list[dict]]]:
        query = (
            select(QuestionSource, Question)
            .join(Subject, QuestionSource.subject_id == Subject.id)
            .outerjoin(Question, QuestionSource.id == Question.source_id)
            .where(
                Subject.slug == slug,
                Subject.is_active.is_(True),
                QuestionSource.is_deleted.is_(False),
                QuestionSource.parse_status == ParseStatus.SUCCESS.value,
            )
            .order_by(QuestionSource.uploaded_at.desc(), QuestionSource.id.desc(), Question.ordinal.asc())
        )
        rows = (await db.execute(query)).all()
        sources_dict: dict[str, QuestionSource] = {}
        questions_by_source: dict[str, list[dict]] = {}
        for source, question in rows:
            sid = source.id
            if sid not in sources_dict:
                sources_dict[sid] = source
                questions_by_source[sid] = []
            if question is not None:
                questions_by_source[sid].append(
                    {
                        "ordinal": int(question.ordinal or 0),
                        "stem": question.stem,
                        "options": question.options_json or [],
                        "answer": question.answer_text,
                    }
                )
        return list(sources_dict.values()), questions_by_source

    async def get_subject_decks_async(
        self, db: AsyncSession, slug: str, user_id: str | None = None
    ) -> tuple[list[QuestionSource], dict[str, dict]]:
        def _sync(session):
            return self._sync_crud.get_subject_decks_optimized(session, slug, user_id)

        return await db.run_sync(_sync)


crud_question_source_async = CRUDQuestionSourceAsync()
