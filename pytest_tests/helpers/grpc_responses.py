import re

# Regex patterns of status codes of Container service (https://github.com/nspcc-dev/neofs-spec/blob/98b154848116223e486ce8b43eaa35fec08b4a99/20-api-v2/container.md)
CONTAINER_NOT_FOUND = "code = 3072.*message = container not found"


# Regex patterns of status codes of Object service (https://github.com/nspcc-dev/neofs-spec/blob/98b154848116223e486ce8b43eaa35fec08b4a99/20-api-v2/object.md)
MALFORMED_REQUEST = "code = 1024.*message = malformed request"
WRONG_CONTAINER = "code = 1024.*message = wrong container"
SESSION_NOT_ISSUED_BY_OWNER = "code = 1024.*message = session was not issued by the container owner"
OBJECT_ACCESS_DENIED = "code = 2048.*message = access to object operation denied"
OBJECT_NOT_FOUND = "code = 2049.*message = object not found"
OBJECT_ALREADY_REMOVED = "code = 2052.*message = object already removed"
SESSION_NOT_FOUND = "code = 4096.*message = session token not found"
OUT_OF_RANGE = "code = 2053.*message = out of range"
EXPIRED_SESSION_TOKEN = "code = 4097.*message = expired session token"
# TODO: Due to https://github.com/nspcc-dev/neofs-node/issues/2092 we have to check only codes until fixed
# OBJECT_IS_LOCKED = "code = 2050.*message = object is locked"
# LOCK_NON_REGULAR_OBJECT = "code = 2051.*message = ..." will be available once 2092 is fixed
OBJECT_IS_LOCKED = "code = 2050"
LOCK_NON_REGULAR_OBJECT = "code = 2051"

LIFETIME_REQUIRED = "expiration epoch or lifetime period is required"
LOCK_OBJECT_REMOVAL = "lock object removal"
LOCK_OBJECT_EXPIRATION = "lock object expiration: {expiration_epoch}; current: {current_epoch}"
INVALID_RANGE_ZERO_LENGTH = "invalid '{range}' range: zero length"
INVALID_RANGE_OVERFLOW = "invalid '{range}' range: uint64 overflow"
INVALID_OFFSET_SPECIFIER = "invalid '{range}' range offset specifier"
INVALID_LENGTH_SPECIFIER = "invalid '{range}' range length specifier"

NOT_CONTAINER_OWNER = "provided account differs with the container owner"
NOT_SESSION_CONTAINER_OWNER = "session issuer differs with the container owner"
TIMED_OUT = "timed out after \\d+ seconds"
CONTAINER_DELETION_TIMED_OUT = "container deletion: await timeout expired"

EACL_TIMED_OUT = "eACL setting: await timeout expired"
EACL_TABLE_IS_NOT_SET = "extended ACL table is not set for this container"
EACL_NOT_FOUND = "code = 3073.*message = eACL not found"
EACL_PROHIBITED_TO_MODIFY_SYSTEM_ACCESS = (
    "table validation: it is prohibited to modify system access"
)


def error_matches_status(error: Exception, status_pattern: str) -> bool:
    """
    Determines whether exception matches specified status pattern.

    We use re.search to be consistent with pytest.raises.
    """
    match = re.search(status_pattern, str(error))
    return match is not None
