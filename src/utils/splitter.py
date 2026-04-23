"""
Markdown 文件切分器

切分策略：
1. 先依 Markdown 標題層級切分（一個 section = 一個 chunk）
2. 若 chunk 超過 MAX_CHUNK_CHARS，再依段落邊界二次切分
3. 若單一段落仍過長，依句子邊界切分
4. 每個子 chunk 保留原始 header_path，附加 (1/n) 標記

目的：確保每個 chunk 都在 embedding 模型的 token 上限之內，
      避免長文內容被靜默截斷導致語意品質下降。
"""

import re
import hashlib
from typing import List, Optional
from dataclasses import dataclass
from src.constants import KNOWLEDGE_CONSTANTS


@dataclass
class ChunkNode:
    """Markdown Chunk 節點"""
    id: str
    header_path: str   # 標題路徑（麵包屑）
    content: str       # 完整內容（含標題行）
    preview: str       # 前 200 字預覽
    level: int         # 標題層級（1–6，0 = 無標題）


# ── 句子切分用的斷句符號（中英文標點）────────────────────────────────────────
_SENTENCE_END = re.compile(r'(?<=[。！？.!?\n])\s*')


class MarkdownSplitter:
    """
    Markdown 文件切分器

    按照 Markdown 標題階層切分文件，並對過長的 section 做二次切分，
    確保每個 chunk 的字元數不超過 MAX_CHUNK_CHARS。
    """

    def __init__(self, parent_id: str):
        self.parent_id  = parent_id
        self._max_chars = KNOWLEDGE_CONSTANTS.MAX_CHUNK_CHARS

    # ── Public API ────────────────────────────────────────────────────────────

    def split(self, content: str) -> List[ChunkNode]:
        """切分 Markdown 文件，回傳所有 ChunkNode。"""
        raw_chunks = self._split_by_headers(content)

        result: List[ChunkNode] = []
        for chunk in raw_chunks:
            if len(chunk.content) > self._max_chars:
                result.extend(self._subdivide(chunk))
            else:
                result.append(chunk)
        return result

    # ── Step 1：依標題切分 ────────────────────────────────────────────────────

    def _split_by_headers(self, content: str) -> List[ChunkNode]:
        chunks: List[ChunkNode] = []
        lines = content.split('\n')

        header_stack: List[tuple[int, str]] = []
        current_lines: List[str] = []
        current_level = 0

        for line in lines:
            m = re.match(r'^(#{1,6})\s+(.+)$', line)
            if m:
                if current_lines:
                    chunk = self._make_chunk(header_stack, current_lines, current_level)
                    if chunk:
                        chunks.append(chunk)

                level = len(m.group(1))
                title = m.group(2).strip()

                # 移除比當前層級深或同級的舊標題
                header_stack = [(l, t) for l, t in header_stack if l < level]
                header_stack.append((level, title))

                current_lines = [line]
                current_level = level
            else:
                current_lines.append(line)

        if current_lines:
            chunk = self._make_chunk(header_stack, current_lines, current_level)
            if chunk:
                chunks.append(chunk)

        return chunks

    # ── Step 2：大 chunk 二次切分 ─────────────────────────────────────────────

    def _subdivide(self, chunk: ChunkNode) -> List[ChunkNode]:
        """
        將超過 MAX_CHUNK_CHARS 的 chunk 切成數個子 chunk。

        切分順序：
          1. 保留標題行
          2. 將 body 依空行分成段落
          3. 貪婪地把段落合併，不超過上限
          4. 若單一段落仍過長，再依句子邊界切
        """
        lines = chunk.content.split('\n')

        # 分離標題行（第一行若為 # 開頭）
        if lines and re.match(r'^#{1,6}\s+', lines[0]):
            header_line = lines[0]
            body_lines  = lines[1:]
        else:
            header_line = ''
            body_lines  = lines

        # 以空行分段
        paragraphs = self._lines_to_paragraphs(body_lines)

        # 貪婪合併段落成 sub-chunks
        sub_bodies: List[str] = []
        current: List[str] = []
        current_len = len(header_line) + 1  # +1 for newline

        for para in paragraphs:
            # 若單一段落就超過上限，先拆成句子
            if len(para) > self._max_chars:
                # flush 目前累積
                if current:
                    sub_bodies.append('\n\n'.join(current))
                    current, current_len = [], len(header_line) + 1
                for sentence_chunk in self._split_by_sentences(para):
                    sub_bodies.append(sentence_chunk)
                continue

            if current_len + len(para) + 2 > self._max_chars and current:
                sub_bodies.append('\n\n'.join(current))
                current, current_len = [], len(header_line) + 1

            current.append(para)
            current_len += len(para) + 2  # +2 for \n\n

        if current:
            sub_bodies.append('\n\n'.join(current))

        if not sub_bodies:
            return [chunk]

        # 若只有一段，不切（避免無意義的 (1/1) 標記）
        if len(sub_bodies) == 1:
            return [chunk]

        total   = len(sub_bodies)
        result: List[ChunkNode] = []

        for i, body in enumerate(sub_bodies, 1):
            # ── Overlap：將前一個 sub-chunk 的尾部加到當前開頭 ────────────────
            # 只在 i > 1 時加，且只取純 body（不含 header_line）
            if i > 1:
                tail    = self._tail_overlap(sub_bodies[i - 2])
                if tail:
                    body = tail + "\n\n" + body

            suffix      = f" ({i}/{total})"
            header_path = chunk.header_path + suffix
            content     = (f"{header_line}\n{body}" if header_line else body).strip()

            if len(content) < 10:
                continue

            preview  = content[:200] + '...' if len(content) > 200 else content
            chunk_id = self._gen_id(header_path, content[:100])

            result.append(ChunkNode(
                id          = chunk_id,
                header_path = header_path,
                content     = content,
                preview     = preview,
                level       = chunk.level,
            ))

        return result if result else [chunk]

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _lines_to_paragraphs(lines: List[str]) -> List[str]:
        """把行列表依空行分組成段落字串列表。"""
        paragraphs: List[str] = []
        current: List[str] = []
        for line in lines:
            if line.strip() == '':
                if current:
                    paragraphs.append('\n'.join(current).strip())
                    current = []
            else:
                current.append(line)
        if current:
            paragraphs.append('\n'.join(current).strip())
        return [p for p in paragraphs if p]

    def _split_by_sentences(self, text: str) -> List[str]:
        """將過長的單段文字依句子邊界切分。"""
        max_s = KNOWLEDGE_CONSTANTS.MAX_SENTENCE_CHARS
        sentences = [s for s in _SENTENCE_END.split(text) if s.strip()]
        chunks: List[str] = []
        current = ''
        for s in sentences:
            if len(current) + len(s) > max_s and current:
                chunks.append(current.strip())
                current = s
            else:
                current += s
        if current.strip():
            chunks.append(current.strip())
        return chunks if chunks else [text]

    def _make_chunk(
        self,
        header_stack: List[tuple[int, str]],
        content_lines: List[str],
        level: int,
    ) -> Optional[ChunkNode]:
        content = '\n'.join(content_lines).strip()
        if len(content) < 10:
            return None

        header_path = (
            ' > '.join(t for _, t in header_stack)
            if header_stack else '(Root)'
        )
        preview  = content[:200] + '...' if len(content) > 200 else content
        chunk_id = self._gen_id(header_path, content[:100])

        return ChunkNode(
            id          = chunk_id,
            header_path = header_path,
            content     = content,
            preview     = preview,
            level       = level,
        )

    def _tail_overlap(self, body: str) -> str:
        """
        取前一個 sub-chunk 的尾部作為 overlap。

        1. 先取最後 CHUNK_OVERLAP_CHARS 個字元
        2. 嘗試在句子邊界（。！？.!?\\n）截斷，避免從句子中間切入
        3. 若找不到斷點，直接回傳原始截取結果
        """
        n = KNOWLEDGE_CONSTANTS.CHUNK_OVERLAP_CHARS
        if len(body) <= n:
            return body

        tail = body[-n:]

        # 嘗試找到第一個句子邊界，從那個位置往後才是乾淨的起點
        m = re.search(r'[。！？.!?\n]', tail)
        if m:
            # 從邊界符號後一個字元開始
            start = m.end()
            candidate = tail[start:].strip()
            if candidate:
                return candidate

        return tail.strip()

    def _gen_id(self, header_path: str, content_sample: str) -> str:
        h = hashlib.md5(
            f"{self.parent_id}:{header_path}:{content_sample}".encode()
        ).hexdigest()[:12]
        return f"{self.parent_id}:{h}"


# ── 快捷函式 ──────────────────────────────────────────────────────────────────

def split_markdown(parent_id: str, content: str) -> List[ChunkNode]:
    """切分 Markdown 文件，回傳 ChunkNode 列表。"""
    return MarkdownSplitter(parent_id).split(content)
