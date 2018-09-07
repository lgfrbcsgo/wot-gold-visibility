from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED
from wand.image import Image
from wand.drawing import Drawing
from wand.color import Color

from mod.sprite_layout import sprite_layout


def transparent(width, height):
    img = Image(width=width, height=height)
    img.background_color = Color('rgba(255, 255, 255, 1)')
    return img


def resize(image, width, height):
    with image.clone() as src:
        src.transform(resize='%ix%i' % (width, height))
        hoffset = (height - src.height) / 2
        woffset = (width - src.width) / 2

        dest = transparent(width, height)
        dest.composite(src, int(woffset) if woffset > 0 else 0, int(hoffset) if hoffset > 0 else 0)
        dest.format = src.format
        return dest


def multiply_color(image, color):
    parsed_color = Color(color)
    image.evaluate('multiply', parsed_color.red, channel='red')
    image.evaluate('multiply', parsed_color.green, channel='green')
    image.evaluate('multiply', parsed_color.blue, channel='blue')
    image.evaluate('multiply', parsed_color.alpha, channel='alpha')
    return image


def set_color(image, color, luminize=False):
    with Drawing() as draw:
        parsed_color = Color(color)
        draw.fill_color = parsed_color
        draw.color(0, 0, 'reset')
        if luminize:
            draw.composite('luminize', 0, 0, image.width, image.height, image)
        draw.composite('copy_opacity', 0, 0, image.width, image.height, image)
        draw(image)
        image.evaluate('multiply', parsed_color.alpha, channel='alpha')
        return image


def make_custom_texture(icon, color=None, luminize=False):
    with Image(blob=icon) as src:
        dest = transparent(4096, 4096)

        sizes = dict()
        for width, height, bbox in sprite_layout:
            sizes[(width, height)] = None

        for width, height in sizes.keys():
            sizes[(width, height)] = resize(src, width, height)
            if color is not None:
                set_color(sizes[(width, height)], color, luminize)

        for width, height, bbox in sprite_layout:
            xstart, ystart, xend, yend = bbox

            for x in range(xstart, xend, width):
                for y in range(ystart, yend, height):
                    dest.composite(sizes[(width, height)], x, y)

        for size in sizes.values():
            size.close()

        dest.format = 'dds'
        return dest


def make_texture(color=None, file=None, luminize=False):
    if file is not None:
        return make_custom_texture(file, color, luminize)

    texture = Image(filename='mod/texture.dds')
    if color is not None:
        return multiply_color(texture, color)

    raise ValueError('Neither color or file given!')


def make_mod(color=None, file=None, luminize=False):
    with BytesIO() as wotmod_file, BytesIO as zip_file:
        with make_texture(color, file, luminize) as texture, ZipFile(wotmod_file, 'w') as mod:
            mod.writestr('res/particles/content_deferred/PFX_textures/eff_tex_prem.dds', texture.make_blob())
            with resize(texture, 2048, 2048) as resized:
                mod.writestr('res/particles/content_forward/PFX_textures/eff_tex_prem.dds', resized.make_blob())

        with ZipFile(zip_file, 'w', ZIP_DEFLATED) as zip:
            zip.writestr('goldvisibility.color.wotmod', wotmod_file.getvalue())

        return zip_file.getvalue()
