// Removes secrets, email addresses and URLs from note text before it is published. The
// extractor prompt also asks the model to redact, but a model can miss a secret or be
// talked into copying one by text inside the transcript, so this check does not rely on it.

const PATTERNS = [
  [/-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?(?:-----END [A-Z ]*PRIVATE KEY-----|$)/g, "[secret]"],
  [/\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})/g, "[secret]"],
  [/\bsk-(?:ant-)?[A-Za-z0-9_-]{20,}/g, "[secret]"],
  [/\b(?:AKIA|ASIA)[0-9A-Z]{16}\b/g, "[secret]"],
  [/\bxox[abposr]-[A-Za-z0-9-]{10,}/g, "[secret]"],
  [/\bAIza[0-9A-Za-z_-]{35}/g, "[secret]"],
  [/\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}/g, "[secret]"],
  [/\bBearer\s+[A-Za-z0-9._~+/-]{16,}=*/g, "Bearer [secret]"],
  [
    /\b(password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|client[_-]?secret)(["']?\s*[:=]\s*)["']?[^\s"',;]{6,}/gi,
    "$1$2[secret]",
  ],
  // URLs before email addresses, so credentials in a connection string go with the whole URL.
  [/\b[a-z][a-z0-9+.-]*:\/\/[^\s)\]}>"'`]+/gi, "[url]"],
  [/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g, "[email]"],
];

// Long strings that mix lower case, upper case and digits with high entropy look like keys.
// Slashes are not part of a candidate, so file paths do not match.
const LONG_TOKEN = /[A-Za-z0-9+_=-]{32,}/g;
const MIN_TOKEN_ENTROPY_BITS = 4.2;

export function redact(text) {
  let result = text;
  for (const [pattern, replacement] of PATTERNS) result = result.replace(pattern, replacement);
  return result.replace(LONG_TOKEN, (candidate) => (looksRandom(candidate) ? "[secret]" : candidate));
}

function looksRandom(text) {
  return /[a-z]/.test(text) && /[A-Z]/.test(text) && /[0-9]/.test(text) && shannonEntropy(text) >= MIN_TOKEN_ENTROPY_BITS;
}

function shannonEntropy(text) {
  const counts = new Map();
  for (const char of text) counts.set(char, (counts.get(char) ?? 0) + 1);
  let bits = 0;
  for (const count of counts.values()) {
    const p = count / text.length;
    bits -= p * Math.log2(p);
  }
  return bits;
}
