import { NextResponse } from 'next/server';
import { embedMany } from 'ai';
import { openai } from '@ai-sdk/openai';
import { db } from '@/lib/db';
import { embeddings as embeddingsTable, resources } from '@/lib/db/schema';

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const { chunks, filename } = body;

    if (!chunks || !Array.isArray(chunks) || !filename) {
      return NextResponse.json({ error: 'Missing or invalid chunks/filename' }, { status: 400 });
    }

    console.log(`Received ${chunks.length} chunks from ${filename}. Processing...`);

    const [resource] = await db
      .insert(resources)
      .values({ content: filename })
      .returning({ id: resources.id });

    const { embeddings } = await embedMany({
      model: openai.embedding('text-embedding-ada-002'),
      values: chunks,
    });
    
    const valuesToInsert = embeddings.map((embedding, i) => ({
      resourceId: resource.id,
      content: chunks[i],
      embedding: embedding,
    }));

    await db.insert(embeddingsTable).values(valuesToInsert);

    console.log('Successfully inserted embeddings into the database.');

    return NextResponse.json(
      { message: 'File processed and embeddings stored successfully!' },
      { status: 200 }
    );

  } catch (error) {
    console.error('API Error:', error);
    return NextResponse.json({ error: 'Failed to process request' }, { status: 500 });
  }
}

