"""
Config transformation engine.

Applies lightweight, rule-based transformations to node startup configs
when converting between CML/VIRL and GNS3 environments.  The transforms
handle common differences such as interface naming conventions and
management-plane adjustments.
"""
import re
import logging

logger = logging.getLogger(__name__)


class ConfigTransformer:
    """
    Apply a chain of transformation rules to a node's config text.
    """

    def __init__(self, rules=None):
        self.rules = rules or list(DEFAULT_RULES)

    def transform(self, config_text, node_type=None, direction="cml_to_gns3"):
        """
        Apply all matching transformation rules.

        Args:
            config_text: Raw config string.
            node_type:   CML/VIRL node type (e.g. "iosv", "csr1000v").
            direction:   "cml_to_gns3" or "gns3_to_cml".

        Returns:
            Transformed config string.
        """
        if not config_text:
            return config_text

        for rule in self.rules:
            if rule.matches(node_type, direction):
                config_text = rule.apply(config_text)

        return config_text


class TransformRule:
    """A single regex-based config transformation rule."""

    def __init__(self, name, pattern, replacement, node_types=None,
                 directions=None):
        self.name = name
        self._pattern = re.compile(pattern, re.MULTILINE)
        self._replacement = replacement
        self._node_types = set(node_types) if node_types else None
        self._directions = set(directions) if directions else None

    def matches(self, node_type, direction):
        if self._directions and direction not in self._directions:
            return False
        if self._node_types and node_type and node_type not in self._node_types:
            return False
        return True

    def apply(self, text):
        new_text = self._pattern.sub(self._replacement, text)
        if new_text != text:
            logger.debug(f"Config rule '{self.name}' applied")
        return new_text


DEFAULT_RULES = [
    TransformRule(
        name="loopback_management_strip",
        pattern=r'^interface\s+Management0/0\n(?:.*\n)*?!',
        replacement="!",
        node_types={"iosv", "iosvl2", "csr1000v", "cat8000v"},
        directions={"cml_to_gns3"},
    ),
    TransformRule(
        name="hostname_normalize",
        pattern=r'^hostname\s+"([^"]+)"',
        replacement=r'hostname \1',
        directions={"cml_to_gns3", "gns3_to_cml"},
    ),
    TransformRule(
        name="enable_secret_placeholder",
        pattern=r'^enable secret \d+ \S+',
        replacement='enable secret 0 cisco',
        directions={"cml_to_gns3"},
    ),
    TransformRule(
        name="nxos_feature_telnet",
        pattern=r'^(feature telnet)',
        replacement=r'! \1  (disabled for GNS3)',
        node_types={"nxosv", "nxosv9000"},
        directions={"cml_to_gns3"},
    ),
    TransformRule(
        name="cml_platform_specific_strip",
        pattern=r'^platform\s+.*$',
        replacement='',
        node_types={"csr1000v", "cat8000v", "iosxrv9000"},
        directions={"cml_to_gns3"},
    ),
]
