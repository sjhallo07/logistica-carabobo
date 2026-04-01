-- Create a match_documents function that performs a nearest-neighbors search
-- against the `logistics_knowledge` table using an array embedding column
-- Adjust this SQL if your embedding column uses the 'vector' type (pgvector)

-- Function signature expected by the application: match_documents(match_count int, match_threshold double precision, query_embedding double precision[])
CREATE OR REPLACE FUNCTION public.match_documents(match_count integer, match_threshold double precision, query_embedding double precision[])
RETURNS TABLE(id uuid, content text, metadata jsonb, embedding double precision[], distance double precision)
LANGUAGE plpgsql
AS $$
BEGIN
  -- Nearest neighbors by Euclidean distance using array-based embeddings
  RETURN QUERY
  SELECT id, content, metadata, embedding, (
    -- compute Euclidean distance between arrays
    (SELECT sqrt(sum((a-b)*(a-b))) FROM (
      SELECT unnest(embedding) AS a, unnest(query_embedding) AS b
    ) s)
  )::double precision AS distance
  FROM public.logistics_knowledge
  WHERE embedding IS NOT NULL
  ORDER BY distance ASC
  LIMIT match_count;
END;
$$;

-- NOTE: If your embeddings are stored as the 'vector' type (pgvector), replace the
-- distance computation with the pgvector operator, e.g.:
-- ORDER BY embedding <-> query_embedding
