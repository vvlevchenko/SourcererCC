#!/usr/bin/env python3

import subprocess
import os
import shutil


def run_command(cmd):
    print("running command {}".format(" ".join(cmd)))
    p = subprocess.Popen(cmd, universal_newlines=True)
    p.communicate()
    return p.returncode


def get_full_path(filename):
    cur_dir = os.path.dirname(os.path.realpath(__file__))
    return f"{cur_dir}/{filename}"


def clear_file_mode_tokenizer_files():
    os.remove(get_full_path("tokenizers/file-level/project-list.txt"))
    shutil.rmtree(get_full_path("tokenizers/file-level/tokenizer-sample-input/"))
    os.remove(get_full_path("tokenizers/file-level/blocks.file"))
    shutil.rmtree(get_full_path("tokenizers/file-level/bookkeeping_projs/"))
    shutil.rmtree(get_full_path("tokenizers/file-level/files_stats/"))
    shutil.rmtree(get_full_path("tokenizers/file-level/files_tokens/"))


def clear_block_mode_tokenizer_files():
    shutil.rmtree(get_full_path("tokenizers/block-level/__pycache__/"))
    shutil.rmtree(get_full_path("tokenizers/block-level/blocks_tokens/"))
    shutil.rmtree(get_full_path("tokenizers/block-level/bookkeeping_projs/"))
    shutil.rmtree(get_full_path("tokenizers/block-level/file_block_stats/"))
    os.remove(get_full_path("tokenizers/block-level/project-list.txt"))
    shutil.rmtree(get_full_path("tokenizers/block-level/tokenizer-sample-input/"))


def clear_clone_detector_files():
    os.remove(get_full_path("results.pairs"))
    shutil.rmtree(get_full_path("clone-detector/SCC_LOGS/"))
    shutil.rmtree(get_full_path("clone-detector/backup_output/"))
    shutil.rmtree(get_full_path("clone-detector/fwdindex/"))
    shutil.rmtree(get_full_path("clone-detector/gtpmindex/"))
    shutil.rmtree(get_full_path("clone-detector/index/"))
    os.remove(get_full_path("clone-detector/run_metadata.scc"))
    os.remove(get_full_path("clone-detector/search_metadata.txt"))
    shutil.rmtree(get_full_path("clone-detector/NODE_1/"))
    os.remove(get_full_path("clone-detector/scriptinator_metadata.scc"))
    shutil.rmtree(get_full_path("clone-detector/input/"))
    shutil.rmtree(get_full_path("clone-detector/dist/"))
    shutil.rmtree(get_full_path("clone-detector/build/"))


if __name__ == "__main__":
    download_script_path = get_full_path("downloadRepos.py")
    urls_list_path = get_full_path("urls.txt")
    file_mode_input_dir_path = get_full_path("tokenizers/file-level/tokenizer-sample-input")
    block_mode_input_dir_path = get_full_path("tokenizers/block-level/tokenizer-sample-input")
    run_command([download_script_path, urls_list_path, file_mode_input_dir_path])
    run_command([download_script_path, urls_list_path, block_mode_input_dir_path])

    prettify_script_path = get_full_path("prettify_results.py")
    results_file_path = get_full_path("results.pairs")

    run_blocks_mode_script_path = get_full_path("runSourcererCC-BlocksMode.sh")
    run_command([run_blocks_mode_script_path])
    stats_file_path = get_full_path("tokenizers/block-level/file_block_stats/")
    run_command([prettify_script_path, "--blocks-mode", "-r", results_file_path, "-s", stats_file_path])

    clear_clone_detector_files()
    clear_block_mode_tokenizer_files()

    run_files_mode_script_path = get_full_path("runSourcererCC-FilesMode.sh")
    run_command([run_files_mode_script_path])
    stats_file_path = get_full_path("tokenizers/file-level/files_stats/")
    run_command([prettify_script_path, "-r", results_file_path, "-s", stats_file_path])

    clear_clone_detector_files()
    clear_file_mode_tokenizer_files()
