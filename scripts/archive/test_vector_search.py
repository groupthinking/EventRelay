#!/usr/bin/env python3
"""Test vector similarity search."""
import os
import psycopg2
from google import genai
from dotenv import load_dotenv

load_dotenv(override=True)
client = genai.Client(api_key=os.environ['GOOGLE_API_KEY'])

query = 'How does the video processing pipeline work?'
result = client.models.embed_content(
    model='text-embedding-004',
    contents=query,
    config={'title': "Query"}
)
embedding = result.embeddings[0].values
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