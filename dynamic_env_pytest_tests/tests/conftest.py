import logging
import os
import shutil
import time
from distutils import dir_util

import allure
import pytest
from common import (
    ASSETS_DIR,
    COMPLEX_OBJECT_CHUNKS_COUNT,
    COMPLEX_OBJECT_TAIL_SIZE,
    SIMPLE_OBJECT_SIZE,
    TEST_FILES_DIR,
    TEST_OBJECTS_DIR,
)
from file_helper import generate_file
from neofs_testlib.env.env import NeoFSEnv, NodeWallet
from neofs_testlib.shell import Shell
from python_keywords.neofs_verbs import get_netmap_netinfo

from helpers.wallet_helpers import create_wallet

logger = logging.getLogger("NeoLogger")


def pytest_addoption(parser):
    parser.addoption(
        "--persist-env", action="store_true", default=False, help="persist deployed env"
    )
    parser.addoption("--load-env", action="store", help="load persisted env from file")


@pytest.fixture(scope="session")
def neofs_env(request):
    if request.config.getoption("--load-env"):
        neofs_env = NeoFSEnv.load(request.config.getoption("--load-env"))
    else:
        neofs_env = NeoFSEnv.simple()

    neofs_env.neofs_adm().morph.set_config(
        rpc_endpoint=f"http://{neofs_env.morph_rpc}",
        alphabet_wallets=neofs_env.alphabet_wallets_dir,
        post_data=f"ContainerFee=0 ContainerAliasFee=0 MaxObjectSize=524288",
    )
    time.sleep(30)

    yield neofs_env

    if request.config.getoption("--persist-env"):
        neofs_env.persist()
    else:
        if not request.config.getoption("--load-env"):
            neofs_env.kill()

    logs_path = os.path.join(os.getcwd(), ASSETS_DIR, "logs")
    os.makedirs(logs_path, exist_ok=True)

    shutil.copyfile(neofs_env.s3_gw.stderr, f"{logs_path}/s3_gw_log.txt")
    shutil.copyfile(neofs_env.http_gw.stderr, f"{logs_path}/http_gw_log.txt")
    for idx, ir in enumerate(neofs_env.inner_ring_nodes):
        shutil.copyfile(ir.stderr, f"{logs_path}/ir_{idx}_log.txt")
    for idx, sn in enumerate(neofs_env.storage_nodes):
        shutil.copyfile(sn.stderr, f"{logs_path}/sn_{idx}_log.txt")

    logs_zip_file_path = shutil.make_archive("neofs_logs", "zip", logs_path)
    allure.attach.file(logs_zip_file_path, name="neofs logs", extension="zip")


@pytest.fixture(scope="session")
@allure.title("Prepare default wallet and deposit")
def default_wallet(temp_directory):
    return create_wallet()


@pytest.fixture(scope="session")
def client_shell(neofs_env: NeoFSEnv) -> Shell:
    yield neofs_env.shell


@pytest.fixture(scope="session")
def max_object_size(neofs_env: NeoFSEnv, client_shell: Shell) -> int:
    storage_node = neofs_env.storage_nodes[0]
    net_info = get_netmap_netinfo(
        wallet=storage_node.wallet.path,
        wallet_config=storage_node.cli_config,
        endpoint=storage_node.endpoint,
        shell=client_shell,
    )
    yield net_info["maximum_object_size"]


@pytest.fixture(scope="session")
def simple_object_size(max_object_size: int) -> int:
    yield int(SIMPLE_OBJECT_SIZE) if int(SIMPLE_OBJECT_SIZE) < max_object_size else max_object_size


@pytest.fixture(scope="session")
def complex_object_size(max_object_size: int) -> int:
    return max_object_size * int(COMPLEX_OBJECT_CHUNKS_COUNT) + int(COMPLEX_OBJECT_TAIL_SIZE)


@pytest.fixture(scope="session")
@allure.title("Prepare tmp directory")
def temp_directory() -> str:
    with allure.step("Prepare tmp directory"):
        full_path = os.path.join(os.getcwd(), ASSETS_DIR)
        create_dir(full_path)

    yield full_path

    with allure.step("Remove tmp directory"):
        remove_dir(full_path)


@pytest.fixture(scope="module", autouse=True)
@allure.title(f"Prepare test files directories")
def artifacts_directory(temp_directory: str) -> None:
    dirs = [TEST_FILES_DIR, TEST_OBJECTS_DIR]
    for dir_name in dirs:
        with allure.step(f"Prepare {dir_name} directory"):
            full_path = os.path.join(temp_directory, dir_name)
            create_dir(full_path)

    yield

    for dir_name in dirs:
        with allure.step(f"Remove {dir_name} directory"):
            remove_dir(full_path)


@pytest.fixture(scope="module")
def owner_wallet(temp_directory) -> NodeWallet:
    """
    Returns wallet which owns containers and objects
    """
    return create_wallet()


@pytest.fixture(scope="module")
def user_wallet(temp_directory) -> NodeWallet:
    """
    Returns wallet which will use objects from owner via static session
    """
    return create_wallet()


@pytest.fixture(scope="module")
def stranger_wallet(temp_directory) -> NodeWallet:
    """
    Returns stranger wallet which should fail to obtain data
    """
    return create_wallet()


@pytest.fixture(scope="module")
def scammer_wallet(temp_directory) -> NodeWallet:
    """
    Returns stranger wallet which should fail to obtain data
    """
    return create_wallet()


@pytest.fixture(scope="module")
def not_owner_wallet(temp_directory) -> NodeWallet:
    """
    Returns stranger wallet which should fail to obtain data
    """
    return create_wallet()


@pytest.fixture(scope="function")
@allure.title("Enable metabase resync on start")
def enable_metabase_resync_on_start(neofs_env: NeoFSEnv):
    for node in neofs_env.storage_nodes:
        try:
            node.set_metabase_resync(True)
        except Exception:
            node.set_metabase_resync(True)
    yield
    for node in neofs_env.storage_nodes:
        node.set_metabase_resync(False)


@pytest.fixture(scope="module")
def file_path(simple_object_size, artifacts_directory):
    yield generate_file(simple_object_size)


def create_dir(dir_path: str) -> None:
    with allure.step("Create directory"):
        remove_dir(dir_path)
        os.mkdir(dir_path)


def remove_dir(dir_path: str) -> None:
    with allure.step("Remove directory"):
        shutil.rmtree(dir_path, ignore_errors=True)


@pytest.fixture
def datadir(tmpdir, request):
    filename = request.module.__file__
    test_dir, _ = os.path.splitext(filename)

    if os.path.isdir(test_dir):
        dir_util.copy_tree(test_dir, str(tmpdir))

    return tmpdir
