import datetime
import logging
import os
from datetime import datetime, timedelta
from typing import Optional

import allure
import s3_gate_bucket
import s3_gate_object
from dateutil.parser import parse

logger = logging.getLogger("NeoLogger")


ACL_TO_PERMISSION_MAP_BUCKET = {
    "Group": {
        "public-read-write": "FULL_CONTROL",
        "grant-full-control": "FULL_CONTROL",
        "public-read": "READ",
        "grant-read": "READ",
        "authenticated-read": "READ",
        "grant-write": "WRITE",
    },
    "CanonicalUser": {
        "public-read-write": "FULL_CONTROL",
        "grant-full-control": "FULL_CONTROL",
        "public-read": "FULL_CONTROL",
        "grant-read": "FULL_CONTROL",
        "authenticated-read": "FULL_CONTROL",
        "grant-write": "FULL_CONTROL",
        "private": "FULL_CONTROL",
    },
}

ACL_TO_PERMISSION_MAP_OBJECT = {
    "Group": {
        "public-read-write": "FULL_CONTROL",
        "grant-full-control": "FULL_CONTROL",
        "public-read": "READ",
        "grant-read": "READ",
        "authenticated-read": "READ",
    },
    "CanonicalUser": {
        "public-read-write": "FULL_CONTROL",
        "grant-full-control": "FULL_CONTROL",
        "public-read": "FULL_CONTROL",
        "grant-read": "FULL_CONTROL",
        "authenticated-read": "FULL_CONTROL",
        "private": "FULL_CONTROL",
    },
}


@allure.step("Expected all objects are presented in the bucket")
def check_objects_in_bucket(
    s3_client, bucket, expected_objects: list, unexpected_objects: Optional[list] = None
) -> None:
    unexpected_objects = unexpected_objects or []
    bucket_objects = s3_gate_object.list_objects_s3(s3_client, bucket)
    assert len(bucket_objects) == len(
        expected_objects
    ), f"Expected {len(expected_objects)} objects in the bucket"
    for bucket_object in expected_objects:
        assert (
            bucket_object in bucket_objects
        ), f"Expected object {bucket_object} in objects list {bucket_objects}"

    for bucket_object in unexpected_objects:
        assert (
            bucket_object not in bucket_objects
        ), f"Expected object {bucket_object} not in objects list {bucket_objects}"


@allure.step("Try to get object and got error")
def try_to_get_objects_and_expect_error(s3_client, bucket: str, object_keys: list) -> None:
    for obj in object_keys:
        try:
            s3_gate_object.get_object_s3(s3_client, bucket, obj)
            raise AssertionError(f"Object {obj} found in bucket {bucket}")
        except Exception as err:
            assert "The specified key does not exist" in str(
                err
            ), f"Expected error in exception {err}"


@allure.step("Set versioning enable for bucket")
def set_bucket_versioning(s3_client, bucket: str, status: s3_gate_bucket.VersioningStatus):
    s3_gate_bucket.get_bucket_versioning_status(s3_client, bucket)
    s3_gate_bucket.set_bucket_versioning(s3_client, bucket, status=status)
    bucket_status = s3_gate_bucket.get_bucket_versioning_status(s3_client, bucket)
    assert bucket_status == status.value, f"Expected {bucket_status} status. Got {status.value}"


def object_key_from_file_path(full_path: str) -> str:
    return os.path.basename(full_path)


def assert_tags(
    actual_tags: list, expected_tags: Optional[list] = None, unexpected_tags: Optional[list] = None
) -> None:
    expected_tags = (
        [{"Key": key, "Value": value} for key, value in expected_tags] if expected_tags else []
    )
    unexpected_tags = (
        [{"Key": key, "Value": value} for key, value in unexpected_tags] if unexpected_tags else []
    )
    if expected_tags == []:
        assert not actual_tags, f"Expected there is no tags, got {actual_tags}"
    assert len(expected_tags) == len(actual_tags)
    for tag in expected_tags:
        assert tag in actual_tags, f"Tag {tag} must be in {actual_tags}"
    for tag in unexpected_tags:
        assert tag not in actual_tags, f"Tag {tag} should not be in {actual_tags}"


@allure.step("Expected all tags are presented in object")
def check_tags_by_object(
    s3_client,
    bucket: str,
    key_name: str,
    expected_tags: list,
    unexpected_tags: Optional[list] = None,
) -> None:
    actual_tags = s3_gate_object.get_object_tagging(s3_client, bucket, key_name)
    assert_tags(
        expected_tags=expected_tags, unexpected_tags=unexpected_tags, actual_tags=actual_tags
    )


@allure.step("Expected all tags are presented in bucket")
def check_tags_by_bucket(
    s3_client, bucket: str, expected_tags: list, unexpected_tags: Optional[list] = None
) -> None:
    actual_tags = s3_gate_bucket.get_bucket_tagging(s3_client, bucket)
    assert_tags(
        expected_tags=expected_tags, unexpected_tags=unexpected_tags, actual_tags=actual_tags
    )


def assert_object_lock_mode(
    s3_client,
    bucket: str,
    file_name: str,
    object_lock_mode: str,
    retain_untile_date: datetime,
    legal_hold_status: str = "OFF",
    retain_period: Optional[int] = None,
):
    object_dict = s3_gate_object.get_object_s3(s3_client, bucket, file_name, full_output=True)
    assert (
        object_dict.get("ObjectLockMode") == object_lock_mode
    ), f"Expected Object Lock Mode is {object_lock_mode}"
    assert (
        object_dict.get("ObjectLockLegalHoldStatus") == legal_hold_status
    ), f"Expected Object Lock Legal Hold Status is {legal_hold_status}"
    object_retain_date = object_dict.get("ObjectLockRetainUntilDate")
    retain_date = (
        parse(object_retain_date) if isinstance(object_retain_date, str) else object_retain_date
    )
    if retain_untile_date:
        assert retain_date.strftime("%Y-%m-%dT%H:%M:%S") == retain_untile_date.strftime(
            "%Y-%m-%dT%H:%M:%S"
        ), f'Expected Object Lock Retain Until Date is {str(retain_untile_date.strftime("%Y-%m-%dT%H:%M:%S"))}'
    elif retain_period:
        last_modify_date = object_dict.get("LastModified")
        last_modify = (
            parse(last_modify_date) if isinstance(last_modify_date, str) else last_modify_date
        )
        assert (
            retain_date - last_modify + timedelta(seconds=1)
        ).days == retain_period, f"Expected retention period is {retain_period} days"


def check_permission(grantee_type: str, acl: str, actual_permission: str, acl_map: dict) -> str:
    expected_permission = acl_map.get(grantee_type, {}).get(acl, "")
    assert (
        actual_permission == expected_permission
    ), f"{grantee_type} should have {expected_permission} but got {actual_permission}"
    return expected_permission


def assert_s3_acl(acl_grants: list, permitted_users: str, acl: str, acl_map: dict):
    grantees = {"AllUsers": 0, "CanonicalUser": 0}

    for acl_grant in acl_grants:
        grantee_type = acl_grant.get("Grantee", {}).get("Type")

        if grantee_type == "Group" and permitted_users == "AllUsers":
            uri = acl_grant.get("Grantee", {}).get("URI")
            permission = acl_grant.get("Permission")
            expected_permission = check_permission(grantee_type, acl, permission, acl_map)
            assert (
                uri == "http://acs.amazonaws.com/groups/global/AllUsers"
            ), f"All Groups should have {expected_permission} but got {permission}"
            grantees["AllUsers"] += 1

        elif grantee_type == "CanonicalUser":
            permission = acl_grant.get("Permission")
            check_permission(grantee_type, acl, permission, acl_map)
            grantees["CanonicalUser"] += 1

    if permitted_users == "AllUsers":
        for key in grantees:
            assert grantees[key] >= 1, f"{key} should have permission but got none"

    elif permitted_users == "CanonicalUser" and grantees["AllUsers"] > 0:
        logger.error(f"Permission is given to All Users")


def assert_bucket_s3_acl(acl_grants: list, permitted_users: str, acl: str):
    assert_s3_acl(acl_grants, permitted_users, acl, ACL_TO_PERMISSION_MAP_BUCKET)


def assert_object_s3_acl(acl_grants: list, permitted_users: str, acl: str):
    assert_s3_acl(acl_grants, permitted_users, acl, ACL_TO_PERMISSION_MAP_OBJECT)


def parametrize_clients(metafunc):
    if "s3_client" in metafunc.fixturenames:
        clients = ["aws cli", "boto3"]
        for mark in metafunc.definition.own_markers:
            if mark.name == "aws_cli_only":
                clients = ["aws cli"]
                break
            if mark.name == "boto3_only":
                clients = ["boto3"]
                break
        metafunc.parametrize("s3_client", clients, indirect=True)
