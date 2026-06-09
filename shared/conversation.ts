/** Mirrors packages/core/seal_core/intent/conversation.py for dashboard display. */

const CLARIFICATION_SECTION_HEADERS = [
  '**A few details would help**',
  '**Clarifying questions**',
] as const;

const POST_ANSWER_REASONING_HEADERS = [
  '**Context from our conversation**',
  '**Research notes**',
  '**Suggested follow-ups**',
] as const;

const INLINE_ANSWER_ENRICHMENT_HEADERS = [
  '### Suggested analysis_followups',
  '### Suggested follow-ups',
  '### Research_notes',
  '### Research notes',
] as const;

export function isAssistantClarification(content: string): boolean {
  return CLARIFICATION_SECTION_HEADERS.some((header) => content.includes(header));
}

/** Strip post-answer reasoning suffixes; keep clarification-only bodies intact. */
export function contentForLlmHistory(content: string): string {
  if (isAssistantClarification(content)) {
    return content;
  }
  let cutAt = content.length;
  for (const header of [...POST_ANSWER_REASONING_HEADERS, ...INLINE_ANSWER_ENRICHMENT_HEADERS]) {
    const idx = content.indexOf(header);
    if (idx >= 0) {
      cutAt = Math.min(cutAt, idx);
    }
  }
  let result = content.slice(0, cutAt).trim();
  if (result.endsWith('---')) {
    result = result.slice(0, -3).trim();
  }
  return result;
}
