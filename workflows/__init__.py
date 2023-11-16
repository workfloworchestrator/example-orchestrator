from orchestrator.workflows import LazyWorkflowInstance

LazyWorkflowInstance("workflows.node.create_node", "create_node")
LazyWorkflowInstance("workflows.node.modify_node", "modify_node")
LazyWorkflowInstance("workflows.node.update_node_interfaces", "update_node_interfaces")
LazyWorkflowInstance("workflows.node.terminate_node", "terminate_node")
LazyWorkflowInstance("workflows.node.validate_node", "validate_node")


LazyWorkflowInstance("workflows.port.create_port", "create_port")
LazyWorkflowInstance("workflows.port.modify_port", "modify_port")
LazyWorkflowInstance("workflows.port.terminate_port", "terminate_port")
LazyWorkflowInstance("workflows.port.validate_port", "validate_port")


LazyWorkflowInstance("workflows.core_link.create_core_link", "create_core_link")
LazyWorkflowInstance("workflows.core_link.modify_core_link", "modify_core_link")
LazyWorkflowInstance("workflows.core_link.terminate_core_link", "terminate_core_link")
LazyWorkflowInstance("workflows.core_link.validate_core_link", "validate_core_link")
