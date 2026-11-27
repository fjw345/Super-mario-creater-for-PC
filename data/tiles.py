"""Editor tile table. One entry per palette slot, in key order (1..9, 0).

To add a tile: add its ID to constants.py, add one TileDef here, and add a
creator to CustomLevel.TILE_CREATORS. The editor palette, preview, drawing
and names are all driven from this table.
"""

from collections import namedtuple

from . import constants as c

# icon / world: (sheet, x, y, w, h) cut from a sprite sheet, or a name of a
# composed image the editor builds itself ('pipe', 'koopa', 'flagpole').
# anchor: how a placed tile is aligned to its grid cell when drawn.
#   'cell'   - drawn at the cell's top-left
#   'bottom' - drawn so the image's bottom edge sits on the cell's bottom
TileDef = namedtuple('TileDef', 'id zh en icon world anchor')

TILES = (
    TileDef(c.TILE_GROUND, '地面', 'GROUND',
            ('tile_set', 0, 16, 16, 16), None, 'cell'),
    TileDef(c.TILE_COIN_BOX, '升级问号砖', 'UPGRADE QUESTION BOX',
            ('tile_set', 384, 0, 16, 16), None, 'cell'),
    TileDef(c.TILE_PIPE, '管道', 'PIPE',
            'pipe_icon', 'pipe', 'cell'),
    TileDef(c.TILE_GOOMBA, '栗子怪', 'GOOMBA',
            ('smb_enemies_sheet', 0, 4, 16, 16), None, 'cell'),
    TileDef(c.TILE_KOOPA, '乌龟', 'KOOPA',
            'koopa_icon', 'koopa', 'bottom'),
    TileDef(c.TILE_COIN, '金币问号砖', 'COIN QUESTION BOX',
            ('tile_set', 416, 0, 16, 16), None, 'cell'),
    TileDef(c.TILE_BRICK, '砖块', 'BRICK',
            ('tile_set', 16, 0, 16, 16), None, 'cell'),
    TileDef(c.TILE_FLAG, '旗杆', 'FLAGPOLE',
            ('item_objects', 128, 32, 16, 16), 'flagpole', 'bottom'),
    TileDef(c.TILE_MUSHROOM, '蘑菇', 'MUSHROOM',
            ('item_objects', 0, 0, 16, 16), None, 'cell'),
    TileDef(c.TILE_FIREFLOWER, '火焰花', 'FIRE FLOWER',
            ('item_objects', 0, 32, 16, 16), None, 'cell'),
)

TILES_BY_ID = {t.id: t for t in TILES}
PALETTE_IDS = tuple(t.id for t in TILES)


def display_name(tile_id, lang):
    """Localized name for the palette; unknown IDs fall back to the ID."""
    tile = TILES_BY_ID.get(tile_id)
    if tile is None:
        return tile_id if lang == 'zh' else str(tile_id).upper()
    return tile.zh if lang == 'zh' else tile.en
