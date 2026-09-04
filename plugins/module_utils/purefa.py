# -*- coding: utf-8 -*-

# This code is part of Ansible, but is an independent component.
# This particular file snippet, and this file snippet only, is BSD licensed.
# Modules you write using this snippet, which is embedded dynamically by Ansible
# still belong to the author of the module, and may assign their own license
# to the complete work.
#
# Copyright (c), Simon Dodsley <simon@everpuredata.com>,2017
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright notice,
#      this list of conditions and the following disclaimer in the documentation
#      and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE
# USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from __future__ import absolute_import, division, print_function

__metaclass__ = type

HAS_URLLIB3 = True
try:
    import urllib3
except ImportError:
    HAS_URLLIB3 = False

HAS_DISTRO = True
try:
    import distro
except ImportError:
    HAS_DISTRO = False

HAS_PYPURECLIENT = True
try:
    from pypureclient import flasharray
except ImportError:
    HAS_PYPURECLIENT = False

from os import environ
import platform

VERSION = 1.5
USER_AGENT_BASE = "Ansible"


def get_array(module):
    """Return System Object or Fail"""
    if HAS_URLLIB3 and module.params["disable_warnings"]:
        urllib3.disable_warnings()
    if HAS_DISTRO:
        user_agent = "%(base)s %(class)s/%(version)s (%(platform)s)" % {
            "base": USER_AGENT_BASE,
            "class": __name__,
            "version": VERSION,
            "platform": distro.name(pretty=True),
        }
    else:
        user_agent = "%(base)s %(class)s/%(version)s (%(platform)s)" % {
            "base": USER_AGENT_BASE,
            "class": __name__,
            "version": VERSION,
            "platform": platform.platform(),
        }
    if not HAS_PYPURECLIENT:
        module.fail_json(msg="py-pure-client and/or requests are not installed.")

    # Module parameters take precedence over the matching PUREFA_* env vars.
    # Three mutually-exclusive authentication modes are supported:
    #   1. api_token - static API token (default, backwards compatible).
    #   2. id_token - a pre-signed JWT, exchanged by the array for an access
    #      token.
    #   3. private_key_file with client_id, key_id, issuer and username - the
    #      SDK signs the JWT locally before exchange.
    # Modes 2 and 3 require a matching API Client registered on the array
    # (see the purefa_apiclient module).
    target = module.params["fa_url"] or environ.get("PUREFA_URL")
    api = module.params["api_token"] or environ.get("PUREFA_API")
    id_token = module.params.get("id_token") or environ.get("PUREFA_ID_TOKEN")
    private_key_file = module.params.get("private_key_file") or environ.get(
        "PUREFA_PRIVATE_KEY_FILE"
    )
    private_key_password = module.params.get("private_key_password") or environ.get(
        "PUREFA_PRIVATE_KEY_PASSWORD"
    )
    username = module.params.get("username") or environ.get("PUREFA_USERNAME")
    client_id = module.params.get("client_id") or environ.get("PUREFA_CLIENT_ID")
    key_id = module.params.get("key_id") or environ.get("PUREFA_KEY_ID")
    issuer = module.params.get("issuer") or environ.get("PUREFA_ISSUER")

    common = {"target": target, "user_agent": user_agent}

    if target and api:
        system = flasharray.Client(api_token=api, **common)
    elif target and id_token:
        system = flasharray.Client(id_token=id_token, **common)
    elif target and private_key_file and client_id and key_id and issuer and username:
        system = flasharray.Client(
            private_key_file=private_key_file,
            private_key_password=private_key_password,
            client_id=client_id,
            key_id=key_id,
            issuer=issuer,
            username=username,
            **common,
        )
    else:
        module.fail_json(
            msg="You must set PUREFA_URL and PUREFA_API environment variables "
            "or the fa_url and api_token module arguments. Alternatively, use "
            "token-based authentication via id_token, or private_key_file with "
            "client_id, key_id, issuer and username (or the matching PUREFA_* "
            "environment variables)."
        )
    try:
        system.get_hardware()
    except Exception:
        module.fail_json(
            msg="Everpure FlashArray authentication failed. Check your credentials"
        )
    return system


def purefa_argument_spec():
    """Return standard base dictionary used for the argument_spec argument in AnsibleModule"""

    return dict(
        fa_url=dict(),
        api_token=dict(no_log=True),
        # OAuth2 / API-client token authentication (alternatives to api_token).
        # See the purefa_apiclient module for registering the trusted key.
        id_token=dict(no_log=True),
        private_key_file=dict(no_log=False),
        private_key_password=dict(no_log=True),
        username=dict(),
        client_id=dict(),
        key_id=dict(no_log=False),
        issuer=dict(),
        disable_warnings=dict(type="bool", default=False),
    )
