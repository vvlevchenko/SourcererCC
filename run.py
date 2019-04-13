#!/usr/bin/env python3

from subprocess import run
import os
import shutil
import glob


def get_full_path(filename):
    cur_dir = os.path.dirname(os.path.realpath(__file__))
    return f"{cur_dir}/{filename}"


def rm_folder(foldername):
    full_foldername = get_full_path(foldername)
    if os.path.exists(full_foldername):
        shutil.rmtree(full_foldername)


def rm_file(filename):
    full_filename = get_full_path(filename)
    if os.path.exists(full_filename):
        os.remove(full_filename)


def clear_file_mode_tokenizer_files():
    rm_file("tokenizers/file-level/project-list.txt")
    rm_folder("tokenizers/file-level/tokenizer-sample-input/")
    rm_folder("tokenizers/file-level/bookkeeping_projs/")
    rm_folder("tokenizers/file-level/files_stats/")
    rm_folder("tokenizers/file-level/files_tokens/")


def clear_block_mode_tokenizer_files():
    rm_folder("tokenizers/block-level/__pycache__/")
    rm_folder("tokenizers/block-level/blocks_tokens/")
    rm_folder("tokenizers/block-level/bookkeeping_projs/")
    rm_folder("tokenizers/block-level/file_block_stats/")
    rm_folder("tokenizers/block-level/tokenizer-sample-input/")
    rm_file("tokenizers/block-level/project-list.txt")


def clear_clone_detector_files():
    rm_folder("clone-detector/SCC_LOGS/")
    rm_folder("clone-detector/backup_output/")
    rm_folder("clone-detector/fwdindex/")
    rm_folder("clone-detector/gtpmindex/")
    rm_folder("clone-detector/index/")
    rm_folder("clone-detector/NODE_1/")
    rm_folder("clone-detector/input/")
    rm_folder("clone-detector/dist/")
    rm_folder("clone-detector/build/")
    rm_file("clone-detector/run_metadata.scc")
    rm_file("clone-detector/search_metadata.txt")
    rm_file("results.pairs")
    rm_file("clone-detector/scriptinator_metadata.scc")


def run_algo():
    run([get_full_path("clone-detector/controller.py"), "1"], cwd=get_full_path("clone-detector/"))
    with open(get_full_path("results.pairs"), "w", encoding="utf-8") as results_file:
        for output_file in glob.glob(get_full_path("clone-detector/NODE_*/output8.0/query_*")):
            with open(output_file, "r", encoding="utf-8") as out_file_descr:
                results_file.writelines(out_file_descr.readlines())


def run_block_mode():
    os.makedirs(get_full_path("clone-detector/input/dataset"))
    run([get_full_path("tokenizers/block-level/tokenizer.py"), "zipblocks"], cwd=get_full_path("tokenizers/block-level/"))
    with open(get_full_path("clone-detector/input/dataset/blocks.file"), "w", encoding="utf-8") as blocks_file:
        for out_file in glob.glob(get_full_path("tokenizers/block-level/blocks_tokens/*")):
            with open(out_file, "r", encoding="utf-8") as out_file_descr:
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
    with open(get_full_path("clone-detector/input/dataset/blocks.file"), "w", encoding="utf-8") as blocks_file:
        for out_file in glob.glob(get_full_path("tokenizers/file-level/files_tokens/*")):
            with open(out_file, "r", encoding="utf-8") as out_file_descr:
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
    with open(file_mode_projects_list_path, "w", encoding="utf-8") as out_file:
        run([download_script_path, urls_list_path, file_mode_input_dir_path], stdout=out_file)
    with open(block_mode_projects_list_path, "w", encoding="utf-8") as out_file:
        run([download_script_path, urls_list_path, block_mode_input_dir_path], stdout=out_file)

    run_block_mode()
    run_file_mode()
