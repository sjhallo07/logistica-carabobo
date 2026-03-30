-- 1. Enable pgvector
create extension if not exists vector;

-- 2. Knowledge & Coupons Table
create table logistics_knowledge (
  id uuid primary key default gen_random_uuid(),
  content text not null,
  metadata jsonb,
  embedding vector(1536)
);

-- 3. Similarity Search Function
create or replace function match_documents (
  query_embedding vector(1536),
  match_threshold float,
  match_count int
)
returns table (
  id uuid,
  content text,
  metadata jsonb,
  similarity float
)
language plpgsql
as $$
begin
  return query
  select
    logistics_knowledge.id,
    logistics_knowledge.content,
    logistics_knowledge.metadata,
    1 - (logistics_knowledge.embedding <=> query_embedding) as similarity
  from logistics_knowledge
  where 1 - (logistics_knowledge.embedding <=> query_embedding) > match_threshold
  order by similarity desc
  limit match_count;
end;
$$;
