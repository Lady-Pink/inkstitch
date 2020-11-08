from copy import copy

from inkex import paths, transforms

from ..svg import get_guides
from ..svg.tags import SVG_GROUP_TAG, SVG_PATH_TAG


class Glyph(object):
    """Represents a single character in a single font variant.

    For example, the font inkstitch_small may have variants for left-to-right,
    right-to-left, etc.  Each variant would have a set of Glyphs, one for each
    character in that variant.

    Properties:
      width -- total width of this glyph including all component satins
      node  -- svg:g XML node containing the component satins in this character
    """

    def __init__(self, group):
        """Create a Glyph.

        The nodes will be copied out of their parent SVG document (with nested
        transforms applied).  The original nodes will be unmodified.

        Arguments:
          group -- an svg:g XML node containing all the paths that make up
            this Glyph.  Nested groups are allowed.
        """

        self._process_baseline(group.getroottree().getroot())
        self.node = self._process_group(group)
        self._process_bbox()
        self._move_to_origin()

    def _process_group(self, group):
        new_group = copy(group)
        new_group.attrib.pop('transform', None)
        del new_group[:]  # delete references to the original group's children

        for node in group:
            if node.tag == SVG_GROUP_TAG:
                new_group.append(self._process_group(node))
            else:
                node_copy = copy(node)

                if "d" in node.attrib:
                    # Convert the path to absolute coordinates, incorporating all
                    # nested transforms.
                    path = paths.Path(node.get("d"))
                    path = path.transform(transforms.Transform(node.get("transform")))
                    node_copy.set("d", str(path))

                # Delete transforms from paths and groups, since we applied
                # them to the paths already.
                node_copy.attrib.pop('transform', None)

                new_group.append(node_copy)

        return new_group

    def _process_baseline(self, svg):
        for guide in get_guides(svg):
            if guide.label == "baseline":
                self._baseline = guide.position.y
                break
        else:
            # no baseline guide found, assume 0 for lack of anything better to use...
            self._baseline = 0

    def _process_bbox(self):
        # TODO: Positioning and size of glyphs isn't quiet right yet
        # TODO: Running stitches are way off in the simulator
        # left, right, top, bottom = simpletransform.computeBBox(self.node.iterdescendants())
        bbox = [paths.Path(node.get("d")).bounding_box() for node in self.node.iterdescendants(SVG_PATH_TAG)]
        left, right = min([box.left for box in bbox]), max([box.right for box in bbox])
        self.width = right - left
        self.min_x = left

    def _move_to_origin(self):
        translate_x = -self.min_x
        translate_y = -self._baseline
        transform = transforms.Transform("translate(%s, %s)" % (translate_x, translate_y))

        for node in self.node.iter(SVG_PATH_TAG):
            # node.set('transform', transform)
            # simpletransform.fuseTransform(node)
            path = paths.Path(node.get("d"))
            path = path.transform(transform)
            node.set('d', str(path))
            node.attrib.pop('transform', None)
