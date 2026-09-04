# -*- coding: utf-8 -*-

# Copyright: (c) 2017, Simon Dodsley <simon@everpuredata.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type


class ModuleDocFragment(object):
    # Standard Everpure documentation fragment
    DOCUMENTATION = r"""
options:
  - See separate platform section for more details
requirements:
  - See separate platform section for more details
notes:
  - Ansible modules are available for the following Everpure products: FlashArray, FlashBlade
"""

    # Documentation fragment for FlashArray
    FA = r"""
options:
  fa_url:
    description:
      - FlashArray management IPv4 address or Hostname.
    type: str
  api_token:
    description:
      - FlashArray API token for admin privileged user.
    type: str
  id_token:
    description:
      - A pre-signed JWT to authenticate with, as an alternative to I(api_token).
      - The token is exchanged by the array for a short-lived access token.
      - Requires a matching API Client to be registered on the array
        (see M(everpure.flasharray.purefa_apiclient)).
    type: str
    version_added: '1.43.0'
  private_key_file:
    description:
      - Path to the PEM RSA private key used to sign an identity token,
        as an alternative to I(api_token).
      - Requires I(client_id), I(key_id), I(issuer) and I(username).
    type: str
    version_added: '1.43.0'
  private_key_password:
    description:
      - Password protecting I(private_key_file), if encrypted.
    type: str
    version_added: '1.43.0'
  username:
    description:
      - Username the issued token should be granted to.
      - Must be a valid user on the array. Used with I(private_key_file).
    type: str
    version_added: '1.43.0'
  client_id:
    description:
      - ID of the API Client that issues the identity token.
      - Used with I(private_key_file).
    type: str
    version_added: '1.43.0'
  key_id:
    description:
      - Key ID of the API Client that issues the identity token.
      - Used with I(private_key_file).
    type: str
    version_added: '1.43.0'
  issuer:
    description:
      - The API Client's trusted identity issuer registered on the array.
      - Used with I(private_key_file).
    type: str
    version_added: '1.43.0'
  disable_warnings:
    description:
     - Disable insecure certificate warnings in debug logs
    type: bool
    default: false
    version_added: '1.29.0'
notes:
  - This module requires the C(py-pure-client) Python library.
  - Additional Python libraries may be required for specific modules.
  - You must set C(PUREFA_URL) and C(PUREFA_API) environment variables
    if I(fa_url) and I(api_token) arguments are not passed to the module directly.
  - Token-based authentication (I(id_token), or I(private_key_file) with
    I(client_id), I(key_id), I(issuer) and I(username)) may be used as an
    alternative to I(api_token), and requires a matching API Client registered
    on the array via M(everpure.flasharray.purefa_apiclient).
requirements:
  - python >= 3.3
  - purestorage >= 1.19
  - py-pure-client >= 1.90.0
  - netaddr
  - requests
  - pycountry
  - urllib3
"""
