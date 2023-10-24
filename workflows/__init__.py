from orchestrator.workflows import LazyWorkflowInstance

LazyWorkflowInstance("workflows.node.create_node", "create_node")
LazyWorkflowInstance("workflows.node.modify_node", "modify_node")
LazyWorkflowInstance("workflows.node.terminate_node", "terminate_node")
LazyWorkflowInstance("workflows.node.validate_node", "validate_node")
