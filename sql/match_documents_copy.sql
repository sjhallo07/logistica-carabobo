-- match_documents — pgvector / Supabase-ready implementation
-- Replaces array-based distance computation with pgvector operators and
-- adds an ivfflat index + an example RLS policy (owner or public). This file
-- assumes your table is `public.logistics_knowledge` and that it has the
-- following columns (common in Supabase setups):
--   - id         uuid
--   - content    text
--   - metadata   jsonb
--   - embedding  vector
--   - owner      uuid (optional; user id for RLS)
--   - is_public  boolean (optional)

-- 1) Nearest-neighbor search function (accepts a pgvector value)
CREATE OR REPLACE FUNCTION public.match_documents(
  match_count integer,
  match_threshold double precision,
  query_embedding vector
) RETURNS TABLE(id uuid, content text, metadata jsonb, distance double precision)
LANGUAGE sql
AS $$
  SELECT
    id,
    content,
    metadata,
    (embedding <-> query_embedding)::double precision AS distance
  FROM public.logistics_knowledge
  WHERE embedding IS NOT NULL
  ORDER BY embedding <-> query_embedding
  LIMIT match_count;
$$;

-- 2) Optional: create an index for fast ANN searches using ivfflat (L2)
DO $$
BEGIN
  -- Only attempt index creation if the table and column exist
  PERFORM 1 FROM public.logistics_knowledge LIMIT 1;
  BEGIN
    EXECUTE 'CREATE INDEX IF NOT EXISTS logistics_knowledge_embedding_idx ON public.logistics_knowledge USING ivfflat (embedding vector_l2_ops) WITH (lists = 100)';
  EXCEPTION WHEN others THEN
    RAISE NOTICE 'Could not create ivfflat index: %', SQLERRM;
  END;
EXCEPTION WHEN others THEN
  RAISE NOTICE 'Table public.logistics_knowledge not found - skipping index creation';
END$$;

-- 3) Row Level Security (RLS) example — owner or public
-- This attempts to enable RLS and add a SELECT policy that allows access
-- when `is_public` is true or the `owner` equals the current authenticated user
-- (auth.uid() is provided by Supabase's Postgres auth helpers).
DO $$
BEGIN
  PERFORM 1 FROM public.logistics_knowledge LIMIT 1;

  BEGIN
    EXECUTE 'ALTER TABLE public.logistics_knowledge ENABLE ROW LEVEL SECURITY';
  EXCEPTION WHEN others THEN
    RAISE NOTICE 'Could not enable RLS: %', SQLERRM;
  END;

  BEGIN
    EXECUTE $q$
      CREATE POLICY IF NOT EXISTS logistics_knowledge_select_owner_or_public
      ON public.logistics_knowledge
      FOR SELECT
      USING (coalesce(is_public, false) OR (owner::text IS NOT NULL AND owner::text = auth.uid()));
    $q$;
  EXCEPTION WHEN others THEN
    RAISE NOTICE 'Could not create RLS policy (columns may be missing): %', SQLERRM;
  END;

EXCEPTION WHEN others THEN
  RAISE NOTICE 'Table public.logistics_knowledge not found - skipping RLS setup';
END$$;

-- Notes:
-- - The function `match_documents` takes a `vector` value for `query_embedding`.
--   If your application computes embeddings client-side (e.g., via OpenAI) and
--   sends them as an array, convert them to a `vector` before calling this
--   function, e.g. in SQL: `SELECT * FROM match_documents(10, 0.0, '[0.1,0.2, ...]'::vector);`
-- - The RLS block is defensive: it will log a NOTICE rather than fail if the
--   table or expected columns don't exist. Review and adapt the policy to
--   match your schema and security model.
-- - Tune the ivfflat `lists` parameter to your dataset size and performance needs.
