import datetime as dt
import zipfile
import re
import collections
import hashlib
import os
from configparser import ConfigParser


from .utils import *
from . import extract_java_functions
from . import extract_python_functions


language_config = {}
dirs_config = {}
inner_config = {
    "MULTIPLIER": 50000000
}

file_count = 0


def read_language_config(config):
    language_config = {}
    language_config["separators"] = config.get('Language', 'separators').strip('"').split(' ')
    language_config["comment_inline"] = re.escape(config.get('Language', 'comment_inline'))
    language_config["comment_open_tag"] = re.escape(config.get('Language', 'comment_open_tag'))
    language_config["comment_close_tag"] = re.escape(config.get('Language', 'comment_close_tag'))
    language_config["file_extensions"] = config.get('Language', 'File_extensions').split(' ')

    language_config["comment_inline_pattern"] = language_config["comment_inline"] + '.*?$'
    language_config["comment_open_close_pattern"] = language_config["comment_open_tag"] + '.*?' + language_config["comment_close_tag"]
    return language_config


def read_inner_config(config):
    inner_config = {}
    # Get info from config.ini into global variables
    inner_config["N_PROCESSES"] = config.getint('Main', 'N_PROCESSES')
    inner_config["PROJECTS_BATCH"] = config.getint('Main', 'PROJECTS_BATCH')
    inner_config["FILE_projects_list"] = config.get('Main', 'FILE_projects_list')
    # Reading config settings
    inner_config["init_file_id"] = config.getint('Config', 'init_file_id')
    inner_config["init_proj_id"] = config.getint('Config', 'init_proj_id')
    # flag before proj_id
    inner_config["proj_id_flag"] = config.getint('Config', 'init_proj_id')
    return inner_config


def read_dirs_config(config):
    dirs_config = {}
    dirs_config["stats_file_folder"] = config.get('Folders/Files', 'PATH_stats_file_folder')
    dirs_config["bookkeeping_proj_folder"] = config.get('Folders/Files', 'PATH_bookkeeping_proj_folder')
    dirs_config["tokens_file_folder"] = config.get('Folders/Files', 'PATH_tokens_file_folder')
    return dirs_config


def read_config(config_filename):
    global language_config
    global dirs_config
    global inner_config

    config = ConfigParser()
    try:
        config.read(os.path.join(os.path.dirname(os.path.abspath(__file__)), config_filename))
    except IOError:
        print(f"[ERROR] - Config file {config_filename} is not found")
        sys.exit(1)

    language_config = read_language_config(config)
    inner_config = read_inner_config(config)
    dirs_config = read_dirs_config(config)


def get_lines_stats(string, language_config):
    def is_line_empty(line):
        return line.strip() == ""
    def remove_lines(string, predicate):
        return "\n".join(filter(lambda s: not predicate(s), string.splitlines()))

    lines = count_lines(string)

    string_lines = remove_lines(string, is_line_empty)
    loc = count_lines(string)

    string_lines, remove_comments_time = remove_comments(string_lines, language_config)
    code = remove_lines(string_lines, is_line_empty)
    sloc = count_lines(code, False)

    return code, lines, loc, sloc, remove_comments_time


def process_tokenizer(string, language_config):
    string_hash, hash_time = hash_measuring_time(string)

    string, lines, loc, sloc, remove_comments_time = get_lines_stats(string, language_config)

    tokens_bag, tokens_count_total, tokens_count_unique = tokenize_string(string, language_config)  # get tokens bag
    tokens, format_time = format_tokens(tokens_bag)  # make formatted string with tokens

    tokens_hash, hash_delta_time = hash_measuring_time(tokens)
    hash_time += hash_delta_time

    return (string_hash, lines, loc, sloc), (tokens_count_total, tokens_count_unique, tokens_hash, tokens), {
        "tokens_time": format_time,
        "hash_time": hash_time,
        "string_time": remove_comments_time
    }


def parse_blocks(file_string, file_path, language_config):
    block_linenos = None
    blocks = None
    function_name = ''
    if '.py' in language_config["extensions"]:
        (block_linenos, blocks) = extract_python_functions.get_functions(file_string, file_path)
        return (block_linenos, blocks, "PYTHON_FUNCTION_SIGNATURE_NOT_IMPLEMENTED")
    elif '.java' in language_config["extensions"]:
        # Workaround with replacing is needed because javalang counts things like String[]::new as syntax errors
        tmp_file_string = file_string.replace("[]::", "::")
        comment_inline_pattern = language_config["comment_inline_pattern"]
        return extract_java_functions.get_functions(tmp_file_string, file_path, comment_inline_pattern)
    return (None, None, None)


def tokenize_blocks(file_string, file_path):
    global language_config

    times = {
        "zip_time": 0,
        "file_time": 0,
        "string_time": 0,
        "tokens_time": 0,
        "hash_time": 0,
        "regex_time": 0
    }

    block_linenos, blocks, function_name = parse_blocks(file_string, file_path, language_config)
    if block_linenos is None:
        print(f"[INFO] Returning None on tokenize_blocks for file {file_path}")
        return None, None, None

    file_hash, hash_time = hash_measuring_time(file_string)
    file_string, lines, LOC, SLOC, re_time = get_lines_stats(file_string, language_config)

    blocks_data = []
    for i, block_string in enumerate(blocks):
        (start_line, end_line) = block_linenos[i]

        stats, block_tokens, tokenizer_times = process_tokenizer(block_string, language_config)
        block_stats = (stats, start_line, end_line)

        for time_name, time in tokenizer_times.items():
            times[time_name] += time
        blocks_data.append((block_tokens, block_stats, function_name[i]))
    times["hash_time"] += hash_time
    return (file_hash, lines, LOC, SLOC), blocks_data, times


def process_file_contents(file_string, proj_id, file_id, container_path, file_path, file_bytes, file_tokens_file, file_stats_file):
    print(f"[INFO] Started process_file_contents on {file_path}")
    global file_count
    file_count += 1

    file_path = os.path.join(container_path, file_path)
    (final_stats, blocks_data, times) = tokenize_blocks(file_string, file_path)

    if (final_stats is None) or (blocks_data is None) or (times is None):
        print(f"[WARNING] Problems tokenizing file {file_path}")
        return {}

    if len(blocks_data) > 90000:
        print(f"[WARNING] File {file_path} has {len(blocks_data)} blocks, more than 90000. Range MUST be increased")
        return {}

    # file stats start with a letter 'f'
    (file_hash, lines, LOC, SLOC) = final_stats
    file_stats_file.write(f'f,{proj_id},{file_id},"{file_path}","{file_url}","{file_hash}",{file_bytes},{lines},{LOC},{SLOC}\n')
    blocks_data = enumerate(blocks_data, 10000)

    start_time = dt.datetime.now()
    try:
        for relative_id, block_data in blocks_data:
            (blocks_tokens, blocks_stats, experimental_values) = block_data
            block_id = f"{relative_id}{file_id}"

            (tokens_count_total, tokens_count_unique, token_hash, tokens) = blocks_tokens
            (block_hash, block_lines, block_LOC, block_SLOC, start_line, end_line) = blocks_stats

            # Adjust the blocks stats written to the files, file stats start with a letter 'b'
            stats_file.write(f'b,{proj_id},{block_id},"{block_hash}",{block_lines},{block_LOC},{block_SLOC},{start_line},{end_line}\n')
            tokens_file.write(f'{proj_id},{block_id},{tokens_count_total},{tokens_count_unique},{experimental_values.replace(",", ";")},{token_hash}@#@{tokens}\n')
    except Exception as e:
        print("[WARNING] Error on step3 of process_file_contents")
        print(e)
    print(f"[INFO] Successfully ran process_file_contents {os.path.join(container_path, file_path)}")
    file_times["write_time"] = (dt.datetime.now() - start_time).microseconds
    return file_times


def print_times(project_info, elapsed, times):
    print(f"[INFO] Finished {project_info}")
    print(f"[INFO] Total: {elapsed} ms")
    for time_name, time in times.items():
        print(f"[INFO]      {time_name}: {time} ms")

def process_one_project(process_num, proj_id, proj_path, base_file_id, tokens_file, bookkeeping_proj, stats_file):
    project_info = f"project <id: {proj_id}, path: {proj_path}> (process {process_num})"
    print(f"[INFO] Starting  {project_info}")

    start_time = dt.datetime.now()
    proj_id = f"{proj_id_flag}{proj_id}"
    if not os.path.isfile(proj_path):
        print(f"[WARNING] Unable to open {project_info}")
        return
    times = process_zip_ball(process_num, proj_id, proj_path, base_file_id, language_config, process_file_contents)
    file_bookkeeping_proj.write(f'{proj_id},"{proj_path}"\n')
    elapsed_time = dt.datetime.now() - start_time

    print_times(project_info, elapsed_time, times)