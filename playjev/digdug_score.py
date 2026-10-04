"""Partial exact Dig Dug HUD font; unseen glyphs remain unknown, never OCR guesses."""
import io
from PIL import Image

# Seven native pixels per glyph, eight-pixel slots. Labeled native 0/10/20/30 HUDs.
FONT={
    '0':['..###..','.##.##.','##...##','##...##','##...##','.##.##.','..###..'],
    '1':['...##..','..###..','...##..','...##..','...##..','...##..','.######'],
    '2':['.#####.','##...##','.....##','..####.','###....','##.....','#######'],
    '3':['######.','.....##','.....##','.#####.','.....##','.....##','######.'],
}


def playfield_visible(source):
    # The blue playfield header is absent on the native title screen. Extra-life
    # blocks can be zero while the last life is still playable: they are not a gate.
    return sum(1 for y in range(3,19) for x in range(12,148)
               if (lambda c:c[0]<100 and c[1]<100 and c[2]>120)(source.getpixel((x,y))))>500


def digit_grids(frame):
    source=Image.open(io.BytesIO(frame)).convert('RGB')
    if source.size!=(160,210):raise ValueError('Dig Dug HUD needs a native 160x210 frame')
    if not playfield_visible(source):return [['.'*7]*7 for _ in range(6)]
    def foreground(x,y):
        r,g,b=source.getpixel((x,y))
        return 180<r<215 and 90<g<120 and 40<b<80
    return [[''.join('#' if foreground(x,y) else '.' for x in range(left,left+7))
             for y in range(181,188)] for left in (100,108,116,124,132,140)]
