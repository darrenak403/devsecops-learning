python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 3636
taskkill //F //IM python.exe

permanent

rtk gain
rtk gain --history

migrate:

# 1) BE: chạy test

cd /Users/ngothanhdat/Documents/CODE/beyond8-quiz/be/beyond8-mfa
python -m pytest app/tests/... -q

# 2) BE: chạy migration (nếu có)

cd /Users/ngothanhdat/Documents/CODE/beyond8-quiz/be/beyond8-mfa
alembic upgrade head

alembic current
alembic heads

# 3) FE: check type

cd /Users/ngothanhdat/Documents/CODE/beyond8-quiz/be/beyond8-mfa-fe
npx tsc --noEmit

# 4) FE: lint nhanh các file liên quan

cd /Users/ngothanhdat/Documents/CODE/beyond8-quiz/be/beyond8-mfa-fe
npx eslint "app/admin/deck-markdown/page.tsx" "hooks/useQuestionSources.ts" "lib/api/services/fetchQuestionSources.ts" "lib/questionMarkdown/index.ts"

# 5) FE: chạy local

cd /Users/ngothanhdat/Documents/CODE/beyond8-quiz/be/beyond8-mfa-fe
npm run dev
