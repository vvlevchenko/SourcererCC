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

MULTIPLIER = 50000000

N_PROCESSES = 2
PROJECTS_BATCH = 20
FILE_projects_list = 'project-list.txt'
PATH_stats_file_folder = 'files_stats'
PATH_bookkeeping_proj_folder = 'bookkeeping_projs'
PATH_tokens_file_folder = 'files_tokens'
language_config = {}

file_count = 0


def read_config(config_filename):
    global N_PROCESSES, PROJECTS_BATCH
    global PATH_stats_file_folder, PATH_bookkeeping_proj_folder, PATH_tokens_file_folder
    global separators, comment_inline, comment_inline_pattern, comment_open_tag, comment_close_tag, comment_open_close_pattern
    global file_extensions

    global init_file_id
    global init_proj_id
    global proj_id_flag

    config = ConfigParser()

    # parse existing file
    try:
        config.read(os.path.join(os.path.dirname(os.path.abspath(__file__)), config_filename))
    except IOError:
        print('[ERROR] - Config settings not found. Usage: $python this-script.py config-file.ini')
        sys.exit()

    # Get info from config.ini into global variables
    N_PROCESSES = config.getint('Main', 'N_PROCESSES')
    PROJECTS_BATCH = config.getint('Main', 'PROJECTS_BATCH')
    FILE_projects_list = config.get('Main', 'FILE_projects_list')
    PATH_stats_file_folder = config.get('Folders/Files', 'PATH_stats_file_folder')
    PATH_bookkeeping_proj_folder = config.get('Folders/Files', 'PATH_bookkeeping_proj_folder')
    PATH_tokens_file_folder = config.get('Folders/Files', 'PATH_tokens_file_folder')

    # Reading Language settings
    language_config["separators"] = config.get('Language', 'separators').strip('"').split(' ')
    language_config["comment_inline"] = re.escape(config.get('Language', 'comment_inline'))
    language_config["comment_inline_pattern"] = language_config["comment_inline"] + '.*?$'
    language_config["comment_open_tag"] = re.escape(config.get('Language', 'comment_open_tag'))
    language_config["comment_close_tag"] = re.escape(config.get('Language', 'comment_close_tag'))
    language_config["comment_open_close_pattern"] = language_config["comment_open_tag"] + '.*?' + language_config["comment_close_tag"]
    language_config["file_extensions"] = config.get('Language', 'File_extensions').split(' ')

    # Reading config settings
    init_file_id = config.getint('Config', 'init_file_id')
    init_proj_id = config.getint('Config', 'init_proj_id')

    # flag before proj_id
    proj_id_flag = config.getint('Config', 'init_proj_id')


def get_lines_stats(string, comment_open_close_pattern, comment_inline_pattern):
    lines = count_lines(string)

    string = "\n".join([s for s in string.splitlines() if s.strip()])
    lines_of_code = count_lines(string)

    string, remove_comments_time = remove_comments(string, language_config)
    string = "\n".join([s for s in string.splitlines() if s.strip()]).strip()
    source_lines_of_code = count_lines(string, False)

    return string, lines, lines_of_code, source_lines_of_code, remove_comments_time


def process_tokenizer(string):
    hashsum, hash_time = hash_measuring_time(string)

    string, lines, lines_of_code, source_lines_of_code, remove_comments_time = get_lines_stats(string, comment_open_close_pattern, comment_inline_pattern)

    tokens_bag, tokens_count_total, tokens_count_unique = tokenize_string(string, language_config)  # get tokens bag
    tokens, format_time = format_tokens(tokens_bag)  # make formatted string with tokens

    tokens_hash, hash_delta_time = hash_measuring_time(tokens)
    hash_time += hash_delta_time

    return (hashsum, lines, lines_of_code, source_lines_of_code), (tokens_count_total, tokens_count_unique, tokens_hash, '@#@' + tokens), {
        "tokens_time": format_time,
        "hash_time": hash_time,
        "string_time": remove_comments_time
    }


def tokenize_blocks(file_string, file_path):
    times = {
        "zip_time": 0,
        "file_time": 0,
        "string_time": 0,
        "tokens_time": 0,
        "hash_time": 0,
        "regex_time": 0
    }
    block_linenos = None
    blocks = None
    experimental_values = ''
    if '.py' in file_extensions:
        (block_linenos, blocks) = extract_python_functions.get_functions(file_string, file_path)
    # Notice workaround with replacing. It is needed because javalang counts things like String[]::new as syntax errors
    if '.java' in file_extensions:
        tmp_file_string = file_string.replace("[]::", "::")
        (block_linenos, blocks, experimental_values) = \
            extract_java_functions.get_functions(tmp_file_string, file_path, \
                language_config["separators"], language_config["comment_inline_pattern"])

    if block_linenos is None:
        print("[INFO] Returning None on tokenize_blocks for file {}".format(file_path))
        return None, None, None

    blocks_data = []
    file_hash, hash_time = hash_measuring_time(file_string)
    file_string, lines, LOC, SLOC, re_time = get_lines_stats(file_string, comment_open_close_pattern, comment_inline_pattern)
    final_stats = (file_hash, lines, LOC, SLOC)

    for i, block_string in enumerate(blocks):
        (start_line, end_line) = block_linenos[i]

        (*block_stats, start_line, end_line), block_tokens, times = process_tokenizer(block_string, comment_open_close_pattern, comment_inline_pattern, separators)

        for time_name, time in tmp.items():
            times[time_name] += time
        blocks_data.append((block_tokens, block_stats, experimental_values[i]))
    times["hash_time"] += hash_time
    return final_stats, blocks_data, times


def process_file_contents(file_string, proj_id, file_id, container_path, file_path, file_bytes, file_tokens_file, file_stats_file):
    print(f"[INFO] Started process_file_contents on {file_path}")
    global file_count
    file_count += 1

    file_path = os.path.join(container_path, file_path)
    print(f"[INFO] Started tokenizing blocks on {file_path}")
    (final_stats, blocks_data, times) = tokenize_blocks(file_string, file_path)
    if (final_stats is None) or (blocks_data is None) or (times is None):
        print(f"[WARNING] Problems tokenizing file {file_path}")
        return {}

    if len(blocks_data) > 90000:
        print(f"[WARNING] File {file_path} has {len(blocks_data))} blocks, more than 90000. Range MUST be increased")
        return {}

    # write file stats

    # file stats start with a letter 'f'
    (file_hash, lines, LOC, SLOC) = final_stats
    file_stats_file.write(f'f,{proj_id},{file_id},"{file_path}","{file_url}","{file_hash}",{file_bytes},{lines},{LOC},{SLOC}\n')
    blocks_data = enumerate(blocks_data, 10000)

    start_time = dt.datetime.now()
    try:
        for relative_id, block_data in blocks_data:
            (blocks_tokens, blocks_stats, experimental_values) = block_data
            block_id = f"{relative_id}{file_id}"

            (block_hash, block_lines, block_LOC, block_SLOC, start_line, end_line) = blocks_stats
            (tokens_count_total, tokens_count_unique, token_hash, tokens) = blocks_tokens

            # Adjust the blocks stats written to the files, file stats start with a letter 'b'
            file_stats_file.write(f'b,{proj_id},{block_id},"{block_hash}",{block_lines},{block_LOC},{block_SLOC},{start_line},{end_line}\n')
            file_tokens_file.write(f'{proj_id},{block_id},{tokens_count_total},{tokens_count_unique}')
            if len(experimental_values) != 0:
                file_tokens_file.write("," + experimental_values.replace(",", ";"))
            file_tokens_file.write(f",{token_hash}{tokens}\n")
        file_times["write_time"] = (dt.datetime.now() - start_time).microseconds
    except Exception as e:
        print("[WARNING] Error on step3 of process_file_contents")
        print(e)
    print(f"[INFO] Successfully ran process_file_contents {os.path.join(container_path, file_path)}")
    return file_times


def process_one_project(process_num, proj_id, proj_path, base_file_id, file_tokens_file, file_bookkeeping_proj, file_stats_file):
    print(f"[INFO] Starting  project <{proj_id},{proj_path}> (process {process_num})")
    p_start = dt.datetime.now()

    proj_id = str(proj_id_flag) + proj_id
    if not os.path.isfile(proj_path):
        print(f"[WARNING] Unable to open project <{proj_id},{proj_path}> (process {process_num})")
        return
    times = process_zip_ball(process_num, proj_path, proj_id, proj_path, base_file_id, FILE_tokens_file, FILE_bookkeeping_proj, FILE_stats_file, language_config, process_file_contents)
    zip_time, file_time, string_time, tokens_time, write_time, hash_time, regex_time = (-1, -1, -1, -1, -1, -1, -1)
    if times is not None:
        zip_time = times["zip_time"]
        file_time = times["file_time"]
        string_time = times["string_time"]
        tokens_time = times["tokens_time"]
        write_time = times["write_time"]
        hash_time = times["hash_time"]
        regex_time = times["regex_time"]
    file_bookkeeping_proj.write(f'{proj_id},"{proj_path}"\n')

    p_elapsed = dt.datetime.now() - p_start
    print(f"[INFO] Project finished <{proj_id},{proj_path}> (process {process_num})")
    print(f"[INFO]  ({process_num}): Total: {p_elapsed} ms")
    print(f"[INFO]      Zip: {zip_time} ms")
    print(f"[INFO]      Read: {file_time} ms")
    print(f"[INFO]      Separators: {string_time} ms")
    print(f"[INFO]      Tokens: {tokens_time} ms")
    print(f"[INFO]      Write: {write_time} ms")
    print(f"[INFO]      Hash: {hash_time} ms")
    print(f"[INFO]      regex: {regex_time} ms")
