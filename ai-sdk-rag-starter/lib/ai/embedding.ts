import { openai } from '@ai-sdk/openai';
import { embed, embedMany } from 'ai';
import { cosineDistance, desc, gt, sql } from 'drizzle-orm';

import { db } from '@/lib/db';
import { embeddings } from '@/lib/db/schema/resources';

const embeddingModel = openai.embedding('text-embedding-ada-002');

const generateChunks = (input: string): string[] => {
  return input
    .trim()
    .split('.')
    .filter(i => i !== '');
};

export const generateEmbeddings = async (
  value: string,
): Promise<Array<{ embedding: number[]; content: string }>> => {
  const chunks = generateChunks(value);
  const { embeddings } = await embedMany({
    model: embeddingModel,
    values: chunks,
  });
  return embeddings.map((e, i) => ({ content: chunks[i], embedding: e }));
};

export const generateEmbedding = async (value: string): Promise<number[]> => {
  const input = value.replaceAll('\\n', ' ');
  const { embedding } = await embed({
    model: embeddingModel,
    value: input,
  });
  return embedding;
};

export const findRelevantContent = async (userQuery: string) => {
  const userQueryEmbedded = await generateEmbedding(userQuery);
  const similarity = sql<number>`1 - (${cosineDistance(
    embeddings.embedding,
    userQueryEmbedded,
  )})`;
  
  const similarGuides = await db
    .select({ content: embeddings.content, similarity })
    .from(embeddings)
    .where(gt(similarity, 0.85))  // ← MÓDOSÍTÁS: 0.80 → 0.85
    .orderBy((t) => desc(t.similarity))
    .limit(4);
  
  console.log('Search results:', similarGuides);
  console.log('Total results found:', similarGuides.length);
  
  if (similarGuides.length === 0) {
    console.log('No results found - checking total embeddings in database...');
    const totalCount = await db.select({ count: sql`count(*)` }).from(embeddings);
    console.log('Total embeddings in database:', totalCount[0].count);
    return "No relevant information found in the knowledge base.";
  }
  
  return similarGuides
    .map((guide, index) => 
      `[Score: ${guide.similarity.toFixed(4)}] ${guide.content}`
    )
    .join('\n\n');
};