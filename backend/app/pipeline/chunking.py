"""Text chunking utilities.

Provides `chunk_text` which splits long text into 300-500 token chunks
with ~15% overlap while respecting sentence/paragraph boundaries. Captions
should not be chunked and are handled by callers.
"""

import re
from typing import List, Dict


def _split_into_sentences(text: str) -> List[str]:
	# Very small heuristic sentence splitter: split on punctuation or newlines.
	# Keeps abbreviations intact in most cases for our use-case.
	# Also preserve paragraphs by splitting on double newlines first.
	text = text.strip()
	if not text:
		return []

	paragraphs = re.split(r"\n\s*\n", text)
	sentences: List[str] = []
	for p in paragraphs:
		# split by sentence enders followed by whitespace
		parts = re.split(r'(?<=[.!?])\s+', p.strip())
		for s in parts:
			s = s.strip()
			if s:
				sentences.append(s)
		# preserve paragraph boundary as a short sentinel (keeps chunks natural)
		sentences.append("\n")
	# drop trailing paragraph sentinel
	if sentences and sentences[-1] == "\n":
		sentences.pop()
	return sentences


def _count_tokens_approx(text: str) -> int:
	# Approximate token count by whitespace-split words. Good enough for chunk sizing.
	if not text:
		return 0
	return len(text.split())


def chunk_text(text: str, page_number: int, source_item_id: str) -> List[Dict]:
	"""Split `text` into 300-500 token chunks with ~15% overlap.

	Each returned dict contains:
	  - "text": chunk text
	  - "page_number": original page number (int)
	  - "source_item_id": id of the originating item (str)
	  - "chunk_index": zero-based index of the chunk for that source

	This function never chunks captions (callers must skip caption inputs).
	Sentences and paragraph boundaries are respected (no mid-sentence cuts).
	"""
	sentences = _split_into_sentences(text)
	if not sentences:
		return []

	MIN_TOKENS = 300
	MAX_TOKENS = 500
	OVERLAP_PCT = 0.15

	chunks: List[Dict] = []
	cur_sentences: List[str] = []
	cur_tokens = 0
	chunk_index = 0

	i = 0
	while i < len(sentences):
		s = sentences[i]
		# paragraph sentinel
		if s == "\n":
			# include paragraph break as newline if current chunk non-empty
			if cur_sentences:
				cur_sentences.append("\n")
			i += 1
			continue

		s_tokens = _count_tokens_approx(s)
		# If a single sentence is extremely long, allow it to form its own chunk
		if s_tokens >= MAX_TOKENS:
			if cur_sentences:
				# flush current chunk first
				chunk_text_str = " ".join(cur_sentences).strip()
				chunks.append(
					{
						"text": chunk_text_str,
						"page_number": page_number,
						"source_item_id": source_item_id,
						"chunk_index": chunk_index,
					}
				)
				chunk_index += 1
				cur_sentences = []
				cur_tokens = 0
			# add the very long sentence as its own chunk
			chunks.append(
				{
					"text": s,
					"page_number": page_number,
					"source_item_id": source_item_id,
					"chunk_index": chunk_index,
				}
			)
			chunk_index += 1
			i += 1
			continue

		# Add sentence to current chunk
		cur_sentences.append(s)
		cur_tokens += s_tokens
		i += 1

		# Decide whether to flush chunk: exceed MAX_TOKENS or (>=MIN and next sentence would overflow)
		next_tokens = 0
		if i < len(sentences) and sentences[i] != "\n":
			next_tokens = _count_tokens_approx(sentences[i])

		if cur_tokens >= MAX_TOKENS or (
			cur_tokens >= MIN_TOKENS and (cur_tokens + next_tokens) > MAX_TOKENS
		):
			chunk_text_str = " ".join(cur_sentences).strip()
			chunks.append(
				{
					"text": chunk_text_str,
					"page_number": page_number,
					"source_item_id": source_item_id,
					"chunk_index": chunk_index,
				}
			)
			chunk_index += 1

			# prepare overlap: keep last N tokens worth of sentences
			overlap_tokens = max(1, int(cur_tokens * OVERLAP_PCT))
			if overlap_tokens > 0:
				# walk sentences backwards to gather overlap
				overlap_sentences: List[str] = []
				acc = 0
				for sent in reversed(cur_sentences):
					if sent == "\n":
						overlap_sentences.insert(0, sent)
						continue
					tok = _count_tokens_approx(sent)
					overlap_sentences.insert(0, sent)
					acc += tok
					if acc >= overlap_tokens:
						break
				cur_sentences = overlap_sentences
				cur_tokens = sum(_count_tokens_approx(s) for s in cur_sentences if s != "\n")
			else:
				cur_sentences = []
				cur_tokens = 0

	# flush remaining
	if cur_sentences:
		chunk_text_str = " ".join(cur_sentences).strip()
		chunks.append(
			{
				"text": chunk_text_str,
				"page_number": page_number,
				"source_item_id": source_item_id,
				"chunk_index": chunk_index,
			}
		)

	return chunks

