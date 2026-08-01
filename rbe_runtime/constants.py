"""Version and execution constants for the RBE runtime foundation.

The methodology profile's identity used to live here, which made the runtime capable
of exactly one methodology by construction. It now lives in
`controlled_authority.profiles`, where more than one can be declared. Only the
architecture's own version remains a constant: the runtime is one RBE release.
"""

ENGINE_VERSION = "0.1.0"
RUNTIME_SCHEMA_VERSION = "1.0.0"
RBE_RELEASE = "1.1.0"

