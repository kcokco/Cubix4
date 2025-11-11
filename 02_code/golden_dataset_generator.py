import os
import json
import glob
from pathlib import Path
from typing import List, Dict, Any, Optional
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# Prompt for generating query-excerpt pairs in a single call
QUERY_EXCERPT_GENERATION_PROMPT = """
You are helping to create a golden dataset for evaluating a RAG (Retrieval-Augmented Generation) system.

Given a technical documentation page, generate {num_pairs} diverse query-answer pairs where:
1. Each query is a realistic user question that someone might ask
2. Each answer is a meaningful excerpt/quote directly from the provided document that answers the query
3. The excerpt should be substantial enough to fully answer the query (include code examples, explanations, etc.)

Requirements for queries:
- Generate queries of varying complexity (simple facts, how-to questions, comparisons, troubleshooting)
- Make queries natural and realistic (how real users would ask)
- Cover different aspects and sections of the document
- Keep queries concise but specific

Requirements for excerpts:
- Extract exact text from the document (preserve formatting, code blocks, etc.)
- Include enough context to fully answer the query
- Don't paraphrase - use the actual document text
- Include relevant code examples or commands when present

Format your response as JSON:
{{
  "pairs": [
    {{
      "query": "user question here",
      "excerpt": "exact text from document that answers the query"
    }},
    ...
  ]
}}

Document content:
{document}

Generate {num_pairs} query-excerpt pairs:"""

class GoldenDatasetGenerator:
    def __init__(self, openai_api_key: str = None, data_dir: str = "data/docs/qdrant"):
        """
        Initialize the golden dataset generator
        
        Args:
            openai_api_key: OpenAI API key (uses env variable if not provided)
            data_dir: Directory containing markdown documentation files
        """
        api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key must be provided either as parameter or OPENAI_API_KEY environment variable")
        
        self.openai_client = OpenAI(api_key=api_key)
        self.data_dir = Path(data_dir)
        
    def read_markdown_files(self, version: str = "v1.2.x", max_files: Optional[int] = None) -> List[Dict[str, str]]:
        """
        Read markdown files from the specified version directory
        
        Args:
            version: Version directory to read from (e.g., 'v1.2.x')
            max_files: Maximum number of files to process (None for all files)
            
        Returns:
            List of dictionaries with 'file_path', 'title', and 'content'
        """
        version_dir = self.data_dir / version
        if not version_dir.exists():
            raise FileNotFoundError(f"Version directory {version_dir} does not exist")
        
        markdown_files = []
        pattern = str(version_dir / "*.md")
        
        file_paths = glob.glob(pattern)
        
        # Limit number of files if specified
        if max_files is not None:
            file_paths = file_paths[:max_files]
            print(f"Processing {len(file_paths)} files (limited by max_files={max_files})")
        
        for file_path in file_paths:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract title from frontmatter or filename
                title = self._extract_title(content, Path(file_path).stem)
                
                markdown_files.append({
                    'file_path': file_path,
                    'title': title,
                    'content': content
                })
                
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
                continue
                
        return markdown_files
    
    def _extract_title(self, content: str, fallback: str) -> str:
        """Extract title from markdown frontmatter or use fallback"""
        lines = content.split('\n')
        if lines[0].strip() == '---':
            for line in lines[1:]:
                if line.strip() == '---':
                    break
                if line.startswith('title:'):
                    return line.split('title:', 1)[1].strip().strip('"\'')
        return fallback
    
    def generate_query_excerpt_pairs(self, document: str, num_pairs: int = 3) -> List[Dict[str, str]]:
        """
        Generate query-excerpt pairs for a single document in one LLM call
        
        Args:
            document: Document content
            num_pairs: Number of query-excerpt pairs to generate
            
        Returns:
            List of dictionaries with 'query' and 'excerpt' keys
        """
        prompt = QUERY_EXCERPT_GENERATION_PROMPT.format(
            document=document,
            num_pairs=num_pairs
        )
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1000,
                temperature=0.7
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Parse JSON response
            try:
                parsed_response = json.loads(response_text)
                pairs = parsed_response.get("pairs", [])
                
                # Validate and clean the pairs
                valid_pairs = []
                for pair in pairs:
                    if isinstance(pair, dict) and "query" in pair and "excerpt" in pair:
                        valid_pairs.append({
                            "query": pair["query"].strip(),
                            "excerpt": pair["excerpt"].strip()
                        })
                
                return valid_pairs[:num_pairs]  # Ensure we don't exceed requested number
                
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON response: {e}")
                print(f"Response was: {response_text[:200]}...")
                return []
            
        except Exception as e:
            print(f"Error generating query-excerpt pairs: {e}")
            return []
    
    def generate_golden_dataset(self, version: str = "v1.2.x", pairs_per_doc: int = 3, max_files: Optional[int] = None, output_file: str = None) -> Dict[str, Any]:
        """
        Generate the complete golden dataset using single LLM calls per document
        
        Args:
            version: Version directory to process
            pairs_per_doc: Number of query-excerpt pairs to generate per document
            max_files: Maximum number of files to process (None for all files)
            output_file: Output JSON file path (optional)
            
        Returns:
            Generated dataset as dictionary
        """
        print(f"Reading markdown files from {version}...")
        documents = self.read_markdown_files(version, max_files)
        
        if not documents:
            print(f"No documents found in {version}")
            return {}
        
        print(f"Found {len(documents)} documents")
        
        dataset = {
            "metadata": {
                "version": version,
                "generated_at": datetime.now().isoformat(),
                "pairs_per_document": pairs_per_doc,
                "total_documents": len(documents)
            },
            "entries": []
        }
        
        for i, doc in enumerate(documents):
            print(f"Processing {doc['title']} ({i+1}/{len(documents)})...")
            
            # Generate query-excerpt pairs for this document in one call
            qa_pairs = self.generate_query_excerpt_pairs(doc['content'], pairs_per_doc)
            
            if not qa_pairs:
                print(f"  No query-excerpt pairs generated for {doc['title']}")
                continue
            
            # Create document entry
            doc_entry = {
                "document": {
                    "file_path": doc['file_path'],
                    "title": doc['title'],
                    "content": doc['content']
                },
                "qa_pairs": []
            }
            
            # Add the generated pairs (rename 'excerpt' to 'response' for consistency)
            for pair in qa_pairs:
                doc_entry["qa_pairs"].append({
                    "query": pair["query"],
                    "response": pair["excerpt"]  # Use excerpt as response
                })
            
            dataset["entries"].append(doc_entry)
            print(f"  Generated {len(doc_entry['qa_pairs'])} Q&A pairs in single call")
        
        # Save to file if specified
        if output_file:
            self.save_dataset(dataset, output_file)
        
        return dataset
    
    def save_dataset(self, dataset: Dict[str, Any], output_file: str):
        """Save dataset to JSON file"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(dataset, f, indent=2, ensure_ascii=False)
            print(f"Dataset saved to {output_file}")
        except Exception as e:
            print(f"Error saving dataset: {e}")

if __name__ == "__main__":
    try:
        # Initialize generator
        generator = GoldenDatasetGenerator()
        
        # Generate golden dataset
        version = "v1.2.x"
        output_file = f"golden_dataset_{version}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        print("Starting golden dataset generation...")
        dataset = generator.generate_golden_dataset(
            version=version,
            pairs_per_doc=3,
            max_files=None,  # Limit to 5 files for testing/development
            output_file=output_file
        )
        
        print(f"\nGeneration complete!")
        print(f"Total documents processed: {dataset['metadata']['total_documents']}")
        print(f"Total entries: {len(dataset['entries'])}")
        total_qa_pairs = sum(len(entry['qa_pairs']) for entry in dataset['entries'])
        print(f"Total Q&A pairs: {total_qa_pairs}")
        
    except Exception as e:
        print(f"Error during dataset generation: {e}")