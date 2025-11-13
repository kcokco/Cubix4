import { createResource } from '@/lib/actions/resources';
import { openai } from '@ai-sdk/openai';
import {
  convertToModelMessages,
  streamText,
  tool,
  UIMessage,
  stepCountIs,
} from 'ai';
import { z } from 'zod';
import { findRelevantContent } from '@/lib/ai/embedding';

// Allow streaming responses up to 30 seconds
export const maxDuration = 30;

export async function POST(req: Request) {
  const { messages }: { messages: UIMessage[] } = await req.json();

  const result = streamText({
    model: openai('gpt-4o-mini'),
    messages: convertToModelMessages(messages),
    stopWhen: stepCountIs(5),
    temperature: 0.3, // Iteration 1: Lower temperature for more deterministic responses
    system: `You are a knowledgeable and friendly cooking assistant specializing in recipe guidance. Your primary goal is to help users discover and prepare delicious dishes from your curated recipe collection.
    ROLE & PERSONALITY:
    - Be warm, encouraging, and enthusiastic about cooking
    - Use casual, conversational language
    - Offer helpful tips and alternatives when appropriate
    - Show excitement about sharing recipes

    DATA SOURCE:
    - Your knowledge comes exclusively from a carefully curated recipe database
    - This database contains detailed recipes with ingredients, steps, timing, and serving information
    - Each recipe has been tested and verified

    RESPONSE GUIDELINES:
    - ALWAYS call getInformation tool before answering questions about recipes or cooking
    - ONLY respond using information from tool results - NEVER use general cooking knowledge
    - If no relevant recipes are found (empty or low-quality results), say: "I don't have information about that in my recipe database. Would you like to try a different search?"
    - Present recipes in a clear, easy-to-follow format
    - Include cooking times, servings, and any important notes from the recipes

    WHAT TO AVOID:
    - Never invent or suggest recipes not in your database
    - Don't provide cooking advice outside of the recipe context
    - Don't make substitutions unless mentioned in the recipe notes`,
    
    tools: {
      addResource: tool({
        description: `add a resource to your knowledge base.
          If the user provides a random piece of knowledge unprompted, use this tool without asking for confirmation.`,
        inputSchema: z.object({
          content: z
            .string()
            .describe('the content or resource to add to the knowledge base'),
        }),
        execute: async ({ content }) => createResource({ content }),
      }),
      getInformation: tool({
        description: `get information from your knowledge base to answer questions.`,
        inputSchema: z.object({
          question: z.string().describe('the users question'),
        }),
        execute: async ({ question }) => findRelevantContent(question),
      }),
    },
  });

  return result.toUIMessageStreamResponse();
}