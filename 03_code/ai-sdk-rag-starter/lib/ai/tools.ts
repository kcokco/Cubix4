import { z } from 'zod';
import { createResource } from '@/lib/actions/resources';
import { findRelevantContent } from '@/lib/ai/embedding';

export const addResource = {
  description: `add a resource to your knowledge base.
  If the user provides a random piece of knowledge unprompted, use this tool to add it to your knowledge base.
  Don't ask for confirmation.`,
  inputSchema: z.object({
    content: z
      .string()
      .describe('the content or resource to add to the knowledge base'),
  }),
  execute: async ({ content }: { content: string }) => {
    return await createResource({ content });
  },
};

export const getInformation = {
  description: `get information from your knowledge base to answer questions.`,
  inputSchema: z.object({
    question: z.string().describe('the users question'),
  }),
  execute: async ({ question }: { question: string }) => {
    return await findRelevantContent(question);
  },
};