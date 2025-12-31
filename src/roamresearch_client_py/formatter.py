from typing import cast
import re

REF_PATTERN = r'\(\(([a-zA-Z0-9_-]*?)\)\)'


def extract_ref(text):
    return re.findall(REF_PATTERN, text)


def _get_sorted_children(block):
    """Get direct children of a block, sorted by order."""
    children = block.get(':block/children', [])
    if not children:
        return []
    return sorted(children, key=lambda x: x.get(':block/order', 0))


def _collect_children_flat(block, min_level=2, current_level=1):
    """
    Recursively collect children blocks, flattened.
    Only include blocks at min_level or deeper.
    current_level is the level of `block`, its children are at current_level + 1.
    """
    result = []
    direct_children = _get_sorted_children(block)
    child_level = current_level + 1

    for child in direct_children:
        if child_level >= min_level:
            result.append(child)
        result.extend(_collect_children_flat(child, min_level, child_level))

    return result


def _flatten_all_blocks(block):
    """Recursively flatten all blocks for reference resolution."""
    blocks = [block]
    for child in block.get(':block/children', []):
        blocks.extend(_flatten_all_blocks(child))
    return blocks


def _resolve_refs(text, all_blocks):
    """Replace block references ((uid)) with actual text."""
    refs = extract_ref(text)
    for ref in refs:
        node = next((b for b in all_blocks if b.get(':block/uid') == ref), None)
        if node:
            text = text.replace(f"(({ref}))", node.get(':block/string', ''))
    return text


def format_ref_block(ref_uid: str, block: dict, depth: int = 0, max_depth: int = 2) -> str:
    """
    Format a referenced block with its children as a quoted block.

    Args:
        ref_uid: The UID of the referenced block
        block: The block data (with :block/string, :block/children, etc.)
        depth: Current recursion depth
        max_depth: Maximum recursion depth for nested refs

    Returns:
        Formatted string with blockquote format
    """
    if not block:
        return f"> **((_{ref_uid}_))**: _[not found]_"

    text = block.get(':block/string', '')
    lines = [f"> **((_{ref_uid}_))**: {text}"]

    # Add children as nested items
    children = _get_sorted_children(block)
    for child in children:
        child_text = child.get(':block/string', '')
        lines.append(f">   - {child_text}")

        # Recursively add grandchildren (up to one level)
        grandchildren = _get_sorted_children(child)
        for grandchild in grandchildren:
            gc_text = grandchild.get(':block/string', '')
            lines.append(f">     - {gc_text}")

    return '\n'.join(lines)


def expand_refs_in_text(text: str, ref_blocks: dict, depth: int = 0, max_depth: int = 2) -> str:
    """
    Expand block references in text to show their content.

    Args:
        text: Text containing ((uid)) references
        ref_blocks: Dict mapping uid -> block data
        depth: Current recursion depth
        max_depth: Maximum recursion depth

    Returns:
        Text with refs expanded as blockquotes after the line
    """
    refs = extract_ref(text)
    if not refs:
        return text

    expanded_parts = []
    for ref_uid in refs:
        if ref_uid in ref_blocks:
            block = ref_blocks[ref_uid]
            expanded = format_ref_block(ref_uid, block, depth, max_depth)
            expanded_parts.append(expanded)

    if expanded_parts:
        return text + '\n\n' + '\n\n'.join(expanded_parts)
    return text


def _format_block_text(block, all_blocks):
    """Format a single block's text with heading prefix if applicable."""
    text = block.get(':block/string', '')
    text = _resolve_refs(text, all_blocks)

    heading = block.get(':block/heading')
    if heading:
        prefix = '#' * heading
        return f"{prefix} {text}"
    return text


def _is_table_block(block):
    """Check if block is a Roam table."""
    text = block.get(':block/string', '')
    return text.strip() == '{{[[table]]}}'


def _is_code_block(block):
    """Check if block is a code block."""
    text = block.get(':block/string', '')
    return text.strip().startswith('```')


def _collect_row_cells(row_block, all_blocks):
    """
    Collect cells from a table row.
    In Roam tables, cells are horizontally nested (each cell is child of previous).
    """
    cells = [row_block.get(':block/string', '')]
    current = row_block

    while True:
        children = _get_sorted_children(current)
        if not children:
            break
        # Take first child as next cell in row
        current = children[0]
        cells.append(current.get(':block/string', ''))

    return cells


def _format_table(block, all_blocks):
    """Format a Roam table as GFM table."""
    rows = _get_sorted_children(block)
    if not rows:
        return ''

    table_data = []
    for row in rows:
        cells = _collect_row_cells(row, all_blocks)
        # Resolve refs in each cell
        cells = [_resolve_refs(c, all_blocks) for c in cells]
        table_data.append(cells)

    if not table_data:
        return ''

    # Determine column count
    max_cols = max(len(row) for row in table_data)

    # Pad rows to same length
    for row in table_data:
        while len(row) < max_cols:
            row.append('')

    lines = []
    # Header row
    lines.append('| ' + ' | '.join(table_data[0]) + ' |')
    # Separator
    lines.append('| ' + ' | '.join(['---'] * max_cols) + ' |')
    # Data rows
    for row in table_data[1:]:
        lines.append('| ' + ' | '.join(row) + ' |')

    return '\n'.join(lines)


def format_block_as_markdown(blocks, all_blocks=None):
    """
    Format Roam blocks as GFM markdown.

    - Blocks with :block/heading become headings (#, ##, ###)
    - Top-level blocks without heading become paragraphs
    - Level 1 children: headings or paragraphs
    - Level 2+ children become a flat bullet list
    - {{[[table]]}} blocks become GFM tables
    """
    if all_blocks is None:
        all_blocks = []
        for b in blocks:
            all_blocks.extend(_flatten_all_blocks(b))

    lines = []

    for block in blocks:
        # Handle table blocks
        if _is_table_block(block):
            if lines:
                lines.append('')
            lines.append(_format_table(block, all_blocks))
            lines.append('')
            continue

        text = _format_block_text(block, all_blocks)
        heading = block.get(':block/heading')

        if heading:
            # Heading: add blank line before if not first
            if lines:
                lines.append('')
            lines.append(text)
        else:
            # Paragraph
            lines.append(text)

        lines.append('')

        # Level 1 children: headings or paragraphs
        level1_children = _get_sorted_children(block)
        for child in level1_children:
            if _is_table_block(child):
                lines.append(_format_table(child, all_blocks))
                lines.append('')
                continue

            child_text = _format_block_text(child, all_blocks)
            child_heading = child.get(':block/heading')

            if child_heading:
                if lines:
                    lines.append('')
                lines.append(child_text)
            else:
                lines.append(child_text)

            lines.append('')

            # Level 2+ children: list items (except code blocks)
            deep_children = _collect_children_flat(child, min_level=2, current_level=1)
            if deep_children:
                list_items = []
                for deep_child in deep_children:
                    deep_text = deep_child.get(':block/string', '')
                    deep_text = _resolve_refs(deep_text, all_blocks)

                    if _is_code_block(deep_child):
                        # Flush pending list items
                        if list_items:
                            lines.extend(list_items)
                            list_items = []
                            lines.append('')
                        # Output code block as-is
                        lines.append(deep_text)
                        lines.append('')
                    else:
                        list_items.append(f"- {deep_text}")

                # Flush remaining list items
                if list_items:
                    lines.extend(list_items)
                    lines.append('')

    return '\n'.join(lines).strip()

def format_block(i, nodes, indent=0):
    lines = []
    text = i[':block/string']
    refs = extract_ref(text)
    if refs:
        for ref in refs:
            node = next((k for k in nodes if k[':block/uid'] == ref), None)
            if node:
                text = text.replace(f"(({ref}))", node[':block/string'])
        for ref in i.get(':block/refs', []):
            if ":block/string" in ref:
                text = text.replace(f"(({ref[':block/uid']}))", ref[':block/string'])
    if indent > 0:
        lines.append(f"{'='*indent}> {text}")
    else:
        lines.append(text)
    if ':block/children' in i and len(i[':block/children']) > 0:
        children = filter(lambda x: x is not None,
                          [next((k for k in nodes if k[':db/id'] == j[':db/id']), None) for j in i.get(':block/children', [])])
        sorted_nodes = sorted(children, key=lambda k: cast(dict, k).get(':block/order', 0))
        for j in sorted_nodes:
            lines.append(format_block(j, nodes, indent+2))
    return "\n".join(lines)


def _build_ref_map(blocks: list, ref_map: dict | None = None) -> dict:
    """Build a map of uid -> block for reference resolution."""
    if ref_map is None:
        ref_map = {}
    for block in blocks:
        uid = block.get(':block/uid')
        if uid:
            ref_map[uid] = block
        # Include refs that came with the block
        for ref in block.get(':block/refs', []):
            ref_uid = ref.get(':block/uid')
            if ref_uid and ref_uid not in ref_map:
                ref_map[ref_uid] = ref
        # Recurse into children
        children = block.get(':block/children', [])
        if children:
            _build_ref_map(children, ref_map)
    return ref_map


def _resolve_all_refs(text: str, ref_map: dict, depth: int = 1) -> str:
    """
    Replace ((uid)) references with their text content.

    Args:
        text: Text containing ((uid)) references
        ref_map: Map of uid -> block for resolution
        depth: How many levels deep to resolve (1 = direct refs only)

    Returns:
        Text with refs resolved up to specified depth
    """
    if depth <= 0:
        return text

    for _ in range(depth):
        refs = extract_ref(text)
        if not refs:
            break
        resolved_any = False
        for ref_uid in refs:
            if ref_uid in ref_map:
                ref_block = ref_map[ref_uid]
                ref_text = ref_block.get(':block/string', '')
                text = text.replace(f"(({ref_uid}))", ref_text)
                resolved_any = True
        if not resolved_any:
            break  # No more refs to resolve in current map
    return text


def get_unresolved_refs(text: str, ref_map: dict) -> set:
    """Get UIDs of references not in the ref_map."""
    refs = extract_ref(text)
    return {uid for uid in refs if uid not in ref_map}


def collect_all_text_refs(blocks: list, ref_map: dict | None = None) -> set:
    """
    Collect all ((uid)) references from block text that aren't in ref_map.

    Args:
        blocks: List of blocks to scan
        ref_map: Existing reference map (refs here are excluded)

    Returns:
        Set of UIDs that need to be fetched
    """
    if ref_map is None:
        ref_map = {}

    unresolved = set()

    def scan_block(block):
        text = block.get(':block/string', '')
        for uid in extract_ref(text):
            if uid not in ref_map:
                unresolved.add(uid)
        for child in block.get(':block/children', []):
            scan_block(child)

    for block in blocks:
        scan_block(block)

    return unresolved


def _format_hierarchical_block(
    block: dict,
    ref_map: dict,
    indent_depth: int = 0,
    is_top_level: bool = False,
    resolve_depth: int = 1
) -> list[str]:
    """
    Format a single block and its children hierarchically.

    Args:
        block: Block dict with :block/string, :block/children, etc.
        ref_map: Map of uid -> block for reference resolution
        indent_depth: Current indentation depth (0 = top level)
        is_top_level: If True, don't add bullet prefix at depth 0
        resolve_depth: How many levels deep to resolve refs

    Returns:
        List of formatted lines
    """
    lines = []
    text = block.get(':block/string', '')

    # Skip empty blocks
    if not text.strip():
        # Still process children even if this block is empty
        children = _get_sorted_children(block)
        for child in children:
            lines.extend(_format_hierarchical_block(child, ref_map, indent_depth, is_top_level=False, resolve_depth=resolve_depth))
        return lines

    # Resolve references
    text = _resolve_all_refs(text, ref_map, depth=resolve_depth)

    # Handle special block types
    if _is_table_block(block):
        table_md = _format_table(block, list(ref_map.values()))
        if table_md:
            indent = '  ' * indent_depth
            for line in table_md.split('\n'):
                lines.append(f"{indent}{line}")
            lines.append('')
        return lines

    # Handle headings
    heading = block.get(':block/heading')
    if heading:
        prefix = '#' * heading
        text = f"{prefix} {text}"

    # Format the block line
    indent = '  ' * indent_depth
    if indent_depth == 0 and is_top_level:
        # Top-level blocks: no bullet, just text
        lines.append(text)
    else:
        # Nested blocks: bullet with indentation
        lines.append(f"{indent}- {text}")

    # Process children recursively
    children = _get_sorted_children(block)
    for child in children:
        lines.extend(_format_hierarchical_block(child, ref_map, indent_depth + 1, is_top_level=False, resolve_depth=resolve_depth))

    return lines


def format_blocks_hierarchical(
    blocks: list,
    resolve_depth: int = 1,
    top_level_as_paragraphs: bool = True,
    ref_map: dict | None = None
) -> str:
    """
    Format Roam blocks as hierarchical markdown preserving parent-child structure.

    This formatter maintains the tree structure of Roam blocks, outputting nested
    bullet lists that mirror the block hierarchy in Roam Research.

    Args:
        blocks: List of top-level blocks (each may have :block/children)
        resolve_depth: How many levels deep to resolve refs (0 = disable, 1+ = levels)
        top_level_as_paragraphs: If True, top-level blocks are paragraphs;
                                 if False, all blocks use bullet syntax
        ref_map: Optional pre-built reference map (for external refs)

    Returns:
        Hierarchical markdown string

    Example output:
        Top level block

        - Child 1
          - Grandchild 1
          - Grandchild 2
        - Child 2
    """
    if not blocks:
        return ''

    # Build reference map for resolution
    if ref_map is None:
        ref_map = _build_ref_map(blocks) if resolve_depth > 0 else {}
    elif resolve_depth > 0:
        # Merge with refs from blocks
        _build_ref_map(blocks, ref_map)

    lines = []

    for block in blocks:
        text = block.get(':block/string', '')

        # Handle special cases at top level
        if _is_table_block(block):
            table_md = _format_table(block, list(ref_map.values()))
            if table_md:
                lines.append(table_md)
                lines.append('')
            continue

        if text.strip():
            # Resolve refs in top-level text
            if resolve_depth > 0:
                text = _resolve_all_refs(text, ref_map, depth=resolve_depth)

            # Handle heading
            heading = block.get(':block/heading')
            if heading:
                prefix = '#' * heading
                text = f"{prefix} {text}"

            if top_level_as_paragraphs:
                lines.append(text)
                lines.append('')
            else:
                lines.append(f"- {text}")

        # Process children
        children = _get_sorted_children(block)
        if children:
            for child in children:
                child_lines = _format_hierarchical_block(
                    child,
                    ref_map,
                    indent_depth=0,
                    is_top_level=False,
                    resolve_depth=resolve_depth
                )
                lines.extend(child_lines)
            lines.append('')  # Blank line after children group

    # Clean up multiple blank lines
    result = '\n'.join(lines)
    while '\n\n\n' in result:
        result = result.replace('\n\n\n', '\n\n')

    return result.strip()
