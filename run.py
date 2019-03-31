#!/usr/bin/env python3

from subprocess import run
import os
import shutil
import glob


def get_full_path(filename):
    cur_dir = os.path.dirname(os.path.realpath(__file__))
    return f"{cur_dir}/{filename}"


def clear_file_mode_tokenizer_files():
    os.remove(get_full_path("tokenizers/file-level/project-list.txt"))
    shutil.rmtree(get_full_path("tokenizers/file-level/tokenizer-sample-input/"))
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


def run_algo():
    run([get_full_path("clone-detector/controller.py"), "1"], cwd=get_full_path("clone-detector/"))
    with open(get_full_path("results.pairs"), "w") as results_file:
        for output_file in glob.glob(get_full_path("clone-detector/NODE_*/output8.0/query_*")):
            with open(output_file, "r") as out_file_descr:
                results_file.writelines(out_file_descr.readlines())


def run_block_mode():
    os.makedirs(get_full_path("clone-detector/input/dataset"))
    run([get_full_path("tokenizers/block-level/tokenizer.py"), "zipblocks"], cwd=get_full_path("tokenizers/block-level/"))
    with open(get_full_path("clone-detector/input/dataset/blocks.file"), "w") as blocks_file:
        for out_file in glob.glob(get_full_path("tokenizers/block-level/blocks_tokens/*")):
            with open(out_file, "r") as out_file_descr:
                blocks_file.writelines(out_file_descr.readlines())
    run_algo()
    stats_file_path = get_full_path("tokenizers/block-level/file_block_stats/")
    prettify_script_path = get_full_path("prettify_results.py")
    results_file_path = get_full_path("results.pairs")
    run([prettify_script_path, "--blocks-mode", "-r", results_file_path, "-s", stats_file_path])

    clear_block_mode_tokenizer_files()
    clear_clone_detector_files()


def run_file_mode():
    os.makedirs(get_full_path("clone-detector/input/dataset"))
    run([get_full_path("tokenizers/file-level/tokenizer.py"), "zip"], cwd=get_full_path("tokenizers/file-level/"))
    with open(get_full_path("clone-detector/input/dataset/blocks.file"), "w") as blocks_file:
        for out_file in glob.glob(get_full_path("tokenizers/file-level/files_tokens/*")):
            with open(out_file, "r") as out_file_descr:
                blocks_file.writelines(out_file_descr.readlines())
    run_algo()
    stats_file_path = get_full_path("tokenizers/file-level/files_stats/")
    prettify_script_path = get_full_path("prettify_results.py")
    results_file_path = get_full_path("results.pairs")
    run([prettify_script_path, "-r", results_file_path, "-s", stats_file_path])

    clear_file_mode_tokenizer_files()
    clear_clone_detector_files()


if __name__ == "__main__":
    download_script_path = get_full_path("downloadRepos.py")
    urls_list_path = get_full_path("urls.txt")
    file_mode_input_dir_path = get_full_path("tokenizers/file-level/tokenizer-sample-input")
    file_mode_projects_list_path = get_full_path("tokenizers/file-level/project-list.txt")
    block_mode_input_dir_path = get_full_path("tokenizers/block-level/tokenizer-sample-input")
    block_mode_projects_list_path = get_full_path("tokenizers/block-level/project-list.txt")
    with open(file_mode_projects_list_path, "w") as out_file:
        run([download_script_path, urls_list_path, file_mode_input_dir_path], stdout=out_file)
    with open(block_mode_projects_list_path, "w") as out_file:
        run([download_script_path, urls_list_path, block_mode_input_dir_path], stdout=out_file)

    run_block_mode()
    run_file_mode()
