# Copyright 2019-2023 SURF.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from orchestrator.workflows import LazyWorkflowInstance

LazyWorkflowInstance("workflows.node.create_node", "create_node")
LazyWorkflowInstance("workflows.node.modify_node", "modify_node")
LazyWorkflowInstance("workflows.node.modify_sync_ports", "modify_sync_ports")
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


LazyWorkflowInstance("workflows.l2vpn.create_l2vpn", "create_l2vpn")
LazyWorkflowInstance("workflows.l2vpn.modify_l2vpn", "modify_l2vpn")
LazyWorkflowInstance("workflows.l2vpn.terminate_l2vpn", "terminate_l2vpn")
LazyWorkflowInstance("workflows.l2vpn.validate_l2vpn", "validate_l2vpn")
LazyWorkflowInstance("workflows.l2vpn.modify_l2vpn", "reconcile_l2vpn")


LazyWorkflowInstance("workflows.nsistp.create_nsistp", "create_nsistp")
LazyWorkflowInstance("workflows.nsistp.modify_nsistp", "modify_nsistp")
LazyWorkflowInstance("workflows.nsistp.terminate_nsistp", "terminate_nsistp")
LazyWorkflowInstance("workflows.nsistp.validate_nsistp", "validate_nsistp")


LazyWorkflowInstance("workflows.nsip2p.create_nsip2p", "create_nsip2p")


LazyWorkflowInstance("workflows.tasks.bootstrap_netbox", "task_bootstrap_netbox")
LazyWorkflowInstance("workflows.tasks.wipe_netbox", "task_wipe_netbox")
