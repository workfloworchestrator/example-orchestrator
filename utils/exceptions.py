# Copyright 2019-2024 SURF.
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

"""Provides ValueError Exception classes."""


class AllowedStatusValueError(ValueError):
    pass


class ASNValueError(ValueError):
    pass


class BGPPolicyValueError(ValueError):
    pass


class BlackHoleCommunityValueError(ValueError):
    pass


class ChoiceValueError(ValueError):
    pass


class DuplicateValueError(ValueError):
    pass


class EndpointTypeValueError(ValueError):
    pass


class FieldValueError(ValueError):
    pass


class FreeSpaceValueError(ValueError):
    pass


class InSyncValueError(ValueError):
    pass


class IPAddressValueError(ValueError):
    pass


class IPPrefixValueError(ValueError):
    pass


class LocationValueError(ValueError):
    pass


class NodesValueError(ValueError):
    pass


class CustomerValueError(ValueError):
    pass


class PeeringValueError(ValueError):
    pass


class PeerGroupNameError(ValueError):
    pass


class PeerNameValueError(ValueError):
    pass


class PeerPortNameValueError(ValueError):
    pass


class PeerPortValueError(ValueError):
    pass


class PortsModeValueError(ValueError):
    def __init__(self, mode: str = "", message: str = ""):
        super().__init__(message)
        self.message = message
        self.mode = mode


class PortsValueError(ValueError):
    pass


class ProductValueError(ValueError):
    pass


class ServicesActiveValueError(ValueError):
    pass


class SubscriptionTypeValueError(ValueError):
    pass


class UnsupportedSpeedValueError(ValueError):
    pass


class UnsupportedTypeValueError(ValueError):
    pass


class VlanRetaggingValueError(ValueError):
    pass


class VlanValueError(ValueError):
    pass


class InUseByAzError(ValueError):
    pass
