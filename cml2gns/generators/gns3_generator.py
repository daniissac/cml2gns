"""
Generator for GNS3 project files.
"""
import json
import logging
import uuid
import zipfile
from pathlib import Path
from cml2gns.models.gns3_model import GNS3Project, GNS3Node, GNS3Link
from cml2gns.utils.validators import validate_gns3_project
from cml2gns.utils.annotations import extract_drawings
from cml2gns.utils.config_transform import ConfigTransformer

logger = logging.getLogger(__name__)


class GNS3Generator:
    """
    Generator for GNS3 project files from parsed CML/VIRL topologies.
    """
    
    def __init__(self, gns3_version=None, gns3_revision=None,
                 config_transformer=None):
        self.gns3_version = gns3_version
        self.gns3_revision = gns3_revision
        self.config_transformer = config_transformer or ConfigTransformer()
    
    def generate(self, topology, output_dir, project_id=None, portable=False):
        """
        Generate a GNS3 project from a parsed topology.
        
        Args:
            topology: The parsed topology (CMLTopology or VIRLTopology)
            output_dir (Path): Directory to save the GNS3 project
            project_id (str): Optional project UUID
            portable (bool): If True, also produce a .gns3p zip archive.
            
        Returns:
            dict: Statistics about the generated project
        """
        logger.info(f"Generating GNS3 project in {output_dir}")
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        kwargs = {}
        if self.gns3_version:
            kwargs["version"] = self.gns3_version
        if self.gns3_revision is not None:
            kwargs["revision"] = self.gns3_revision

        project = GNS3Project(
            name=topology.name,
            project_id=project_id or str(uuid.uuid4()),
            **kwargs,
        )
        
        node_map = {}
        
        for node in topology.nodes.values():
            gns3_node = GNS3Node(
                name=node.label,
                node_type=getattr(node, 'gns3_template', None) or "qemu",
                node_id=str(uuid.uuid4()),
                console_type=getattr(node, 'console_type', None) or "telnet",
                compute_type=getattr(node, 'gns3_compute_type', None) or "qemu",
                x=int(node.x),
                y=int(node.y),
                symbol=getattr(node, 'gns3_symbol', None),
                properties=getattr(node, 'gns3_properties', None) or {},
            )
            
            project.add_node(gns3_node)
            node_map[node.id] = gns3_node.node_id
            
            if node.configuration:
                config_dir = output_dir / "configs"
                config_dir.mkdir(exist_ok=True)

                transformed = self.config_transformer.transform(
                    node.configuration,
                    node_type=getattr(node, 'node_type', None),
                    direction="cml_to_gns3",
                )

                config_file = config_dir / f"{gns3_node.name}_{gns3_node.node_id}.cfg"
                with open(config_file, 'w', encoding='utf-8') as f:
                    f.write(transformed)
                
                logger.debug(f"Saved configuration for node {node.id} to {config_file}")
        
        for link in topology.links.values():
            if link.node1_id in node_map and link.node2_id in node_map:
                gns3_link = GNS3Link(
                    link_id=str(uuid.uuid4()),
                    node1_id=node_map[link.node1_id],
                    node2_id=node_map[link.node2_id],
                    interface1=link.interface1,
                    interface2=link.interface2
                )
                project.add_link(gns3_link)
            else:
                logger.warning(f"Skipping link {link.id}: endpoint not found in node map")
        
        for drawing in extract_drawings(topology):
            project.add_drawing(drawing)

        validate_gns3_project(project)

        project_file = output_dir / f"{project.name}.gns3"
        with open(project_file, 'w', encoding='utf-8') as f:
            json.dump(project.to_dict(), f, indent=2)
        
        logger.info(f"Created GNS3 project file: {project_file}")

        result = {
            "project_file": str(project_file),
            "node_count": len(project.nodes),
            "link_count": len(project.links),
        }

        if portable:
            portable_path = self._create_portable(output_dir, project.name)
            result["portable_file"] = str(portable_path)
            logger.info(f"Created portable project: {portable_path}")

        return result

    @staticmethod
    def _create_portable(output_dir, project_name):
        """Bundle the output directory into a .gns3p zip archive."""
        output_dir = Path(output_dir)
        archive_path = output_dir.parent / f"{project_name}.gns3p"
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path in sorted(output_dir.rglob('*')):
                if file_path.is_file():
                    arcname = file_path.relative_to(output_dir)
                    zf.write(file_path, arcname)
        return archive_path