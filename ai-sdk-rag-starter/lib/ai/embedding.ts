import { openai } from '@ai-sdk/openai';
import { embed, embedMany } from 'ai';
import { cosineDistance, desc, gt, sql } from 'drizzle-orm';

import { db } from '@/lib/db';
import { embeddings } from '@/lib/db/schema/resources';

const embeddingModel = openai.embedding('text-embedding-ada-002');

const generateChunks = (input: string): string[] => {
  // Improved chunking strategy that preserves recipe context
  // Split by double newlines (paragraphs) or major sections, not just sentences

  // First, try to split by double newlines (paragraph boundaries)
  let chunks = input
    .trim()
    .split(/\n\n+/)
    .map(chunk => chunk.trim())
    .filter(chunk => chunk.length > 0);

  // If we only get 1 chunk, fall back to splitting by single newlines for recipe sections
  if (chunks.length === 1) {
    chunks = input
      .trim()
      .split('\n')
      .map(chunk => chunk.trim())
      .filter(chunk => chunk.length > 0);
  }

  // If still only 1 chunk or very few, split by sentences but keep more context (multiple sentences per chunk)
  if (chunks.length <= 2) {
    const sentences = input.split(/\.\s+/).filter(s => s.trim().length > 0);
    chunks = [];

    // Group sentences into chunks of 3-5 sentences to maintain context
    for (let i = 0; i < sentences.length; i += 3) {
      const chunk = sentences.slice(i, i + 5).join('. ') + (i + 5 < sentences.length ? '.' : '');
      if (chunk.trim().length > 0) {
        chunks.push(chunk.trim());
      }
    }
  }

  return chunks.filter(chunk => chunk.length >= 20); // Filter out very short chunks
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
    .where(gt(similarity, 0.75))  // ← MÓDOSÍTÁS: Lowered from 0.85 to 0.75 for better recall
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