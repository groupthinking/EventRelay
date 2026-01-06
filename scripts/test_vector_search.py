#!/usr/bin/env python3
"""Test vector similarity search."""
import google.generativeai as genai
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv(override=True)
genai.configure(api_key=os.environ['GOOGLE_API_KEY'])

query = 'How does the video processing pipeline work?'
result = genai.embed_content(model='models/text-embedding-004', content=query, task_type='retrieval_query')
embedding = result['embedding']
vector_str = '[' + ','.join(map(str, embedding)) + ']'

conn = psycopg2.connect(os.environ['VECTOR_DATABASE_URL'])
cur = conn.cursor()
cur.execute("""
    SELECT (metadata::json)->>'filename' as filename,
           1 - (embedding <=> %s) as similarity
    FROM vector_items
    ORDER BY embedding <=> %s
    LIMIT 5
""", (vector_str, vector_str))

print('\nTop 5 results for: "How does the video processing pipeline work?"\n')
for row in cur.fetchall():
    print(f'  {row[1]:.3f} - {row[0]}')

cur.close()
conn.close()
print('\n✓ Vector search working!')
