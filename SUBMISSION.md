# RouteMind - MongoDB SFTW Hackathon submission

## Describe your use of MongoDB products to build the submitted project

We stored the agent's entire memory in MongoDB Atlas. Every possible turn is one document
holding the junction text, the action, a 1024-dimension Voyage embedding, and a usefulness
score the agent updates as it learns. Recall is a single Atlas Vector Search query on the
mnemo_vec index, and after each trip the agent writes back to Atlas: it raises the score of
turns that helped and deletes the ones that keep misleading it. Keeping the vector, the
metadata, and the learned signal in the same document meant recall and learning lived in one
collection, with no separate vector store to sync.

## Provide feedback from your experience using MongoDB products

The biggest win was cohesion: putting the vector, the metadata, and our own usefulness score in
one document and recalling with a single $vectorSearch kept the whole memory in one place, and
create_search_index with status polling made index setup painless. Two things cost us time and
would help others if documented more loudly. First, the vector search index is eventually
consistent, so usefulness values we had just written were not reflected in $vectorSearch results
for a few seconds, which forced an in-process cache to rerank reliably. Second, using an in-query
filter inside $vectorSearch requires declaring that field in the index definition, which was not
obvious, so we fell back to over-fetching and $match.

## Provide feedback from your experience using partner products

Voyage AI: moving embeddings from OpenAI to voyage-3.5 through the ai.mongodb.com endpoint was
close to a drop-in change, and retrieval quality held at 1024 dimensions, which also shrank our
index. Worth documenting: only specific model names work on that endpoint (voyage-3.5, not
voyage-3), and the MongoDB-issued Voyage key does not work against api.voyageai.com.

Raindrop: one key and one POST, and within a minute we could watch each recall stream into the
dashboard. Seeing the wrong-turn events dry up across trips made the self-improvement obvious,
which is exactly what we wanted to show.

Modelence: npx create-modelence-app gave us a full TypeScript, React, and MongoDB app with auth,
a build, and a deploy path already wired, and reading our existing Atlas cluster from a server
module worked first try.

ElevenLabs: one POST added a narrator voice to the dashboard, and the quality was well beyond
browser text to speech, making the demo feel finished with almost no effort.
