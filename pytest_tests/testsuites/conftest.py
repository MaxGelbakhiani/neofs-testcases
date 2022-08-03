import logging
import os
import re
import shutil

import allure
import pytest
from robot.api import deco

import wallet
from cli_helpers import _cmd_run
from common import ASSETS_DIR, FREE_STORAGE, MAINNET_WALLET_PATH, NEOFS_NETMAP_DICT
from payment_neogo import neofs_deposit, transfer_mainnet_gas
from python_keywords.node_management import node_healthcheck, create_ssh_client
from sbercloud_helper import SberCloudConfig


def robot_keyword_adapter(name=None, tags=(), types=()):
    return allure.step(name)


deco.keyword = robot_keyword_adapter

logger = logging.getLogger('NeoLogger')


@pytest.fixture(scope='session')
def cloud_infrastructure_check():
    if not is_cloud_infrastructure():
        pytest.skip('Test only works on SberCloud infrastructure')
    yield


def is_cloud_infrastructure():
    cloud_config = SberCloudConfig.from_env()
    return cloud_config.project_id is not None


@pytest.fixture(scope='session', autouse=True)
@allure.title('Check binary versions')
def check_binary_versions(request):
    environment_dir = request.config.getoption('--alluredir')
    is_cloud = is_cloud_infrastructure()
    # Collect versions of neo binaries
    binaries = ['neo-go', 'neofs-cli', 'neofs-authmate']
    env_out = _get_binaries_version_local(binaries)

    if is_cloud:
        binaries = ['neo-go',
                    'neofs-adm',
                    'neofs-cli',
                    'neofs-http-gw',
                    'neofs-ir',
                    'neofs-lens',
                    'neofs-node',
                    'neofs-s3-authmate',
                    'neofs-s3-gw',
                    'neogo-morph-cn']
        env_out = _get_binaries_version_remote(binaries)

    # Get version of aws binary
    out = _cmd_run('aws --version')
    out_lines = out.split("\n")
    env_out["AWS"] = out_lines[0] if out_lines else 'Unknown'

    if environment_dir:
        with open(f'{environment_dir}/environment.properties', 'w') as out_file:
            for env, env_value in env_out.items():
                out_file.write(f'{env}={env_value}\n')


def _get_binaries_version_local(binaries: list) -> dict:
    env_out = {}
    for binary in binaries:
        out = _cmd_run(f'{binary} --version')
        version = re.search(r'version[:\s]*(.+)', out, re.IGNORECASE)
        env_out[binary.upper()] = version.group(1) if version else 'Unknown'
    return env_out


def _get_binaries_version_remote(binaries: list) -> dict:
    env_out = {}

    for node_name in NEOFS_NETMAP_DICT:
        with create_ssh_client(node_name) as ssh_client:
            for binary in binaries:
                out = ssh_client.exec(f'{binary} --version').stdout
                version = re.search(r'version[:\s]*(.+)', out, re.IGNORECASE)
                version = version.group(1) if version else 'Unknown'
                if not env_out.get(binary.upper()):
                    env_out[binary.upper()] = version
                else:
                    msg = f'Expected binary {binary} versions on node s1 and {node_name} are the same'
                    assert env_out[binary.upper()] == version, msg
    return env_out


@pytest.fixture(scope='session', autouse=True)
@allure.title('Run health check for all storage nodes')
def run_health_check():
    failed_nodes = []
    for node_name in NEOFS_NETMAP_DICT.keys():
        health_check = node_healthcheck(node_name)
        if health_check.health_status != 'READY' or health_check.network_status != 'ONLINE':
            failed_nodes.append(node_name)

    if failed_nodes:
        raise AssertionError(f'Nodes {failed_nodes} are not healthy')


@pytest.fixture(scope='session')
@allure.title('Prepare tmp directory')
def prepare_tmp_dir():
    full_path = f'{os.getcwd()}/{ASSETS_DIR}'
    shutil.rmtree(full_path, ignore_errors=True)
    os.mkdir(full_path)
    yield full_path
    shutil.rmtree(full_path)


@pytest.fixture(scope='session')
@allure.title('Init wallet with address')
def init_wallet_with_address(prepare_tmp_dir):
    yield wallet.init_wallet(ASSETS_DIR)


@pytest.fixture(scope='session')
@allure.title('Prepare wallet and deposit')
def prepare_wallet_and_deposit(init_wallet_with_address):
    wallet, addr, _ = init_wallet_with_address
    logger.info(f'Init wallet: {wallet},\naddr: {addr}')
    allure.attach.file(wallet, os.path.basename(wallet), allure.attachment_type.JSON)

    if not FREE_STORAGE:
        deposit = 30
        transfer_mainnet_gas(wallet, deposit + 1, wallet_path=MAINNET_WALLET_PATH)
        neofs_deposit(wallet, deposit)

    return wallet
