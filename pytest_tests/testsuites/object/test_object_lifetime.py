import logging

import allure
import pytest
from epoch import get_epoch
from file_helper import generate_file, get_file_hash
from grpc_responses import OBJECT_NOT_FOUND
from pytest import FixtureRequest
from python_keywords.container import create_container
from python_keywords.neofs_verbs import get_object_from_random_node, put_object_to_random_node
from utility import wait_for_gc_pass_on_storage_nodes

from steps.cluster_test_base import ClusterTestBase

logger = logging.getLogger("NeoLogger")


@pytest.mark.grpc_api
class TestObjectApiLifetime(ClusterTestBase):
    @allure.title("Test object life time")
    @pytest.mark.parametrize(
        "object_size,expiration_flag",
        [
            (pytest.lazy_fixture("simple_object_size"), "lifetime"),
            (pytest.lazy_fixture("complex_object_size"), "expire_at"),
        ],
        ids=["simple object, lifetime", "complex object, expire_at"],
    )
    def test_object_api_lifetime(
        self, default_wallet: str, request: FixtureRequest, object_size: int, expiration_flag: str
    ):
        """
        Test object deleted after expiration epoch.
        """

        allure.dynamic.title(f"Test object life time for {request.node.callspec.id}")

        wallet = default_wallet
        endpoint = self.cluster.default_rpc_endpoint
        cid = create_container(wallet, self.shell, endpoint)

        file_path = generate_file(object_size)
        file_hash = get_file_hash(file_path)
        epoch = get_epoch(self.shell, self.cluster)

        oid = put_object_to_random_node(
            wallet,
            file_path,
            cid,
            self.shell,
            self.cluster,
            expire_at=epoch + 1 if expiration_flag == "expire_at" else None,
            lifetime=1 if expiration_flag == "lifetime" else None,
        )
        got_file = get_object_from_random_node(wallet, cid, oid, self.shell, self.cluster)
        assert get_file_hash(got_file) == file_hash

        with allure.step("Tick two epochs"):
            self.tick_epochs_and_wait(2)

        # Wait for GC, because object with expiration is counted as alive until GC removes it
        wait_for_gc_pass_on_storage_nodes()

        with allure.step("Check object deleted because it expires-on epoch"):
            with pytest.raises(Exception, match=OBJECT_NOT_FOUND):
                get_object_from_random_node(wallet, cid, oid, self.shell, self.cluster)
